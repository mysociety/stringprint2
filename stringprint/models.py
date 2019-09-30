# -*- coding: utf-8 -*-

import os
import datetime
import time
import codecs
import shutil
import io
from PIL import Image
from tempfile import mkdtemp
import tinify

from django.conf import settings
from django.urls import reverse
from django.core.files import File
from django.contrib.auth.models import User
from django.db import models
from django.db.models import F
from django.template.loader import render_to_string
from django.utils.html import escape, mark_safe
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import FileSystemStorage
from django.utils.timezone import now
from dirsync import sync

from collections import OrderedDict
from ruamel.yaml import YAML
from selenium import webdriver, common

from useful_inkleby.useful_django.fields import JsonBlockField
from useful_inkleby.useful_django.models import FlexiBulkModel

from charts.fields import GoogleChartField
from .tools.deepink import process_ink
from charts import GoogleChart
from .functions import compress_static

chrome_driver_path = settings.CHROME_DRIVER


class OverwriteStorage(FileSystemStorage):

    def get_available_name(self, name, max_length=None):
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


def get_yaml(file_path):
    yaml = YAML(typ="safe")
    with open(file_path, "rb") as doc:
        data = yaml.load(doc)
    #data = fix_yaml(data)
    return data


def get_file(fi):
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
        max_length=255, blank=True, null=True)  # for google analytics
    publish_root = models.URLField(max_length=255, blank=True, null=True)
    custom_css = models.TextField(default="", blank=True)
    fonts = models.TextField(default="", blank=True)
    include_favicon = models.BooleanField(default=True)
    stylesheet = models.CharField(
        max_length=255, blank=True, null=True)
    icon = models.CharField(max_length=255, blank=True, null=True)

    @property
    def storage_dir(self):
        return settings.ORGS[self.slug]["storage_dir"]

    @property
    def upload_url(self):
        return settings.ORGS[self.slug]["upload_url"]

    @property
    def token(self):
        token = settings.ORGS[self.slug]["token"]
        if "%%" in token:
            token = token[2:-2]
            token = os.environ[token]
        return token

    @property
    def publish_dir(self):
        return settings.ORGS[self.slug]["publish_dir"]

    def load_from_yaml(self):
        print(self.storage_dir)
        data = get_yaml(os.path.join(self.storage_dir, "settings.yaml"))
        ignore = ["orglinks"]
        change = False

        if "fonts" in data:
            current = self.fonts
            data["fonts"] = "\n".join(data["fonts"])

        for k, v in data.items():
            if k not in ignore:
                current = getattr(self, k)
                if current != v:
                    setattr(self, k, v)
                    change = True

        if change:
            self.save()

        if "orglinks" in data:
            self.org_links.all().delete()
            orglinks = data["orglinks"]
            links = []
            for k, v in orglinks.items():
                o = OrgLinks(org=self,
                             name=k,
                             link=v["link"],
                             order=v["order"])
                links.append(o)
            OrgLinks.objects.bulk_create(links)

    def org_links_ordered(self):
        return self.org_links.all().order_by('order')

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

    def get_ga_code(self):
        if self.ga_code:
            return self.ga_code
        else:
            try:
                return settings.GA_CODE
            except Exception:
                return ""


def org_source_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return 'org_{0}/sources/{1}'.format(instance.org_id, filename)


