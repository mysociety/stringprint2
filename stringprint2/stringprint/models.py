# -*- coding: utf-8 -*-
from __future__ import annotations
import time
import sys
import codecs
import datetime
import importlib
import io
import os
import shutil
import subprocess
import time
from collections import OrderedDict
from pathlib import Path
from tempfile import mkdtemp
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

import Levenshtein as lev
import markdown
import mkepub
import tinify
from stringprint2.charts import Chart
from stringprint2.charts.fields import ChartField
from dirsync import sync
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.staticfiles import finders
from django.core.files import File
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import models
from django.db.models import F
from django.db.models.query import QuerySet
from django.template import Context, Template
from django.template.loader import render_to_string
from django.test.client import RequestFactory
from django.urls import reverse
from django.utils.html import escape, mark_safe
from django.utils.timezone import now
from PIL import Image
from ruamel.yaml import YAML
from selenium import common, webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from useful_inkleby.files import QuickText
from useful_inkleby.useful_django.fields import JsonBlockField
from useful_inkleby.useful_django.models import FlexiBulkModel
from webptools import webplib as webp

from stringprint.tools.deepink import Graf, Section

from .tools.deepink import process_ink

chrome_driver_path = settings.CHROME_DRIVER


class OverwriteStorage(FileSystemStorage):
    def get_available_name(self, name: str, max_length: Optional[int] = None) -> str:
        if self.exists(name):
            os.remove(os.path.join(self.location, name))
        return super().get_available_name(name, max_length)


def fix_yaml(ya):
    if type(ya) == list:
        items = [fix_yaml(x) for x in ya]
        di = {}
        for i in items:
            di.update(i)
        return di
    if type(ya) == dict:
        return {x: fix_yaml(y) for x, y in ya.items()}
    return ya


def get_yaml(file_path: str) -> dict:
    yaml = YAML(typ="safe")
    with open(file_path, "rb") as doc:
        data = yaml.load(doc)
    # data = fix_yaml(data)
    return data


def write_yaml(file_path: str, content: dict) -> None:
    yaml = YAML()
    yaml.default_flow_style = False

    with open(file_path, "wb") as f:
        yaml.dump(content, f)


def get_file(fi: str) -> File:
    reopen = open(fi, "rb")
    django_file = File(reopen)
    return django_file


class Organisation(models.Model):
    # for twitter card and ciations 'ny times'
    name = models.CharField(max_length=255, blank=True, null=True)
    slug = models.CharField(max_length=255, blank=True, null=True)
    # for twitter card 'ny times'
    twitter = models.CharField(max_length=255, blank=True, null=True)
    ga_code = models.CharField(
        max_length=255, blank=True, null=True
    )  # for google analytics
    ga_cookies = models.BooleanField(default=True)
    publish_root = models.URLField(max_length=255, blank=True, null=True)
    include_favicon = models.BooleanField(default=True)
    icon = models.CharField(max_length=255, blank=True, null=True)
    default_values = JsonBlockField(default={})
    commands = JsonBlockField(default={})
    extra_values = JsonBlockField(default={})

    def __init__(self, *args, **kwargs) -> None:
        """
        make extra values directly accessible from the object
        """
        super().__init__(*args, **kwargs)
        self.__dict__.update(self.extra_values)

    @property
    def storage_dir(self) -> str:
        return settings.ORGS[self.slug]["storage_dir"]

    @property
    def publish_dir(self) -> str:
        alt_path = os.path.join(self.storage_dir, "_publish")
        return settings.ORGS[self.slug].get("publish_dir", alt_path)

    @property
    def template_dir(self) -> str:
        template_dir = os.path.join(self.storage_dir, "_templates")
        if os.path.exists(template_dir):
            return template_dir
        else:
            return None

    def relative_icon_path(self) -> str:
        """
        resolve for local org static dirs
        """
        if self.icon:
            relative_org_static = "orgs/{0}/".format(self.slug)
            return relative_org_static + self.icon

    def org_scss(self, filename: str = "main.scss") -> str:
        """
        is there a local scss file to use
        """
        scss_file = os.path.join(self.storage_dir, "_static", "scss", filename)

        scss_file_rel = os.path.join("orgs", self.slug, "scss", filename)
        if os.path.exists(scss_file):
            return scss_file_rel

    def org_scss_screenshot(self):
        """
        is there a local scss file to use for screenshots
        """
        return self.org_scss("screenshot.scss")

    def load_from_yaml(self) -> None:
        data = get_yaml(os.path.join(self.storage_dir, "_conf", "settings.yaml"))
        ignore = ["orglinks"]
        change = False

        for k in list(self.extra_values.keys()):
            if k not in data:
                del self.extra_values[k]

        for k, v in data.items():
            if k not in ignore:
                if hasattr(self, k):
                    current = getattr(self, k)
                    if current != v:
                        setattr(self, k, v)
                        change = True
                else:
                    current = self.extra_values.get(k)
                    if current != v:
                        self.extra_values[k] = v
                        change = True

        self.save()

        if "orglinks" in data:
            self.org_links.all().delete()
            orglinks = data["orglinks"]
            links = []
            for k, v in orglinks.items():
                o = OrgLinks(org=self, name=k, link=v["link"], order=v["order"])
                links.append(o)
            OrgLinks.objects.bulk_create(links)

    def org_links_ordered(self) -> QuerySet:
        return self.org_links.all().order_by("order")

    def stylesheet_min(self):
        if self.stylesheet:
            head, tail = os.path.splitext(self.stylesheet)
            return head + ".min" + tail

    def safe_css(self):
        """
        return useable css code
        """
        return mark_safe(self.custom_css)

    def display_fonts(self):
        for f in self.fonts.split("\n"):
            yield f.strip()

    def __str__(self):
        return self.name

    def get_ga_code(self) -> str:
        if self.ga_code:
            return self.ga_code
        else:
            try:
                return settings.GA_CODE
            except Exception:
                return ""


def org_source_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return "org_{0}/sources/{1}".format(instance.org_id, filename)


def kindle_source_storage(instance: Article, filename: str) -> str:
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return "kindle/org_{0}/{1}".format(instance.org_id, filename)


class OrgLinks(models.Model):
    org = models.ForeignKey(
        Organisation, related_name="org_links", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255)
    link = models.URLField(max_length=255)
    order = models.IntegerField(default=0)


class Chrome(object):
    """
    stores selenium driver to reduce time spent after
    first start up
    """

    driver = None

    @classmethod
    def get_driver(cls) -> WebDriver:
        if cls.driver:
            return cls.driver

        options = webdriver.ChromeOptions()
        options.add_argument("headless")
        options.add_argument("hide-scrollbars")
        options.add_argument("--no-sandbox")
        cls.driver = webdriver.Chrome(
            executable_path=chrome_driver_path, options=options
        )
        return cls.driver

    @classmethod
    def quit(cls) -> None:
        if cls.driver:
            cls.driver.quit()
        cls.driver = None

    def __del__(self):
        if self.driver:
            self.driver.quit()
        super(Chrome, self).__del__()