def kindle_source_storage(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return 'kindle/org_{0}/{1}'.format(instance.org_id, filename)


class OrgLinks(models.Model):
    org = models.ForeignKey(Organisation,
                            related_name="org_links",
                            on_delete=models.CASCADE)
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
    def get_driver(cls):
        if cls.driver:
            return cls.driver

        options = webdriver.ChromeOptions()
        options.add_argument("headless")
        options.add_argument("hide-scrollbars")
        cls.driver = webdriver.Chrome(executable_path=chrome_driver_path,
                                      options=options)
        return cls.driver

    @classmethod
    def quit(cls):
        if cls.driver:
            cls.driver.quit()
        cls.driver = None

    def __del__(self):
        if self.driver:
            self.driver.quit()
        super(Chrome, self).__del__()


class Article(models.Model):
    title = models.CharField(max_length=255, blank=True, null=True)
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
    org = models.ForeignKey(Organisation, null=True,
                            blank=True, related_name="articles",
                            on_delete=models.CASCADE)
    book_cover = models.ImageField(
        upload_to=kindle_source_storage, null=True, blank=True)
    kindle_location = models.CharField(max_length=255, null=True, blank=True)
    sections_over_pages = models.BooleanField(default=False)
    first_section_name = models.CharField(
        max_length=255, default="start", blank=True)
    pdf_location = models.CharField(max_length=255, default="", blank=True)
    needs_processing = models.BooleanField(default=False)
    reprocess_source = models.BooleanField(default=False)
    production_url = models.URLField(default="")
    display_notes = models.BooleanField(default=False)
    display_footnotes_at_foot = models.BooleanField(default=True)
    repo_entry = models.URLField(blank=True, default="")
    bottom_iframe = models.URLField(blank=True, default="")

    def load_from_yaml(self, storage_dir, refresh_header=False):
        data = get_yaml(os.path.join(storage_dir, "settings.yaml"))
        ignore = ["repo_slug", "header", "book_cover"]

        for k, v in data.items():
            if k not in ignore:
                current = getattr(self, k)
                if current != v:
                    setattr(self, k, v)

        if "repo_slug" in data:
            repo_slug = data["repo_slug"]
            self.repo_entry = "https://research.mysociety.org/publications/{0}".format(
                repo_slug)
            self.bottom_iframe = "https://research.mysociety.org/embed/related:{0}".format(
                repo_slug)

        if "header" in data:
            header = data["header"]
            file_name = header["location"]
            if os.path.exists(file_name) is False:
                file_name = os.path.join(
                    self.org.storage_dir, self.slug, file_name)
            file_ext = os.path.splitext(file_name)[1]
            internal_name = self.slug + file_ext
            self.add_image(file_name,
                           refresh=refresh_header,
                           internal_name=internal_name,
                           title_image=True,
                           size=header.get("size", "6"))

        if "book_cover" in data:
            print ("loading book cover")
            file_name = data["book_cover"]
            if os.path.exists(file_name) is False:
                file_name = os.path.join(self.org.storage_dir,
                                         self.slug,
                                         file_name)
            self.get_book_cover(file_name)

        if "production_url" not in data:
            self.production_url = self.org.publish_root + self.slug + "/"

        if os.path.exists(self.file_source) is False:
            self.file_source = os.path.join(storage_dir, self.file_source)

        self.last_updated = datetime.datetime.now()
        self.save()

    def yaml_export(self, folder):
        basic_settings = ["title",
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
                          "sections_over_pages",
                          "pdf_location",
                          "production_url",
                          "display_notes",
                          "display_footnotes_at_foot",
                          "repo_entry",
                          "bottom_iframe"]

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

    def export_paragraph_images(self, folder, refresh_all=False):
        """
        exports a folder of images - 1 for each element labeled with the
        combo key
        """
        from io import BytesIO
        import base64

        BAKE_SERVER = "http://127.0.0.1:8000"

        url = self.social_url().replace(settings.SITE_ROOT, BAKE_SERVER)
        url = url + \
            "?id={0}&highlight_first=true".format(
                self.id)
        c = self.content()
        c.retrieve_sections_over_pages = True
        c.load_sections([])
        grafs_to_do = [
        ]
        for g in c.all_grafs():
            g.destination_location = os.path.join(
                folder, "{0}.png".format(g.combo_key()))
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
        driver.set_window_size(500, 568)
        driver.get(url)

        driver.execute_script('$("nav").hide()')
        driver.execute_script('$(".extended-row").show();')
        driver.execute_script('$(".extended").show();')
        driver.execute_script('$(".hide-link").hide();')
        driver.execute_script('$("body").css("overflow", "hidden");')
        # Need to generalise this
        # driver.execute_script('$(".container").css("background-color","#F1F3EB");')
        # driver.execute_script('$(".content-row").css("background-color","#F1F3EB");')

        for g in grafs_to_do:
            print(g.order, g.combo_key())
            try:
                element = driver.find_element_by_xpath(
                    "//div[@id='{0}']".format(g.order))
            except common.exceptions.NoSuchElementException:
                print ("skipping - element {0} not found".format(g.order))
                continue
            location = element.location
            size = element.size

            offset = 50
            left_offset = 15
            if g.blockquote:
                left_offset += 30

            driver.execute_script(
                "window.scrollTo(0, {0});".format(location['y'] - offset))

            screenshot = driver.get_screenshot_as_base64()
            img = Image.open(
                BytesIO(base64.decodebytes(screenshot.encode("utf-8"))))
            width = 500
            height = int(width / 1.91)

            left = location['x'] - left_offset
            top = offset - 8
            right = left + 4 + width
            bottom = top + height  # size['height'] + 2

            elements = (int(left), int(top), int(right), int(bottom))
            im = img.crop(elements)
            im.save(g.destination_location)
        Chrome.quit()

    def reprocessing(self):
        return self.needs_processing or self.reprocess_source

    def search_url(self):
        if self.baking:
            return "search.html"
        else:
            return "search"

    def import_assets(self, asset_folder):
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
            f = Asset(article=self,
                      slug=a["slug"],
                      type=a["content_type"],
                      alt_text=a["caption"],
                      caption=a["caption"],
                      )
            file_name = "{0}.{1}".format(a["slug"], a["type"])
            file_path = os.path.join(asset_folder, file_name)
            if a["content_type"] == "image":
                reopen = open(file_path, "rb")
                django_file = File(reopen)
                suf = SimpleUploadedFile('{2}.{0}.{1}'.format(a["slug"],
                                                              a["type"],
                                                              self.id),
                                         django_file.read(),
                                         content_type='image/png')
                f.image = suf
                django_file.close()
            if a["content_type"] == "table":
                f.chart = GoogleChart(chart_type="table_chart",
                                      file_name=file_path)
            print ("saving {0}".format(f.slug))
            f.save()

    def prepare_assets(self):
        """
        if assets have a chart - produce the image
        """
        for a in self.assets.filter(regenerate_image_chart=True):
            if a.chart and a.chart.chart_type != "table_chart":
                print("making image for {0}".format(a.slug))
                a.get_chart_image()

    def tinify_headers(self):
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

    def get_book_cover(self, path):
        fi = get_file(path)
        self.book_cover.save("{0}-book-cover.tif".format(self.id),
                             fi,
                             save=True)
        fi.close()

    def cite_link(self, paragraph):
        """
        returns a citeable link depending on article settings
        """
        if hasattr(self, "baking") and self.baking:
            v = self.production_url
            if v[-1] != "/":
                v += "/"
            v += "l/{0}".format(paragraph.combo_key())
            return v
        else:
            return reverse('redirect_link', args=(self.slug,
                                                  paragraph.combo_key(),))

    def social_cite_link(self, paragraph):
        """
        returns a citeable link depending on article settings
        """

        v = "#" + paragraph.combo_key()

        return self.social_url() + v

    def prep_image_lookup(self):
        images = self.images.all()
        self.image_lookup = {x.section_name: x for x in images}

    def add_image(self, file_location="", image_vertical="", internal_name="",
                  refresh=False, **kwargs):
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
                print ("found-deleting")
                q.delete()

        ni, created = HeaderImage.objects.get_or_create(article=self,
                                                        source_loc=file_location,
                                                        **kwargs
                                                        )
        ni.save()
        if created is True or refresh is True:
            fi = get_file(file_location)
            ni.image.save(internal_name,
                          fi,
                          save=True
                          )
            fi.close()
            if image_vertical:

                header, tail = os.path.splitext(internal_name)
                vert_file = header + "_vert" + tail
                fi = get_file(image_vertical)
                ni.image_vertical.save(vert_file,
                                       fi,
                                       save=True)
                fi.close()
            # ni.trigger_create_responsive()
            ni.create_responsive()
            ni.create_tiny()
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

    def render_to_zip(self, zip_destination, *args, **kwargs):
        """
        render the article and return the location of a zip file
        """
        temp_folder = mkdtemp()
        self.render(destination=temp_folder, *args, **kwargs)
        shutil.make_archive(zip_destination, 'zip', temp_folder)
        return zip_destination

    def render(self, destination, url=None, plain=True, kindle=True,
               refresh_all=False):
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
        if self.org.stylesheet:
            files.append(self.org.stylesheet)

        compress_static(files)
        self.prepare_assets()
        self.tinify_headers()

        from .views import (ArticleView,
                            TextView,
                            TipueContentView,
                            TipueSearchView,
                            RedirectLink,
                            TOCView)

        """
        create destination folders
        """
        dirs = [destination,
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
        generate paragraph images
        """
        self.export_paragraph_images(os.path.join(
            destination, "media", "paragraphs"), refresh_all=refresh_all)

        """
        subclass so we can amend article override settings - force paywall off
        """

        current_article = self

        class BakeArticleView(ArticleView):
            share_image = "{{SITE_ROOT}}/{{article.get_share_image}}"
            twitter_share_image = "{{SITE_ROOT}}/{{article.get_share_image}}"
            article_settings_override = {"paywall": False,
                                         "baking": True,
                                         "search": False}

            def get_article(self, request, article_slug):
                return current_article

        class BakeTipueContentView(TipueContentView):
            article_settings_override = {"paywall": False,
                                         "baking": True,
                                         "search": True}

        class BakeTipueSearchView(TipueSearchView):
            article_settings_override = {"paywall": False,
                                         "baking": True,
                                         "search": True}

        class BakeTOCView(TOCView):
            article_settings_override = {"paywall": False,
                                         "baking": True,
                                         "search": False}

        class BakePlainView(TextView):
            article_settings_override = {"paywall": False,
                                         "baking": True,
                                         "search": False}

        article = self
        article.baking = True

        c = self.display_content()

        for g in c.all_grafs():

            g._article = article

            class BakeRedirectLinkView(RedirectLink):

                def load_article(self, request, article_slug, paragraph_slug):
                    self.article = article
                    self.article.baking = True
                    self.content = c
                    self.graf = g

            args = ("blah", "blah")
            BakeRedirectLinkView.write_file(path=os.path.join(destination,
                                                              "l", g.combo_key() + ".html"),
                                            args=args)

        if self.sections_over_pages:
            c = self.display_content()
            for s in c.sections:
                args = (self.slug, s.anchor())
                name = "{0}.html".format(s.anchor())
                BakeArticleView.write_file(path=os.path.join(destination, name),
                                           args=args)

        args = (self.slug,)
        BakeArticleView.write_file(path=os.path.join(
            destination, "index.html"), args=args)
        BakeTipueSearchView.write_file(path=os.path.join(
            destination, "search.html"), args=args)
        BakeTipueContentView.write_file(path=os.path.join(destination,
                                                          "tipuesearch_content.js"),
                                        args=args)
        BakeTOCView.write_file(path=os.path.join(destination, "toc.json"),
                               args=args)

        if plain:
            BakePlainView.write_file(path=os.path.join(
                destination, "plain.html"), args=args)

        print("moving compressed files")

        self.compressed_files = [x[len(settings.COMPRESS_URL):]
                                 for x in self.compressed_files]

        for c in self.compressed_files:
            print (c)

        """
        move required static files
        """

        files = [
            "js//clipboard.min.js",
            "js//agietan.min.js",
            "js//tipuesearch.min.js",
            "js//tipuesearch_set.js",
            "css//stringprint-core.min.css",
            "css//stringprint-core.min.css",
            "css//stringprint-default.min.css",
            "css//tipuesearch.css",
            "css//kindle.css",
            "css//text_mode.css",
            "css//fa_reduced.css",
        ]

        files.extend(self.compressed_files)

        folders = [
            "favicon",
            "licences",
            "font"
        ]

        static = settings.STATIC_DIR
        media = settings.MEDIA_ROOT

        for f in files:
            print(f)
            shutil.copyfile(os.path.join(static, f),
                            os.path.join(destination, "static", f))

        for f in folders:
            print(f)
            d = os.path.join(destination, "static", f)
            if os.path.isdir(d) is False:
                os.makedirs(d)
            sync(os.path.join(static, f), d, "sync")

        """
        pull in org based static directories
        """
        org_static_dirs = [x for x in settings.STATICFILES_DIRS if x != static]

        for o in org_static_dirs:
            d = os.path.join(destination, "static")
            sync(o, d, "sync")

        """
        move media files - from headerimages and assets
        """

        for i in self.images.all():
            for f in i.get_all_files():
                print(f)
                if os.path.exists(os.path.join(media, f)):
                    shutil.copyfile(os.path.join(media, f),
                                    os.path.join(destination, "media", f))

        for a in self.assets.filter(active=True):
            if a.image:
                print(a.image.name)
                shutil.copyfile(os.path.join(media, a.image.name),
                                os.path.join(destination, "media",
                                             a.image.name))
            if a.image_chart:
                print(a.image_chart.name)
                shutil.copyfile(os.path.join(media, a.image_chart.name),
                                os.path.join(destination, "media",
                                             a.image_chart.name))

        if kindle:
            self.create_kindle(destination, use_temp=True)

    def create_kindle(self, destination, use_temp=False):
        """
        export views and supporting files to location and generate kindle file
        """

        from .views import KindleView, KindleOPF, KindleNCX
        from shutil import copyfile

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
        for a in self.assets.all():
            if a.type == Asset.IMAGE:
                media_files.append(a.image.name)
            if a.type == Asset.CHART:
                if a.chart.chart_type != "table_chart":
                    media_files.append(a.image_chart.name)

        for f in media_files:
            copyfile(os.path.join(settings.MEDIA_ROOT, f),
                     os.path.join(media_dir, f))

        KindleView.write_file(path=os.path.join(
            staging, "text.html"), args=args, minimise=False)
        KindleOPF.write_file(path=opf, args=args, minimise=False)
        KindleNCX.write_file(path=os.path.join(
            staging, "toc.ncx"), args=args, minimise=False)
        copyfile(os.path.join(settings.STATIC_DIR, "css", "kindle.css"),
                 os.path.join(css_dir, "kindle.css"))
        if self.book_cover:
            copyfile(self.book_cover.path,
                     os.path.join(staging, "bookcover.jpg"))

        print("generating mobi")
        com = settings.KINDLEGEN_LOC + " " + opf
        os.system(com)

        if staging != destination:
            if os.path.exists(os.path.join(staging, self.slug + ".mobi")):

                print("copying to destination")
                shutil.copyfile(os.path.join(staging, self.slug + ".mobi"),
                                os.path.join(destination, self.slug + ".mobi"),
                                )
            else:
                print("error! kindle file not present")

    def social_url(self):
        """
        url the baker uses to render to the social settings
        """
        if hasattr(self, "baking") and self.baking:
            return self.production_url
        else:
            return self.url()

    def url(self, section=""):

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
        return settings.LIVE_ROOT + reverse("article_view", args=(self.slug,))

    def year(self):
        if self.publish_date:
            return self.publish_date.year
        else:
            return datetime.datetime.now().year

    def process(self):
        """
        creates the section and graf structure from raw markup
        """
        self.content().process()
        self.needs_processing = False
        self.save()

    def content(self):
        """
        retrieve current version
        """
        q = Version.objects.filter(article=self,
                                   number=self.current_version)
        # error handling
        if q.count() > 1:
            print ("deleting previous")
            q.delete()

        if not q.exists():
            print ("creating new content")
            v = Version.objects.get_or_create(article=self,
                                              number=self.current_version)[0]
        else:

            v = q[0]
        return v

    def display_content(self, slugs=[]):
        if self.current_version == 0:
            return self.content()

        v = Version.restricted(slugs=slugs,
                               article=self,
                               number=self.current_version)

        return v

    def load_from_file(self):

        with codecs.open(self.file_source, encoding='utf-8') as f:
            raw = f.read()
        if raw:
            c = self.content()
            c.raw = raw
            c.save()

    def title_image(self):
        images = self.images.filter(title_image=True)
        if images.exists():
            return images[0]
        else:
            return None

    def get_share_image(self):
        title_image = self.title_image()
        if title_image:
            return title_image.get_share_image()
        else:
            return None


class HeaderImage(FlexiBulkModel):

    title_image = models.BooleanField(default=False)
    section_name = models.CharField(max_length=255, null=True, blank=True)
    source_loc = models.CharField(max_length=255, null=True, blank=True)
    image = models.ImageField(null=True, blank=True,
                              storage=OverwriteStorage())
    image_vertical = models.ImageField(null=True, blank=True)
    image_alt = models.CharField(max_length=255, null=True, blank=True)
    article = models.ForeignKey(Article, related_name="images",
                                on_delete=models.CASCADE)
    size = models.IntegerField(default=0)
    queue_responsive = models.BooleanField(default=False)
    queue_tiny = models.BooleanField(default=False)

    def offset(self):
        """
        return offset to center image
        """
        lookup = {2: 5,
                  4: 4,
                  6: 4,
                  8: 2,
                  10: 2,
                  12: 0
                  }
        try:
            return lookup[self.size]
        except KeyError:
            return 0

    def get_image_name(self, resolution):
        """
        returns big or small image depending if we've tinified
        """
        if self.queue_tiny is True:
            return self.get_responsive_image_name(resolution)
        else:
            return self.get_tiny_responsive_image_name(resolution)

    def get_share_image(self):
        """
        return the large view display for header image
        """
        file_name = self.get_image_name(1200)
        if file_name[:2] == "./":
            file_name = file_name[2:]

        return settings.MEDIA_URL + file_name

    def get_responsive_image_name(self, resolution):
        """
        get the responsive image needed for each resolution
        """
        name, ext = os.path.splitext(self.image.name)
        return name + "_{0}".format(resolution) + ext

    def get_tiny_responsive_image_name(self, resolution):
        """
        get the responsive image needed for each resolution
        """
        name, ext = os.path.splitext(self.image.name)
        return name + "_{0}_tiny".format(resolution) + ext

    def header_image_res(self):
        """

        tell template about different resolutions

        """
        for width in [768, 992, 1200, 1440, 1920]:
            yield settings.MEDIA_URL + self.get_image_name(width), width

    def largest_header(self):
        """
        get largest image size
        """
        return settings.MEDIA_URL + self.get_tiny_responsive_image_name(1440)

    def get_all_files(self):
        """
        get all files named for copying reasons
        """
        widths = [768, 992, 1200, 1440, 1920]
        for width in widths:
            yield self.get_responsive_image_name(width)
            yield self.get_tiny_responsive_image_name(width)

        yield self.image.name

    def create_tiny(self):
        """

        Passes up to tinyimg to reduce.
        """

        tinify.key = settings.TINY_PNG_KEY

        if self.image_vertical:
            images = ((self.image_vertical, [768]),
                      (self.image, [992, 1200, 1440, 1920]),
                      )
        else:
            images = ((self.image, [768, 992, 1200, 1440, 1920]),
                      )
        for i_file, res in images:
            for width in res:
                new_name = settings.MEDIA_ROOT + \
                    self.get_responsive_image_name(width)
                tiny_name = settings.MEDIA_ROOT + \
                    self.get_tiny_responsive_image_name(width)
                source = tinify.from_file(str(new_name))
                source.to_file(tiny_name)

    def create_responsive(self):
        """
        creates the different sized versions of the header image.

        If vertical image will make the smaller one mirror that.

        Passes up to tinyimg to reduce.
        """

        if self.image_vertical:
            images = ((self.image_vertical, [768]),
                      (self.image, [992, 1200, 1440, 1920]),
                      )
        else:
            images = ((self.image, [768, 992, 1200, 1440, 1920]),
                      )
        for i_file, res in images:

            print("creating responsive versions")
            image = Image.open(i_file)
            o_width, o_height = image.size
            for width in res:
                new_height = width / float(o_width) * o_height
                thumbnail = image.copy()
                thumbnail.thumbnail((width, new_height), Image.ANTIALIAS)
                new_name = settings.MEDIA_ROOT + \
                    self.get_responsive_image_name(width)
                thumbnail.save(new_name)  # , quality=90, optimize=True
        self.queue_responsive = False
        HeaderImage.objects.filter(id=self.id).update(queue_responsive=False)


class Version(models.Model):
    article = models.ForeignKey(Article, related_name="versions",
                                on_delete=models.CASCADE)
    number = models.IntegerField()
    label = models.CharField(max_length=255, blank=True, null=True)
    raw = models.TextField(blank=True, null=True)
    sections = JsonBlockField(blank=True, null=True)
    has_notes = models.BooleanField(default=False)

    def load_from_file(self):
        with codecs.open(self.article.file_source, encoding='utf-8') as f:
            raw = f.read()
        if raw:
            self.raw = raw
            self.save()

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
            values = query.values('pk', 'id', 'number',
                                  'label', 'sections', 'has_notes')[0]
            props = {'article': article}
            props.update(values)
            v = cls(**props)
        v.load_sections(slugs)
        return v

    def load_sections(self, slugs):
        """
        construct a self.sections that only contains graf objects for slugs we specify
        """
        if self.article.sections_over_pages or hasattr(self.article,
                                                       "retrieve_sections_over_pages"):
            self.sections = MultiSection.return_sections(self, slugs)

        for s in self.sections:
            s._version = self

    def used_assets(self):
        """
        slugs for assets used by this version
        """
        assets = []
        for s in self.sections:
            assets.extend(s.used_assets())
        return assets

    def display_sections(self):
        for s in self.sections:
            if s.has_grafs():
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
                future = self._toc.items[self.order + 1:]
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

            def add(self, **kwargs):
                item = Link(**kwargs)
                item.order = len(self.items)
                item._toc = self
                self.items.append(item)

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
        for s in self.sections:
            if s.name:
                l = toc.add(name=s.name,
                            anchor=s.anchor(),
                            nav_url=s.nav_url(),
                            id=s.order,
                            level=1
                            )
            for g in s.get_grafs():
                if g.title:
                    l = toc.add(name=g.title,
                                anchor=g.anchor(),
                                nav_url=g.nav_url(),
                                id=g.order,
                                level=g.header_level
                                )
        return toc

    def anchors(self):
        """
        for kindle
        """

        def y(title, anchor, count):
            return {"title": title, "anchor": anchor, 'count': count}

        yield y("Table of Contents", "toc", "1")
        count = 2
        if self.sections[0].name == "":
            yield y("Introduction", "intro", count)
            count += 1
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

    def all_grafs(self):
        """
        only show introduction if not logged in
        """

        for s in self.sections:
            for g in s.grafs:
                yield g

    def limit_all_but_first(self):
        """
        only show introduction if not logged in
        """

        for s in self.sections[1:]:
            s.visible = False
            for g in s.grafs:
                g.visible = False

    def limit_to_code(self, code="", first_para_slug=""):
        """
        only display shared paragraph
        """
        graf, section = self.get_paragraph(code, first_para_slug)

        if graf is None:
            self.limit_all_but_first()
            return

        preview_range = 2
        for s in self.sections[1:]:
            s.sneak_peak = True
            if s == section:
                start_order = s.grafs[0].order
                end_order = s.grafs[-1].order
                cur_pos = graf.order - start_order

                if graf.order < start_order + 2 * preview_range:
                    display_range = list(range(0, (2 * preview_range) + 1))
                elif graf.order > end_order - 2 * preview_range:
                    display_range = list(range(
                        len(s.grafs) - 2 * preview_range, len(s.grafs)))
                else:
                    display_range = list(range(
                        cur_pos - preview_range, cur_pos + preview_range + 1))

                for i, g in enumerate(s.grafs):
                    if i not in display_range:
                        g.visible = False
                    else:
                        g.visible = True

                for i, d in enumerate(display_range):
                    if s.grafs[d] == graf:
                        cur_pos = i

                        break

                # fade out
                s.grafs[display_range[-1]].place_message = True
                if cur_pos == 0:  # start
                    s.grafs[display_range[-2]].visible = "half-opacity"
                    s.grafs[display_range[-1]].visible = "quarter-opacity"
                elif cur_pos == len(display_range) - 1:  # end
                    s.grafs[display_range[0]].visible = "quarter-opacity"
                    s.grafs[display_range[1]].visible = "half-opacity"
                else:  # else
                    s.grafs[display_range[0]].visible = "half-opacity"
                    s.grafs[display_range[-1]].visible = "half-opacity"
            else:
                s.visible = False
                for g in s.grafs:
                    g.visible = False

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

        keys = {'parent_id': parent,
                'order': paragraph_key,
                'letter_key': letter_key,
                'key': key,
                'start_key': start_key,
                'end_key': end
                }

        methods = [
            ['key'],
            ['letter_key'],
            ['start_key', 'end_key'],
            ['start_key', 'order'],
            ['start_key'],
            ['end_key'],
            ['order', 'parent_id'],
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

    def footnotes(self):
        notes = []
        for s in self.sections:
            for g in s.get_grafs():
                for s in g.self_and_extras():
                    if s.footnotes and s.visible:
                        for f in s.footnotes:
                            notes.append(f)
        return notes

    def process(self):
        """
        creates the section and graf structure from raw markup
        """
        self.article.assets.all().update(active=False)
        if not self.raw:
            self.load_from_file()
        process_ink(self, self.raw)

        first_section = "start"
        if self.sections:
            if self.sections[0].name:
                first_section = self.sections[0].anchor()
        self.first_section_name = first_section

        self.last_updated = now()
        self.save()

    def move_to_multi(self):
        self.multi_section.all().delete()
        for s in self.sections:
            m = MultiSection()
            m.stash(self, s)
            m.save()
        self.sections = []

    def save(self, *args, **kwargs):
        """
        increment versioning if copy has changed

        if article is multi_sections - save as independent objects
        """

        if self.article.sections_over_pages:
            self.move_to_multi()

        if self.id:
            old_v = Version.objects.get(id=self.id)
            should_save = old_v.raw != self.raw
        else:
            should_save = True

        if should_save:
            self.number += 1
            self.article.current_version += 1
            Article.objects.filter(id=self.article_id).update(
                current_version=self.number)

        super(Version, self).save(*args, **kwargs)


class MultiSection(models.Model):
    """
    used for things being seperated out over multiple pages
    """
    version = models.ForeignKey(Version, related_name="multi_section",
                                on_delete=models.CASCADE)
    order = models.IntegerField(default=0)
    anchor = models.CharField(max_length=255)
    section = JsonBlockField(blank=True, null=True)
    grafs = JsonBlockField(blank=True, null=True)

    @classmethod
    def return_sections(cls, version, slugs=[]):
        """
        returns basic sections (no grafs) unless slug in list
        """
        sections = []
        d_sections = cls.objects.filter(version=version).order_by('order')
        d_sections = d_sections.values('id', 'order', 'anchor', 'section')
        for i in d_sections:
            instance = cls(**i)
            if instance.anchor in slugs or slugs == []:  # if nothing specified load all
                instance.load_grafs()
                instance.section.active_section = True
            else:
                instance.grafs = []
                instance.section.active_section = False
            sections.append(instance.section)
        return sections

    def stash(self, version, section):
        self.version = version
        self.order = section.order
        self.anchor = section.anchor()
        self.grafs = section.grafs
        section.grafs = []
        self.section = section

    def load_grafs(self):

        g = MultiSection.objects.filter(
            id=self.id).values_list('grafs', flat=True)
        self.section.grafs = g[0]


class Asset(FlexiBulkModel):

    RAW_HTML = "h"
    IMAGE = "i"
    CHART = "c"
    types = ((RAW_HTML, "html"),
             (IMAGE, "image"),
             (CHART, "chart"))

    article = models.ForeignKey(Article, related_name="assets", null=True,
                                on_delete=models.CASCADE)
    slug = models.CharField(max_length=255, null=True)
    type = models.CharField(max_length=2, choices=types, null=True)
    location = models.CharField(max_length=255, null=True)
    chart = GoogleChartField(null=True, blank=True)
    image_chart = models.ImageField(null=True, blank=True,
                                    storage=OverwriteStorage())
    regenerate_image_chart = models.BooleanField(default=False)
    image = models.ImageField(null=True, blank=True,
                              storage=OverwriteStorage())
    alt_text = models.CharField(max_length=255, null=True, blank=True)
    caption = models.CharField(max_length=255, null=True, blank=True)
    content = models.TextField(null=True)
    code_content = models.TextField(null=True)
    active = models.BooleanField(default=False)

    def get_chart_image(self):
        """
        loads the chart in selenium so we can fetch the image version
        """
        from selenium import webdriver
        from .views import AssetView
        import io
        import tempfile

        temp_dir = tempfile._get_default_tempdir()
        temp_name = next(tempfile._get_candidate_names())
        file_destination = os.path.join(temp_dir, temp_name + ".html")
        address = "file:///" + file_destination.replace("\\", "/")
        AssetView.write_file(
            args=(self.article.slug, self.slug, "yes"), path=file_destination)
        driver = webdriver.Firefox()
        driver.get(address)
        elem = driver.find_element_by_id(self.chart.ident)
        contents = elem.get_attribute('innerHTML')
        contents = contents.replace(
            '<img src="data:image/png;base64,', "")[:-2]
        driver.quit()
        image_output = io.StringIO()
        # Write decoded image to buffer
        image_output.write(contents.decode('base64'))
        image_output.seek(0)  # seek beginning of the image string

        suf = SimpleUploadedFile('{0}.png'.format(self.chart.ident),
                                 image_output.read(),
                                 content_type='image/png')

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

        self.image.save(self.slug + tail,
                        get_file(file_location),
                        save=True
                        )

    def get_text_from_file(self):
        """
        extract content for a html asset
        """
        with codecs.open(self.location, encoding='utf-8') as f:
            raw = f.read()
        if "---CODE---" in raw:
            self.content, self.code_content = raw.split("---CODE---")
        else:
            self.content = raw
        self.save()

    def render_image(self, basic=False, chart_alt=False):
        """
        get image ready for render
        """

        if chart_alt:
            image = self.image_chart
        else:
            image = self.image

        url = image.url
        if settings.MEDIA_URL not in url and url[0] == "/":
            url = url[1:]
        if hasattr(self.article, "baking") and self.article.baking:
            url = self.article.production_url + url

        if self.alt_text:
            at = self.alt_text
        else:
            at = self.caption

        if self.caption is None:
            self.caption = ""

        context = {"source": url,
                   "alt": escape(at),
                   "title": escape(self.caption),
                   "caption": self.caption}
        rendered = render_to_string('charts//basic_image.html', context)
        return mark_safe(rendered)

    def render_code(self):
        return mark_safe(self.code_content)

    def render(self, basic=False):
        if self.type == Asset.RAW_HTML:
            return mark_safe(self.content)
        if self.type == Asset.IMAGE:
            return self.render_image(basic=basic, chart_alt=False)
        if self.type == Asset.CHART:
            if basic:
                if self.chart.chart_type == "table_chart":
                    return self.chart.render_html_table(self.caption)
                else:
                    return self.render_image(basic=basic, chart_alt=True)
            else:
                return self.chart.render_div(self.caption)

    def save(self, *args, **kwargs):
        if self.image:
            self.type = Asset.IMAGE
        if self.chart:
            self.type = Asset.CHART
        if self.content:
            self.type = Asset.RAW_HTML
        if self.content is None and self.type == Asset.RAW_HTML:
            self.get_text_from_file()
        super(Asset, self).save(*args, **kwargs)