class Article(models.Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    short_title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(default="")
    byline = models.CharField(max_length=255, blank=True, null=True)
    current_version = models.IntegerField(default=0, null=True)
    copyright = models.TextField(max_length=255, blank=True, null=True)
    authors = models.TextField(null=True)
    file_source = models.CharField(max_length=255, null=True, blank=True)
    slug = models.CharField(max_length=255, blank=True, null=True)
    last_updated = models.DateTimeField(blank=True, null=True)
    publish_date = models.DateField(blank=True, null=True)
    cite_as = models.CharField(max_length=255, null=True, blank=True)
    seed = models.IntegerField(default=13)
    org = models.ForeignKey(
        Organisation,
        null=True,
        blank=True,
        related_name="articles",
        on_delete=models.CASCADE,
    )
    book_cover = models.ImageField(
        upload_to=kindle_source_storage, null=True, blank=True
    )
    kindle_location = models.CharField(max_length=255, null=True, blank=True)
    multipage = models.BooleanField(default=False)
    first_section_name = models.CharField(max_length=255, default="start", blank=True)
    pdf_file = models.CharField(max_length=255, default="", blank=True)
    pdf_location = models.CharField(max_length=255, default="", blank=True)
    needs_processing = models.BooleanField(default=False)
    reprocess_source = models.BooleanField(default=False)
    production_url = models.URLField(default="")
    display_notes = models.BooleanField(default=False)
    display_footnotes_at_foot = models.BooleanField(default=True)
    display_toc = models.BooleanField(default=False)
    include_citation = models.BooleanField(default=False)
    extra_values = JsonBlockField(default={})
    commands = JsonBlockField(default={})

    def __init__(self, *args, **kwargs) -> None:
        """
        make extra values directly accessible from the object
        """
        super().__init__(*args, **kwargs)
        self.__dict__.update(self.extra_values)

    @property
    def storage_dir(self):
        return os.path.join(self.org.storage_dir, "_docs", self.slug)

    def org_related_links(self) -> List[List[str]]:
        items = []
        if hasattr(self, "repo_entry") and self.repo_entry:
            items.append([self.repo_entry, "About this publication"])
        for link in self.org.org_links_ordered():
            items.append([link.link, link.name])
        return items

    def split_title(self) -> str:
        """
        return title - but try and split if possible
        """
        title = self.title
        title = title.replace("-", "&#8209;")

        if self.subtitle:
            return title
        if ":" in title:
            return title.split(":")[0].strip() + ":"
        elif "?" in title:
            return title.split("?")[0].strip() + "?"
        else:
            return title

    def split_subtitle(self) -> None:
        """
        return subtitle if present, or try and split
        the title
        """
        if self.subtitle:
            return self.subtitle
        if ":" in self.title:
            return self.title.split(":")[1].strip()
        elif "?" in self.title:
            return self.title.split("?")[1].strip()

    def pdf_url(self) -> str:
        """
        returns either the external location
        or the local pdf location
        """
        if self.pdf_location:
            return self.pdf_location
        elif self.pdf_file:
            return self.url() + "{0}.pdf".format(self.slug)
        else:
            return None

    def load_from_yaml(self, storage_dir: Path, refresh_header: bool = False) -> None:
        """
        Load config for the article from the stored file
        """
        print("loading yaml")
        data = get_yaml(os.path.join(storage_dir, "settings.yaml"))
        ignore = ["header", "book_cover"]

        existing_keys = list(self.extra_values.keys())
        for k in existing_keys:
            if k not in data:
                del self.extra_values[k]

        # adapation for older files
        if "sections_over_pages" in data:
            data["multipage"] = data["sections_over_pages"]
            del data["sections_over_pages"]

        if "pdf" in data:
            data["pdf_file"] = data["pdf"]
            del data["pdf"]

        if "pdf_file" not in data and self.pdf_file:
            self.pdf_file = ""

        for k, v in self.org.default_values.items():
            if k not in data:
                print("adding {0} value".format(k))
                rendered_v = Template(v).render(Context({"article": data}))
                data[k] = rendered_v

        for k, v in data.items():
            if k not in ignore:
                if hasattr(self, k) and k not in existing_keys:
                    setattr(self, k, v)
                else:
                    print(k, v)
                    self.extra_values[k] = v

        if "header" in data:
            header = data["header"]
            file_name = header["location"]
            if os.path.exists(file_name) is False:
                file_name = os.path.join(
                    self.org.storage_dir, "_docs", self.slug, file_name
                )
            file_ext = os.path.splitext(file_name)[1]
            internal_name = self.slug + file_ext
            image_size = header.get("size", "6")
            if image_size == "background":
                image_size = -1
            self.add_image(
                file_name,
                refresh=refresh_header,
                internal_name=internal_name,
                title_image=True,
                size=image_size,
            )

        if "book_cover" in data:
            print("loading book cover")
            file_name = data["book_cover"]
            if os.path.exists(file_name) is False:
                file_name = os.path.join(
                    self.org.storage_dir, "_docs", self.slug, file_name
                )
            self.get_book_cover(file_name)

        if "production_url" not in data:
            self.production_url = self.org.publish_root + self.slug + "/"

        if os.path.exists(self.file_source) is False:
            self.file_source = os.path.join(storage_dir, self.file_source)

        self.last_updated = now()
        self.save()

    def yaml_export(self, folder):
        basic_settings = [
            "title",
            "short_title",
            "slug",
            "description",
            "byline",
            "current_version",
            "copyright",
            "authors",
            "cite_as",
            "file_source",
            "publish_date",
            "multipage",
            "pdf_location",
            "production_url",
            "display_notes",
            "display_footnotes_at_foot",
            "repo_entry",
            "bottom_iframe",
        ]

        # load into dict
        output = OrderedDict()
        for b in basic_settings:
            output[b] = getattr(self, b)

        # dump to file

        filename = os.path.join(folder, "settings.yaml")
        yaml = YAML()
        yaml.default_flow_style = False
        with open(filename, "wb") as f:
            yaml.dump(output, f)

    def export_paragraph_images(self, folder: str, refresh_all: bool = False) -> None:
        """
        exports a folder of images - 1 for each element labeled with the
        combo key
        """
        import base64
        from io import BytesIO

        BAKE_SERVER = "http://127.0.0.1:8000"

        url = self.social_url().replace(settings.SITE_ROOT, BAKE_SERVER)
        url = url + "?id={0}&screenshot=true".format(self.id)
        c = self.display_content()
        grafs_to_do = []
        for g in c.all_grafs():
            g.destination_location = os.path.join(
                folder, "{0}.png".format(g.combo_key())
            )
            if os.path.exists(g.destination_location) and refresh_all is False:
                continue
            if g.plain_txt.strip() == "" or "[asset:" in g.plain_txt.lower():
                continue
            grafs_to_do.append(g)

        if len(grafs_to_do) == 0:
            return None

        driver = Chrome.get_driver()
        driver.set_page_load_timeout(60)
        print(url)
        driver.set_window_size(520, 568)
        driver.get(url)

        for g in grafs_to_do:
            print(g.order, g.combo_key())
            try:
                element = driver.find_element_by_xpath(
                    "//div[@id='r{0}']".format(g.order)
                )
            except common.exceptions.NoSuchElementException:
                print("skipping - element {0} not found".format(g.order))
                continue
            location = element.location
            size = element.size

            offset = 50
            left_offset = 30
            # if g.blockquote:
            #    left_offset += 30

            driver.execute_script(
                "window.scrollTo(0, {0});".format(location["y"] - offset)
            )

            screenshot = driver.get_screenshot_as_base64()
            img = Image.open(BytesIO(base64.decodebytes(screenshot.encode("utf-8"))))
            width = 520
            height = int(width / 1.91)
            left = location["x"] - left_offset
            top = offset - 8
            right = left + 16 + width
            bottom = top + height  # size['height'] + 2

            elements = (int(left), int(top), int(right), int(bottom))
            im = img.crop(elements)
            im.save(g.destination_location)
        Chrome.quit()

    def reprocessing(self):
        return self.needs_processing or self.reprocess_source

    def search_url(self) -> str:
        if self.baking:
            return "search.html"
        else:
            return "search"

    def import_assets(self, asset_folder: Path, refresh: bool) -> None:
        """
        given the assets folder - loads all assets inside
        """
        yaml_file = os.path.join(asset_folder, "assets.yaml")
        if not os.path.isfile(yaml_file):
            return None
        data = get_yaml(yaml_file)
        slugs = []
        assets = []
        for i in data:
            for k, v in i.items():
                v["slug"] = k
                slugs.append(k)
                assets.append(v)
        Asset.objects.filter(article=self, slug__in=slugs).delete()
        slugs = []
        for a in assets:
            no_header = False
            if a["content_type"] == "table-no-header":
                a["content_type"] = "table"
                no_header = True

            f = Asset(
                article=self,
                slug=a["slug"],
                type=a["content_type"],
                alt_text=a.get("alt_text", a.get("caption", "")),
                caption=a.get("caption", ""),
                content=markdown.markdown(a.get("longdesc", "").replace("\n", "\n\n")),
                no_header=no_header,
            )
            file_name = "{0}.{1}".format(a["slug"], a["type"])
            file_path = os.path.join(asset_folder, file_name)
            if a["content_type"] == "image":
                reopen = open(file_path, "rb")
                filename = "{2}_{0}.{1}".format(a["slug"], a["type"], self.id)
                process_images = True
                if (
                    os.path.exists(os.path.join(settings.MEDIA_ROOT, filename))
                    and refresh is False
                ):
                    process_images = False
                django_file = File(reopen)
                suf = SimpleUploadedFile(
                    filename, django_file.read(), content_type="image/png"
                )
                f.image = suf
                django_file.close()
                f.size = a.get("size", 6)
                if process_images:
                    f.extra_values = {}
                    f.create_responsive(ignore_first=True)
                    f.create_tiny()

                if len(f.extra_values) == 0:
                    f.get_ratio()
                    f.get_average_color()
                    f.header_image_res()
            if "table" in a["content_type"]:
                f.chart = Chart(chart_type="table_chart", file_name=file_path)
            if a["content_type"] == "html":
                f.content_type = "html"
                f.type = Asset.RAW_HTML
                file_name = ".".join([a["slug"], a["type"]])
                file_path = os.path.join(asset_folder, file_name)
                f.content = QuickText().open(file_path).text
            print("saving {0}".format(f.slug))
            f.save()

    def prepare_assets(self) -> None:
        """
        if assets have a chart - produce the image
        """
        for a in self.assets.filter(regenerate_image_chart=True):
            if a.chart and a.chart.chart_type != "table_chart":
                print("making image for {0}".format(a.slug))
                a.get_chart_image()

    def tinify_headers(self) -> None:
        """
        creates tiny version of headers if needed
        """
        for h in self.images.filter(queue_tiny=True):
            h.create_tiny()
        self.images.filter(queue_tiny=True).update(queue_tiny=False)

    def authenticate(self, user, access):
        """
        is the current user allowed to use this article?
        """
        if user.is_staff:
            return True

        access = Access.objects.get_or_none(user=user, article=self)
        if access is None:
            return False

        if access.is_valid() is False:
            return False

        access.use_access()

        return access

    def get_book_cover(self, path: str) -> None:
        if os.path.exists(path):
            fi = get_file(path)
            self.book_cover.save("{0}-book-cover.tif".format(self.id), fi, save=True)
            fi.close()

    def cite_link(self, paragraph: Graf) -> str:
        """
        returns a citeable link depending on article settings
        """
        if hasattr(self, "baking") and self.baking:
            v = self.production_url
            if v[-1] != "/":
                v += "/"
            v += "l/{0}.html".format(paragraph.combo_key())
            return v
        else:
            return reverse(
                "redirect_link",
                args=(
                    self.slug,
                    paragraph.combo_key(),
                ),
            )

    def social_cite_link(self, paragraph: Graf) -> str:
        """
        returns a citeable link depending on article settings
        """

        v = "#" + paragraph.combo_key()

        if self.multipage:
            return (
                self.social_url() + paragraph._section.nav_url(include_anchor=False) + v
            )
        else:
            return self.social_url() + v

    def prep_image_lookup(self) -> None:
        images = self.images.all()
        self.image_lookup = {x.section_name: x for x in images}

    def add_image(
        self,
        file_location: str = "",
        image_vertical: str = "",
        internal_name: str = "",
        refresh: bool = False,
        **kwargs,
    ) -> HeaderImage:
        """
        create image entry
        """
        if internal_name == "":
            internal_name = os.path.split(file_location)[1]
        # delete alternative title if image has changed
        if kwargs.get("title_image", False) is True:
            q = HeaderImage.objects.filter(article=self, title_image=True)
            q = q.exclude(source_loc=file_location)
            if q.exists():
                print("found-deleting")
                q.delete()

        ni, created = HeaderImage.objects.get_or_create(
            article=self,
            source_loc=file_location,
        )
        for k, v in kwargs.items():
            setattr(ni, k, v)

        ni.save()
        if created is True or refresh is True or len(ni.extra_values) == 0:
            fi = get_file(file_location)
            ni.image.save(internal_name, fi, save=True)
            fi.close()
            if image_vertical:
                header, tail = os.path.splitext(internal_name)
                vert_file = header + "_vert" + tail
                fi = get_file(image_vertical)
                ni.image_vertical.save(vert_file, fi, save=True)
                fi.close()
            # ni.trigger_create_responsive()
            ni.extra_values = {}
            ni.create_responsive()
            ni.create_tiny()
            ni.get_ratio()
            ni.get_average_color()
            ni.header_image_res()
            ni.save()
        return ni

    def code_assets(self):
        """
        return all assets that have a code component
        """
        for a in self.assets.filter(active=True, type=Asset.RAW_HTML):
            yield a.render_code()

    def watch_and_regenerate(self):
        """
        regenerate if file changes
        """
        run = True
        last = None

        while run:
            current_mod = os.stat(self.file_source)[8]

            if last != current_mod:
                print("regenerating")
                self.load_from_file()
                self.process()
                last = current_mod
            time.sleep(2)

    def render_to_zip(
        self,
        zip_destination,
        extra_files: List[Tuple[Path, Path]] = [],
        *args,
        **kwargs,
    ):
        """
        render the article and return the location of a zip file
        """
        temp_folder = mkdtemp()
        self.render(destination=temp_folder, *args, **kwargs)
        for origin, dest in extra_files:
            dest_loc = Path(temp_folder, dest)
            shutil.copyfile(origin, dest_loc)
        shutil.make_archive(zip_destination, "zip", temp_folder)
        return zip_destination

    def render(
        self,
        destination: Path,
        url: None = None,
        plain: bool = True,
        kindle: bool = True,
        refresh_all: bool = False,
    ) -> None:
        """
        export this and supporting files to location
        """

        if url is None:
            url = self.production_url
        elif url != self.production_url:
            self.production_url = url
            self.save()

        if not url:
            raise ValueError("No valid sharing URl stated.")

        files = []

        # compress_static(files)
        self.prepare_assets()
        self.tinify_headers()

        from .views import (
            ArticleView,
            RedirectLink,
            TextView,
            TipueContentView,
            TipueSearchView,
            TOCView,
        )

        """
        create destination folders
        """
        dirs = [
            destination,
            os.path.join(destination, "static"),
            os.path.join(destination, "static", "css"),
            os.path.join(destination, "static", "CACHE"),
            os.path.join(destination, "static", "CACHE", "css"),
            os.path.join(destination, "static", "CACHE", "js"),
            os.path.join(destination, "static", "js"),
            os.path.join(destination, "static", "images"),
            os.path.join(destination, "media"),
            os.path.join(destination, "media", "paragraphs"),
            os.path.join(destination, "l"),
        ]

        # discovery is there is a specific org directory to copy across
        org_static_folder = os.path.join(self.org.storage_dir, "_static")
        if os.path.exists(org_static_folder):
            dirs.append(os.path.join(destination, "static", "orgs"))
            dirs.append(os.path.join(destination, "static", "orgs", self.org.slug))

        for d in dirs:
            if os.path.isdir(d) is False:
                os.makedirs(d)

        # set media urls to now be below where we start
        settings.MEDIA_URL = "media/"
        settings.SITE_ROOT = url
        settings.STATIC_URL = "static/"
        settings.COMPRESS_URL = "static/"
        settings.DEBUG = False
        settings.COMPRESS_ENABLED = True

        """
        move pdf if local
        """

        if self.pdf_file:
            source_file = os.path.join(
                self.org.storage_dir, "_docs", self.slug, self.pdf_file
            )
            dest_file = os.path.join(destination, "{0}.pdf".format(self.slug))
            shutil.copyfile(source_file, dest_file)

        extra_files = self.extra_values.get("copy_files", [])
        for f in extra_files:
            source_file = os.path.join(self.org.storage_dir, "_docs", self.slug, f)
            dest_file = os.path.join(destination, f)
            print("copying {0}".format(f))
            shutil.copyfile(source_file, dest_file)

        """
        generate paragraph images
        """
        self.export_paragraph_images(
            os.path.join(destination, "media", "paragraphs"), refresh_all=refresh_all
        )

        """
        subclass so we can amend article override settings - force paywall off
        """

        current_article = self
        current_article.__dict__.update(self.extra_values)

        class BakeArticleView(ArticleView):
            share_image = "{{SITE_ROOT}}/{{article.get_share_image}}"
            twitter_share_image = "{{SITE_ROOT}}/{{article.get_share_image}}"
            article_settings_override = {
                "paywall": False,
                "baking": True,
                "search": False,
            }

            def get_article(self, request, article_slug):
                return current_article

        class BakeTipueContentView(TipueContentView):
            article_settings_override = {
                "paywall": False,
                "baking": True,
                "search": True,
            }

        class BakeTipueSearchView(TipueSearchView):
            article_settings_override = {
                "paywall": False,
                "baking": True,
                "search": True,
            }

            def get_article(self, request, article_slug):
                return current_article

        class BakeTOCView(TOCView):
            article_settings_override = {
                "paywall": False,
                "baking": True,
                "search": False,
            }

        class BakePlainView(TextView):
            article_settings_override = {
                "paywall": False,
                "baking": True,
                "search": False,
            }

        article = self
        article.baking = True

        c = self.display_content()

        grafs = {x.long_combo_key(): x for x in c.all_grafs()}
        grafs.update({x.combo_key(): x for x in c.all_grafs()})
        paragraph_lookup = c.paragraph_lookup()

        for k, v in paragraph_lookup.items():
            shorter_link = ".".join(k.split(".")[:6])

            class BakeRedirectLinkView(RedirectLink):
                def load_article(self, request, article_slug, paragraph_slug):
                    self.article = article
                    self.article.baking = True
                    self.content = c
                    self.graf = None
                    if v is True:
                        self.graf = grafs.get(k, None)
                    elif v is not None:
                        self.graf = grafs.get(v, None)
                    if self.graf:
                        self.graf._article = article
                    else:
                        print("old tag: rendering {0}".format(k))
                    self.paragraph_tag = shorter_link

            args = ("blah", "blah")
            BakeRedirectLinkView.write_file(
                path=os.path.join(destination, "l", shorter_link + ".html"), args=args
            )

        if self.multipage:
            c = self.display_content()
            for s in c.sections:
                args = (self.slug, s.anchor())
                name = "{0}.html".format(s.anchor())
                BakeArticleView.write_file(
                    path=os.path.join(destination, name), args=args
                )

        args = (self.slug,)
        BakeArticleView.write_file(
            path=os.path.join(destination, "index.html"), args=args
        )
        BakeTipueSearchView.write_file(
            path=os.path.join(destination, "search.html"), args=args
        )
        BakeTipueContentView.write_file(
            path=os.path.join(destination, "tipuesearch_content.js"), args=args
        )
        BakeTOCView.write_file(path=os.path.join(destination, "toc.json"), args=args)

        if plain:
            BakePlainView.write_file(
                path=os.path.join(destination, "plain.html"), args=args
            )

        print("moving compressed files")

        self.compressed_files = [
            x[len(settings.COMPRESS_URL) :] for x in self.compressed_files
        ]

        for c in self.compressed_files:
            print(c)

        """
        move required static files
        """

        files = [
            "js//sweetalert2.all.min.js",
            "js//picturefill.min.js",
            "js//tipuesearch.min.js",
            "js//tipuesearch_set.js",
            "css//tipuesearch.css",
            "css//kindle.css",
            "css//text_mode.css",
            "css//fa_reduced.css",
        ]

        files.extend(self.compressed_files)

        folders = ["favicon", "licences", "font"]

        media = settings.MEDIA_ROOT

        for f in files:
            print(f)
            shutil.copyfile(finders.find(f), os.path.join(destination, "static", f))

        for f in folders:
            print(f)
            d = os.path.join(destination, "static", f)
            if os.path.isdir(d) is False:
                os.makedirs(d)
            sync(finders.find(f), d, "sync")

        """
        pull in org based static directories
        """

        org_directory = os.path.join(self.org.storage_dir, "_static")

        if os.path.exists(org_directory):
            d = os.path.join(destination, "static", "orgs", self.org.slug)
            sync(org_directory, d, "sync")

        """
        move media files - from headerimages and assets
        """

        for i in self.images.all():
            for f in i.get_all_files():
                print(f)
                if os.path.exists(os.path.join(media, f)):
                    shutil.copyfile(
                        os.path.join(media, f), os.path.join(destination, "media", f)
                    )

        for a in self.assets.filter(active=True):
            if a.image:
                for f in a.get_all_files():
                    shutil.copyfile(
                        os.path.join(media, f), os.path.join(destination, "media", f)
                    )
            if a.image_chart:
                print(a.image_chart.name)
                shutil.copyfile(
                    os.path.join(media, a.image_chart.name),
                    os.path.join(destination, "media", a.image_chart.name),
                )

        if kindle:
            self.create_kindle(destination, use_temp=True)
            self.create_ebook(destination)

    def create_ebook(self, destination: Path) -> None:
        from .views import EbookChapterView

        authors = self.authors.split(",") if self.authors else ""
        book = mkepub.Book(title=self.title, authors=authors)

        book.set_stylesheet(
            """.asset-long-desc{
                            display: None;
                            }"""
        )

        if self.book_cover and os.path.exists(self.book_cover.path):
            with open(self.book_cover.path, "rb") as file:
                book.set_cover(file.read())

        sections = []
        # iterate through sections:
        for s in self.content().sections:
            anchor = s.anchor()
            args = (self.slug, s.anchor())
            path = self.slug + "/epub/" + anchor
            request = RequestFactory().get(path)
            content = EbookChapterView.as_view(decorators=False)(request, *args).content
            content = content.decode("utf-8")
            content = content.replace('src="/media/', 'src="images/')
            book.add_page(s.name, content)

        media_files = []
        for a in self.assets.filter(active=True):
            if a.type == Asset.IMAGE:
                media_files.append(a.get_image_name(1200))
            if a.type == Asset.CHART:
                if a.chart.chart_type != "table_chart":
                    media_files.append(a.image_chart.name)

        for f in media_files:
            origin = os.path.join(settings.MEDIA_ROOT, f)
            with open(origin, "rb") as file:
                book.add_image(f, file.read())

        file_path = os.path.join(destination, self.slug + ".epub")
        if os.path.exists(file_path):
            os.remove(file_path)
        book.save(file_path)
        print("rendered epub")

    def create_kindle(self, destination: Path, use_temp: bool = False) -> None:
        """
        export views and supporting files to location and generate kindle file
        """

        from shutil import copyfile

        from .views import KindleNCX, KindleOPF, KindleView

        if use_temp:
            staging = mkdtemp()
        else:
            staging = destination

        if not os.path.exists(destination):
            os.makedirs(destination)
        if not os.path.exists(staging):
            os.makedirs(staging)

        # set media urls to now be below where we start

        self.prepare_assets()
        self.tinify_headers()

        settings.STATIC_URL = "./"
        settings.DEBUG = False

        args = (self.slug,)  # (self.short_title.replace(" ","-").lower(),)

        css_dir = os.path.join(staging, "css")
        if not os.path.exists(css_dir):
            os.makedirs(css_dir)

        media_dir = os.path.join(staging, "media")
        if not os.path.exists(media_dir):
            os.makedirs(media_dir)

        opf = os.path.join(staging, self.slug + ".opf")

        media_files = []
        for a in self.assets.filter(active=True):
            if a.type == Asset.IMAGE:
                media_files.append(a.get_image_name(1200))
            if a.type == Asset.CHART:
                if a.chart.chart_type != "table_chart":
                    media_files.append(a.image_chart.name)

        for f in media_files:
            copyfile(os.path.join(settings.MEDIA_ROOT, f), os.path.join(media_dir, f))

        KindleView.write_file(
            path=os.path.join(staging, "text.html"), args=args, minimise=False
        )
        KindleOPF.write_file(path=opf, args=args, minimise=False)
        KindleNCX.write_file(
            path=os.path.join(staging, "toc.ncx"), args=args, minimise=False
        )
        copyfile(
            finders.find(os.path.join("css", "kindle.css")),
            os.path.join(css_dir, "kindle.css"),
        )
        if self.book_cover and os.path.exists(self.book_cover.path):
            copyfile(self.book_cover.path, os.path.join(staging, "bookcover.jpg"))

        print("generating mobi")
        com = settings.KINDLEGEN_LOC + " " + opf
        os.system(com)

        if staging != destination:
            if os.path.exists(os.path.join(staging, self.slug + ".mobi")):
                print("copying to destination")
                shutil.copyfile(
                    os.path.join(staging, self.slug + ".mobi"),
                    os.path.join(destination, self.slug + ".mobi"),
                )
            else:
                print("error! kindle file not present")

    def social_url(self) -> str:
        """
        url the baker uses to render to the social settings
        """
        if hasattr(self, "baking") and self.baking:
            return self.production_url
        else:
            return self.url()

    def url(self, section: str = "") -> str:
        """
        get url of article (with section)
        """
        if hasattr(self, "baking") and self.baking:
            if section:
                return "./" + section + ".html"
            else:
                return "./"

        else:
            if section:
                args = (self.slug, section)
            else:
                args = (self.slug,)

            return settings.SITE_ROOT + reverse("article_view", args=args)

    def live_url(self):
        """
        return version for live site
        """
        return settings.LIVE_ROOT + reverse("article_view", args=(self.slug,))

    def year(self) -> int:
        """
        get year - 'now' if publication date not avaliable
        """
        if self.publish_date:
            return self.publish_date.year
        else:
            return datetime.datetime.now().year

    def run_command(self, command):
        """
        Run commands around process

        Typically preprocess, publish

        Prefer article to org level commands
        Org level commands working directory is the top level
        Article level commands working directory is the article folder

        python script.py {{article.slug}} - passes the slug

        """
        command_str = None
        if command in self.org.commands:
            command_str = self.org.commands[command]
            working_directory = self.org.storage_dir
        if command in self.commands:
            command_str = self.commands[command]
            working_directory = self.storage_dir

        if not command_str:
            print("No {0} command configured".format(command))
            return

        if command_str.startswith("module::"):
            module_path = command_str.replace("module::", "")
            module, item = module_path.split(":")
            if "$doc/" in module:
                module = module.replace("$doc/", "")
                file_path = Path(self.storage_dir) / module
            if "$org/" in module:
                module = module.replace("$org/", "")
                file_path = Path(self.org.storage_dir) / module
            spec = importlib.util.spec_from_file_location("module.name", file_path)
            my_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(my_module)
            detected_item = getattr(my_module, item)
            result = detected_item(self)
            # allow for classes to be instanced and then run
            if callable(result):
                result()
            return result

        # prevent execution by restricting to listed fields
        fields = self._meta.fields
        lookup_dict = {x.name: getattr(self, x.name) for x in fields if x.name != "org"}
        lookup_dict.update(self.extra_values)

        c_context = Context({"article": lookup_dict})

        rendered_command = Template(command_str).render(c_context)

        commands = rendered_command.split(" ")

        print("Running {0} commands".format(command))
        subprocess.call(commands, cwd=working_directory)
        print("{0} complete".format(command))

    def process(self) -> None:
        """
        creates the section and graf structure from raw markup
        """
        self.content().process()
        self.needs_processing = False
        self.save()

    def content(self) -> Version:
        """
        retrieve current version of content
        """
        q = Version.objects.filter(article=self, number=self.current_version)
        # error handling
        if q.count() > 1:
            print("deleting previous")
            q.delete()

        if not q.exists():
            print("creating new content")
            v = Version.objects.get_or_create(
                article=self, number=self.current_version
            )[0]
        else:
            v = q[0]
        return v

    def display_content(
        self, slugs: List[Any] = [], display_first_section: bool = False
    ) -> Version:
        """
        initialize the content for rendering
        """
        content = self.content()
        content.article = self
        content.load_sections(slugs, display_first_section=display_first_section)

        return content

    def load_from_file(self) -> None:
        """
        load markdown from file
        """
        with codecs.open(self.file_source, encoding="utf-8") as f:
            raw = f.read()
        if raw:
            c = self.content()
            c.raw = raw
            c.save()

    def title_image(self) -> Optional[HeaderImage]:
        """
        get the header image reference
        """
        images = self.images.filter(title_image=True).order_by("-id")
        if images.exists():
            return images[0]
        else:
            return None

    def get_share_image(self) -> Optional[str]:
        """
        return a filename for an social share
        """
        title_image = self.title_image()
        if title_image:
            return title_image.get_share_image()
        else:
            return None

    def headers_and_images(self) -> Iterator[HeaderImage]:
        """
        generator that returns the title image and image assets
        """
        title = self.title_image()
        if title:
            title.is_title = True
            yield title

        if hasattr(self, "cached_assets"):
            assets = self.cached_assets
        else:
            assets = self.assets.filter(active=True)

        for a in assets:
            if a.type == Asset.IMAGE:
                a.is_title = False
                yield a


class HeaderMixin(object):
    """
    converts images to various responsive sizes
    """

    def get_image_name(self, resolution: int, assume_tiny: bool = False) -> str:
        """
        returns big or small image depending if we've tinified
        """
        tiny = self.get_tiny_responsive_image_name(resolution)
        normal = self.get_responsive_image_name(resolution)
        options = [tiny, normal]
        if assume_tiny:
            return tiny
        for o in options:
            path = os.path.join(settings.MEDIA_ROOT, o)
            if os.path.exists(path):
                return o
        raise ValueError("{0} missing".format(path))

    def get_share_image(self) -> str:
        """
        return the large view display for header image
        """
        file_name = self.get_image_name(1200)
        if file_name[:2] == "./":
            file_name = file_name[2:]

        return settings.MEDIA_URL + file_name

    def get_responsive_image_name(self, resolution: int, webp: bool = False) -> str:
        """
        get the responsive image needed for each resolution
        """
        name, ext = os.path.splitext(self.image.name)
        if webp:
            ext = ".webp"
        return name + "_{0}".format(resolution) + ext

    def get_tiny_responsive_image_name(self, resolution: int) -> str:
        """
        get the responsive image needed for each resolution
        """
        name, ext = os.path.splitext(self.image.name)
        return name + "_{0}_tiny".format(resolution) + ext

    def header_image_res(self) -> List:
        return list(self._header_image_res())

    def get_ratio(self) -> float:
        ratio = self.extra_values.get("ratio", None)
        if not ratio:
            file_path = os.path.join(settings.MEDIA_ROOT, self.get_image_name(1440))
            image = Image.open(file_path)
            o_width, o_height = image.size
            image.close()
            ratio = float(o_height) / float(o_width)
            self.extra_values["ratio"] = ratio
        return ratio

    def get_average_color(self) -> str:
        color = self.extra_values.get("color", None)
        if not color:
            file_path = os.path.join(settings.MEDIA_ROOT, self.get_image_name(1440))
            image = Image.open(file_path)
            q = image.quantize(colors=2, method=2)
            color = q.getpalette()[:3]
            image.close()
            color = "#{:02x}{:02x}{:02x}".format(*color)
            self.extra_values["color"] = color
        return color

    def _header_image_res(self) -> Iterator[Tuple[str, str, int, int, int, int, int]]:
        """

        tell template about different resolutions
        """
        previous_width = 0
        ratios = self.extra_values.get("sizes", {})
        self.extra_values["sizes"] = ratios
        print("loading image resolution", self.image)
        for width in [768, 992, 1200, 1440, 1920]:
            image_name = settings.MEDIA_URL + self.get_image_name(
                width, assume_tiny=True
            )
            not_tiny_url = settings.MEDIA_URL + self.get_responsive_image_name(width)
            file_path = os.path.join(
                settings.MEDIA_ROOT, self.get_image_name(width, assume_tiny=True)
            )
            if str(width) in ratios:
                o_width, o_height = ratios[str(width)]
            else:
                image = Image.open(file_path)
                o_width, o_height = image.size
                ratios[width] = [o_width, o_height]
                image.close()
            webp_name = os.path.splitext(not_tiny_url)[0] + ".webp"
            ratio = int((float(o_height) / float(o_width)) * 100)
            self.extra_values["sizes"][width] = [o_width, o_height]
            yield image_name, webp_name, previous_width, width, o_width, o_height, ratio
            previous_width = width

    def largest_header(self):
        """
        get largest image size
        """
        return settings.MEDIA_URL + self.get_tiny_responsive_image_name(1440)

    def get_all_files(self) -> Iterator[str]:
        """
        get all files named for copying reasons
        """
        widths = [768, 992, 1200, 1440, 1920]
        for width in widths:
            yield self.get_responsive_image_name(width, webp=False)
            yield self.get_responsive_image_name(width, webp=True)
            yield self.get_tiny_responsive_image_name(width)

        yield self.image.name

    def create_tiny(self) -> None:
        """

        Passes up to tinyimg to reduce.
        """

        tinify.key = settings.TINY_PNG_KEY

        if hasattr(self, "image_vertical") and self.image_vertical:
            images = (
                (self.image_vertical, [768]),
                (self.image, [992, 1200, 1440, 1920]),
            )
        else:
            images = ((self.image, [768, 992, 1200, 1440, 1920]),)
        for i_file, res in images:
            for width in res:
                file_name = settings.MEDIA_ROOT + self.get_responsive_image_name(width)
                tiny_name = settings.MEDIA_ROOT + self.get_tiny_responsive_image_name(
                    width
                )
                if settings.TINY_PNG_KEY:
                    print("reducing using tinify")
                    source = tinify.from_file(str(file_name))
                    source.to_file(tiny_name)
                else:
                    # boring and simply reduction of file if not
                    # using tinify
                    print("using native to reduce")
                    img = Image.open(file_name)
                    img.save(tiny_name, optimize=True, quality=95)

    def create_responsive(self, ignore_first: bool = True) -> None:
        """
        creates the different sized versions of the header image.

        If vertical image will make the smaller one mirror that.

        Passes up to tinyimg to reduce.
        """

        if hasattr(self, "image_vertical") and self.image_vertical:
            images = (
                (self.image_vertical, [768]),
                (self.image, [992, 1200, 1440, 1920]),
            )
        else:
            images = ((self.image, [768, 992, 1200, 1440, 1920]),)

        pos = 0
        web_p_files = []
        for i_file, res in images:
            print("creating responsive versions")
            image = Image.open(i_file)
            o_width, o_height = image.size
            print(self.image.path)
            print(f"original width {o_width}, height {o_height}")

            size_adjustment = {}
            column_size = {}
            if isinstance(self, Asset):
                size_adjustment = {1920: -2, 1440: 2, 1200: 2, 992: 2, 768: 12}
                column_size = {1920: 970 * (5 / 6), 1440: 970 * (5 / 6)}
            for width in res:
                pos += 1
                # if display is being scaled down, reduce size of image
                new_width = width
                if (pos > 1 or ignore_first is False) and self.size != -1:
                    if width in column_size:
                        new_width = column_size[width]
                        print(f"forcing use of {new_width}")
                    else:
                        relative_size = self.size + size_adjustment.get(
                            width, 0
                        )  # in twelves
                        if relative_size > 12:
                            relative_size = 12
                        new_width = (float(new_width) / 12) * relative_size
                    print(
                        f"size={self.size},relative_size={relative_size},new_width={new_width} "
                    )

                    if new_width == 960:  # minor adaption so can appear full screen
                        new_width = 970
                    print("resizing to {0}".format(new_width))
                new_height = round(new_width * (float(o_height) / o_width))
                thumbnail = image.copy()
                print(f"{new_width=}, {o_width=}, {new_height=}")
                if new_width < o_width and new_width > 1 and new_height > 1:
                    thumbnail.thumbnail((new_width, new_height), Image.BICUBIC)
                else:
                    print("new size is larger than original, not downsizing")
                new_name = settings.MEDIA_ROOT + self.get_responsive_image_name(width)
                print("saving as {0}".format(new_name))
                if os.path.exists(new_name):
                    print("deleting")
                    os.remove(new_name)
                thumbnail.save(new_name)
                webp_name = os.path.splitext(new_name)[0] + ".webp"
                web_p_files.append([i_file.path, webp_name, new_width, new_height])
            if os.path.exists(i_file.path) is False:
                image.save(i_file.path)
            for source_name, dest, new_width, new_height in web_p_files:
                if os.path.exists(dest):
                    print("deleting")
                    os.remove(dest)
                print("creating webp")
                result = webp.cwebp(
                    source_name,
                    dest,
                    f"-lossless -q 100 -resize {new_width} {new_height}",
                )
                if os.path.exists(dest) is False:
                    print(result)
                    raise ValueError(
                        f"Webp {dest} not created, with settings:"
                        + f"-lossless -q 100 -resize {new_width} {new_height}"
                    )


class HeaderImage(FlexiBulkModel, HeaderMixin):
    title_image = models.BooleanField(default=False)
    section_name = models.CharField(max_length=255, null=True, blank=True)
    source_loc = models.CharField(max_length=255, null=True, blank=True)
    image = models.ImageField(null=True, blank=True, storage=OverwriteStorage())
    image_vertical = models.ImageField(null=True, blank=True)
    image_alt = models.CharField(max_length=255, null=True, blank=True)
    article = models.ForeignKey(
        Article, related_name="images", on_delete=models.CASCADE
    )
    size = models.IntegerField(default=0)
    queue_responsive = models.BooleanField(default=False)
    queue_tiny = models.BooleanField(default=False)
    extra_values = JsonBlockField(default={})


class Version(models.Model):
    article = models.ForeignKey(
        Article, related_name="versions", on_delete=models.CASCADE
    )
    number = models.IntegerField()
    label = models.CharField(max_length=255, blank=True, null=True)
    raw = models.TextField(blank=True, null=True)
    sections = JsonBlockField(blank=True, null=True)
    paragraph_links = JsonBlockField(blank=True, null=True)
    has_notes = models.BooleanField(default=False)

    def load_from_file(self):
        with codecs.open(self.article.file_source, encoding="utf-8") as f:
            raw = f.read()
        if raw:
            self.raw = raw
            self.save()

    def section_link_lookup(self):
        """
        creates a lookup for tags to order
        """
        di = {}
        for s in self.sections:
            di[s.anchor()] = s
            for g in s.grafs:
                di[g.anchor] = s
        return di

    def tag_lookup(self):
        """
        creates a lookup for tags to order
        """
        if hasattr(self, "_tag_lookup") is False:
            di = {}
            for s in self.sections:
                di.update(s.tagged)
            self._tag_lookup = di
        return self._tag_lookup

    @classmethod
    def restricted(cls, article, slugs=[], **kwargs):
        """
        generates a restricted version for display purposes that doesn't load
        the raw text
        """
        if "slugs" in kwargs:
            slugs = kwargs["slugs"]
            del kwargs["slugs"]
        kwargs["article"] = article
        query = cls.objects.filter(**kwargs)
        if query.exists():
            values = query.values(
                "pk", "id", "number", "label", "sections", "has_notes"
            )[0]
            props = {"article": article}
            props.update(values)
            v = cls(**props)
        v.load_sections(slugs)
        return v

    def load_sections(
        self, slugs: List[Any], display_first_section: bool = False
    ) -> None:
        """
        construct a self.sections connected to the content
        """

        for s in self.sections:
            s._version = self
            if s.anchor() in slugs or slugs == []:
                s.active_section = True
            else:
                s.active_section = False
            if display_first_section:
                if s.order == 1:
                    s.active_section = True
                else:
                    s.active_section = False

    def used_assets(self) -> List[Any]:
        """
        slugs for assets used by this version
        """
        assets = []
        for s in self.sections:
            assets.extend(s.used_assets())
        return assets

    def display_sections(self) -> Iterator[Section]:
        for s in self.sections:
            if s.has_grafs() and s.active_section:
                yield s

    def toc(self, levels=None):
        """
        return a set of links for the different parts
        """

        class Link(object):
            def __init__(self, **kwargs):
                self.id = 0
                self.order = 0
                self.anchor = ""
                self.nav_url = ""
                self.name = ""
                self.level = 1
                self.__dict__.update(kwargs)
                self._toc = None

            @property
            def collection(self):
                return self._toc.items

            def future(self):
                if self.order + 1 < len(self.collection):
                    return self.collection[self.order + 1]
                return None

            def future_level_difference(self):
                f = self.future()
                if not f:
                    return 0
                return f.level - self.level

            def has_children(self):
                f = self.future()
                if not f:
                    return False
                else:
                    return f.level > self.level

            def caret_title(self):
                """
                splits title into layers based on words
                to stop very long horizontal titles in submenus
                """

                def character_group(v):
                    limit = 35
                    words = v.split(" ")
                    groups = []
                    current = []
                    count = 0
                    for w in words:
                        count += len(w)
                        current.append(w)
                        if count > limit:
                            groups.append(" ".join(current))
                            current = []
                            count = 0
                    if current:  # final set
                        groups.append(" ".join(current))

                    return "<br>".join(groups)

                return mark_safe(character_group(self.name))

            def children(self):
                future = self._toc.items[self.order + 1 :]
                children = []
                for i in future:
                    if i.level == self.level:
                        break
                    if i.level == self.level + 1:
                        children.append(i)
                return children

        class Toc(object):
            def __init__(self):
                self.items = []

            def final_level(self):
                return self.items[-1].level

            def final_level_range(self):
                return range(0, self.final_level())

            def final_level_range_left_open(self, offset=1):
                item = 0
                for i in self.items[::-1]:
                    if i.level in [1, 2]:
                        item = i.level
                        break
                return range(0, item - offset)

            def final_level_range_left_open_minus_one(self):
                return self.final_level_range_left_open(2)

            def add(self, **kwargs):
                item = Link(**kwargs)
                item.order = len(self.items)
                item._toc = self
                self.items.append(item)

            def top_two_levels(self):
                items = []
                for i in self.items:
                    if i.level in [1, 2]:
                        items.append(i)

                for l in range(0, len(items)):
                    current = items[l]
                    current_level = current.level
                    if l < len(items) - 1:
                        next = items[l + 1]
                        next_level = next.level
                    else:
                        next_level = 0
                    current.reduced_diff = next_level - current_level
                    yield current

            def __iter__(self):
                for i in self.items:
                    yield i

            def level_1(self):
                """
                get just top level (sections)
                """
                for s in self:
                    if s.level == 1:
                        yield s

        toc = Toc()

        stand_in_introduction = "Introduction"

        for s in self.sections:
            if s.name == stand_in_introduction:
                stand_in_introduction = "Summary"
                break

        for s in self.sections:
            if s.has_grafs():
                name = s.name
                if s.order == 1 and not name:
                    name = stand_in_introduction
                if name:
                    toc.add(
                        name=name,
                        anchor=s.anchor(),
                        nav_url=s.nav_url(),
                        id=s.order,
                        level=1,
                    )
                for g in s.get_grafs():
                    if g.title:
                        toc.add(
                            name=g.title,
                            anchor=g.anchor(),
                            nav_url=g.nav_url(),
                            id=g.order,
                            level=g.header_level,
                        )
        return toc

    def anchors(self) -> Iterator[Dict[str, Union[str, int]]]:
        """
        for kindle
        """

        def y(title, anchor, count):
            return {"title": title, "anchor": anchor, "count": count}

        yield y("Table of Contents", "toc", "1")
        count = 2
        for s in self.toc():
            indent = s.level - 1
            i = "".join(["-" for x in range(0, indent)])
            if i:
                i = i + " "
            if s.name:
                yield y(i + s.name, s.anchor, count)
                count += 1

        if self.footnotes():
            yield y("Notes", "refs", count)
            count += 1

    def all_grafs(self) -> Iterator[Graf]:
        """
        return all graphs across all sections
        """

        for s in self.sections:
            for g in s.grafs:
                g._section = s
                yield g

    def get_paragraph(self, code="", first_para_slug=None):
        """
        return graf and section objects given link code
        """

        if first_para_slug:
            for s in self.sections:
                if s.anchor() == first_para_slug:
                    return (s.grafs[0], s)

        splits = code.split(".")

        if len(splits) == 5:
            parent, paragraph_key, key, start_key, end = splits
            letter_key = ""
        elif len(splits) == 6:
            parent, paragraph_key, key, letter_key, start_key, end = splits

        keys = {
            "parent_id": parent,
            "order": paragraph_key,
            "letter_key": letter_key,
            "key": key,
            "start_key": start_key,
            "end_key": end,
        }

        methods = [
            ["key"],
            ["letter_key"],
            ["start_key", "end_key"],
            ["start_key", "order"],
            ["start_key"],
            ["end_key"],
            ["order", "parent_id"],
        ]

        for m in methods:
            matches = []
            for s in self.sections:
                for g in s.grafs:
                    score = 0
                    for rule in m:
                        if getattr(g, rule) == keys[rule]:
                            score += 1

                    if score == len(m):
                        matches.append((g, s))
            if len(matches) == 1:
                return matches[0]  # paragraph, section
        return None, None

    def footnotes(self) -> List[Any]:
        notes = []
        for s in self.sections:
            if s.active_section:
                for g in s.get_grafs():
                    for s in g.self_and_extras():
                        if s.footnotes and s.visible:
                            for f in s.footnotes:
                                notes.append(f)
        return notes

    def source_paragraph_links_from_render(self) -> List[Any]:
        """
        For converting older versions
        Extract from previously rendered links
        older paragraph keys
        """
        bake_folder = self.article.org.publish_dir
        path = os.path.join(bake_folder, self.article.slug, "l")
        if not os.path.exists(path):
            return []

        files = os.listdir(path)
        files = [os.path.splitext(x)[0] for x in files]
        return files

    def load_paragraph_links(self) -> None:
        para_file = os.path.join(
            self.article.org.storage_dir, "_docs", self.article.slug, "_paragraphs.yaml"
        )
        if os.path.exists(para_file):
            self.paragraph_links = get_yaml(para_file)
        else:
            self.paragraph_links = []

    def save_paragraph_links(self) -> None:
        para_file = os.path.join(
            self.article.org.storage_dir, "_docs", self.article.slug, "_paragraphs.yaml"
        )
        write_yaml(para_file, self.paragraph_links)

    def paragraph_lookup(self) -> Dict[str, Optional[Union[bool, str]]]:
        """
        returns a dictionary of current
        graf status.
        True = existing graf
        'reference' = graf this now maps to
        None = no good mappng
        """
        lookup = {}
        for r in self.paragraph_links:
            if r:
                lookup.update(r)
        return lookup

    def update_paragraph_links(self) -> None:
        """
        upgrade the list of paragraph links (past and present)
        """

        def six_from_seven(key):
            parts = key.split(".")
            return ".".join(parts[:6])

        self.load_paragraph_links()
        paragraph_lookup = self.paragraph_lookup()

        existing_grafs = []
        for s in self.sections:
            for g in s.grafs:
                key = g.long_combo_key()
                existing_grafs.append(key)
                if paragraph_lookup.get(key, True) == None:
                    paragraph_lookup[key] = True

        short_keys = [six_from_seven(x) for x in paragraph_lookup.keys()]

        from_render = self.source_paragraph_links_from_render()
        print("{0} previously rendered".format(len(from_render)))
        new_render = [x for x in from_render if x not in short_keys]
        print("{0} old links found".format(len(new_render)))
        for n in new_render:
            paragraph_lookup[n] = None

        new_existing_grafs = [x for x in existing_grafs if x not in paragraph_lookup]

        orphan_grafs = []
        for k, v in paragraph_lookup.items():
            if k not in existing_grafs:
                if v not in existing_grafs:
                    orphan_grafs.append(k)

        print("{0} new paragraph links".format(len(new_existing_grafs)))

        orphan_mappings = self.anchor_orphans(existing_grafs, orphan_grafs)
        paragraph_lookup.update(orphan_mappings)

        new_paragraph_links = []

        for i in self.paragraph_links:
            if i:
                key = list(i.keys())[0]
                new_paragraph_links.append({key: paragraph_lookup[key]})

        for i in new_existing_grafs:
            new_paragraph_links.append({i: True})

        for i in new_render:
            new_paragraph_links.append({i: paragraph_lookup[i]})

        self.paragraph_links = new_paragraph_links
        self.save_paragraph_links()

    def anchor_orphans(self, all_grafs: List[str], orphan_grafs: List[str]) -> dict:
        """
        given orphan paragraphs, match to better ones
        """

        class MiniGraf(object):
            order = [
                "para_key_position",
                "para_key",
                "letter_key",
                "start_and_end",
                "fuzzy_match",
                "start_and_pos",
                "end_and_pos",
                "start_key",
                "end_key",
                "pos_and_section",
            ]

            def __init__(self, key):
                self.key = key
                parts = key.split(".")
                if len(parts) == 5:
                    parts.extend([None, None])
                if len(parts) == 6:
                    parts.extend([None])

                self.section = parts[0]
                self.para_pos = parts[1]
                self.para_key = parts[2]
                self.start_key = parts[3]
                self.end_key = parts[4]
                self.letter_key = parts[5]
                self.letter_seq = parts[6]

                self.para_key_position = self.para_pos + self.para_key
                self.start_and_end = self.start_key + self.end_key
                self.start_and_pos = self.start_key + self.para_pos
                self.end_and_pos = self.end_key + self.para_pos
                self.pos_and_section = self.section + self.para_pos
                self.match = None

                self.fuzzy_distance = 7

            def check_match(self, other, key):
                return getattr(self, key) == getattr(other, key)

            def fuzzy_match(self, candidates):
                matches = []
                for c in candidates:
                    if self.letter_seq and c.letter_seq:
                        c.distance = lev.distance(self.letter_seq, c.letter_seq)
                        if c.distance <= self.fuzzy_distance:
                            matches.append(c)
                if matches:
                    print("{0} matched fuzzy".format(self.key))
                    matches.sort(key=lambda x: x.distance)
                    self.match = matches[0].key

            def find_match(self, candidates):
                for s in MiniGraf.order:
                    if s == "fuzzy_match":
                        self.fuzzy_match(candidates)
                        if self.match == None:
                            continue
                        else:
                            return
                    matches = []
                    for c in candidates:
                        if self.check_match(c, s):
                            matches.append(c.key)
                    if len(matches) == 1:
                        print("matched {1} {0}".format(s, self.key))
                        self.match = matches[0]
                        return

        candidates = [MiniGraf(x) for x in all_grafs]
        orphans = [MiniGraf(x) for x in orphan_grafs]

        for o in orphans:
            o.find_match(candidates)

        return {x.key: x.match for x in orphans}

    def process(self) -> None:
        """
        creates the section and graf structure from raw markup
        """
        self.article.assets.all().update(active=False)
        if not self.raw:
            self.load_from_file()
        process_ink(self, self.raw)
        self.update_paragraph_links()
        first_section = "start"
        if self.sections:
            if self.sections[0].name:
                first_section = self.sections[0].anchor()
        self.first_section_name = first_section

        self.last_updated = now()
        self.save()

    def save(self, *args, **kwargs) -> None:
        """
        increment versioning if copy has changed

        if article is multi_sections - save as independent objects
        """

        if self.id:
            old_v = Version.objects.get(id=self.id)
            should_save = old_v.raw != self.raw
        else:
            should_save = True

        if should_save:
            self.number += 1
            self.article.current_version += 1
            Article.objects.filter(id=self.article_id).update(
                current_version=self.number
            )

        super(Version, self).save(*args, **kwargs)


class Asset(FlexiBulkModel, HeaderMixin):
    RAW_HTML = "h"
    IMAGE = "i"
    CHART = "c"
    types = ((RAW_HTML, "html"), (IMAGE, "image"), (CHART, "chart"))

    article = models.ForeignKey(
        Article, related_name="assets", null=True, on_delete=models.CASCADE
    )
    slug = models.CharField(max_length=255, null=True)
    type = models.CharField(max_length=2, choices=types, null=True)
    location = models.CharField(max_length=255, null=True)
    chart = ChartField(null=True, blank=True)
    image_chart = models.ImageField(null=True, blank=True, storage=OverwriteStorage())
    regenerate_image_chart = models.BooleanField(default=False)
    image = models.ImageField(null=True, blank=True, storage=OverwriteStorage())
    size = models.IntegerField(default=0)
    alt_text = models.CharField(max_length=255, null=True, blank=True)
    caption = models.CharField(max_length=255, null=True, blank=True)
    content = models.TextField(null=True)
    code_content = models.TextField(null=True)
    no_header = models.BooleanField(default=False)
    active = models.BooleanField(default=False)
    extra_values = JsonBlockField(default={})

    def search_name(self):
        txt = ""
        if self.caption:
            txt = self.caption
        elif self.alt_text:
            txt = self.alt_text
        txt = txt.encode("ascii", "ignore")
        txt = txt.replace(b"[", b"").replace(b"]", b"").replace(b"\n", b"")
        return txt.decode("utf-8")

    def escape_text(self):
        txt = self.content
        txt = txt.replace("<p>", "")
        txt = txt.replace("</p>", "")
        txt = txt.encode("ascii", "ignore")
        txt = txt.replace(b"[", b"").replace(b"]", b"").replace(b"\n", b"")
        return txt.decode("utf-8")

    def get_chart_image(self):
        """
        loads the chart in selenium so we can fetch the image version
        """
        import io
        import tempfile

        from selenium import webdriver

        from .views import AssetView

        temp_dir = tempfile._get_default_tempdir()
        temp_name = next(tempfile._get_candidate_names())
        file_destination = os.path.join(temp_dir, temp_name + ".html")
        address = "file:///" + file_destination.replace("\\", "/")
        AssetView.write_file(
            args=(self.article.slug, self.slug, "yes"), path=file_destination
        )
        driver = webdriver.Firefox()
        driver.get(address)
        elem = driver.find_element_by_id(self.chart.ident)
        contents = elem.get_attribute("innerHTML")
        contents = contents.replace('<img src="data:image/png;base64,', "")[:-2]
        driver.quit()
        image_output = io.StringIO()
        # Write decoded image to buffer
        image_output.write(contents.decode("base64"))
        image_output.seek(0)  # seek beginning of the image string

        suf = SimpleUploadedFile(
            "{0}.png".format(self.chart.ident),
            image_output.read(),
            content_type="image/png",
        )

        self.image_chart = suf
        self.regenerate_image_chart = False
        self.save()

        os.remove(file_destination)

    def add_image(self, file_location):
        """
        add image from file location
        """

        def get_file(fi):
            reopen = open(fi, "rb")
            django_file = File(reopen)
            return django_file

        head, tail = os.path.splitext(file_location)

        self.image.save(self.slug + tail, get_file(file_location), save=True)

    def get_text_from_file(self):
        """
        extract content for a html asset
        """
        with codecs.open(self.location, encoding="utf-8") as f:
            raw = f.read()
        if "---CODE---" in raw:
            self.content, self.code_content = raw.split("---CODE---")
        else:
            self.content = raw
        self.save()

    def render_image(self, basic=False, chart_alt=False, kindle=False, header=False):
        """
        get image ready for render
        """

        if chart_alt:
            image = self.image_chart
        else:
            image = self.image

        url = settings.MEDIA_URL + self.get_image_name(1200)
        if settings.MEDIA_URL not in url and url[0] == "/":
            url = url[1:]

        if hasattr(self.article, "baking") and self.article.baking:
            url = self.article.production_url + url
        if kindle and url[0] == "/":
            url = url[1:]
        if self.alt_text:
            at = self.alt_text
        else:
            at = self.caption

        if self.caption is None:
            self.caption = ""

        if basic:
            template = "charts//basic_image.html"
        else:
            template = "charts//responsive_image.html"

        context = {
            "kindle": kindle,
            "asset": self,
            "source": url,
            "alt": escape(at),
            "title": escape(self.caption),
            "caption": self.caption,
            "header": header,
        }

        rendered = render_to_string(template, context)
        return mark_safe(rendered)

    def render_code(self):
        return mark_safe(self.code_content)

    def render(self, basic=False, kindle=False, header=False):
        if self.type == Asset.RAW_HTML:
            return mark_safe(self.content)
        if self.type == Asset.IMAGE:
            return self.render_image(
                basic=basic, chart_alt=False, kindle=kindle, header=header
            )
        if self.type == Asset.CHART:
            if self.chart.chart_type == "table_chart":
                if basic:
                    return self.chart.render_html_table(self.caption, self.no_header)
                else:
                    return self.chart.render_bootstrap_table(
                        self.caption, self.no_header
                    )
            else:
                if basic:
                    return self.render_image(basic=basic, chart_alt=True)
                else:
                    return self.chart.render_div(self.caption)

    def save(self, *args, **kwargs):
        if self.image:
            self.type = Asset.IMAGE
        elif self.chart:
            self.type = Asset.CHART
        elif self.content:
            self.type = Asset.RAW_HTML
        if self.content is None and self.type == Asset.RAW_HTML:
            self.get_text_from_file()
        super(Asset, self).save(*args, **kwargs)
