# -*- coding: utf-8 -*-

import os
from pathlib import Path
import sys
import django
import shutil
from cmd import Cmd
import io
from datetime import datetime
import fitz

from PyPDF2 import PdfFileWriter, PdfFileReader
from PIL import Image
from useful_inkleby.files import QuickText
from ruamel.yaml import YAML

try:
    os.environ.pop("DJANGO_SETTINGS_MODULE")
except Exception:
    pass

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "proj.settings")
django.setup()

from django.conf import settings
from stringprint.tools.word_convert import convert_word
from stringprint.functions import compress_static
from stringprint.models import Article, Organisation, Asset
from frontend.views import HomeView, ArticleSettingsView
from charts import ChartCollection, Chart


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


def get_yaml(yaml_file):
    yaml = YAML(typ="safe")
    with open(yaml_file, "rb") as doc:
        data = yaml.load(doc)
    # data = fix_yaml(data)
    return data


def load_org_details():
    """
    ingest org details from files
    """
    print("refreshing org details")
    default_slug = os.environ.get("DEFAULT_ORG")
    for k, v in settings.ORGS.items():
        org, created = Organisation.objects.get_or_create(slug=k)
        org.load_from_yaml()
        if default_slug is None:
            default_slug = k
    return default_slug


def merge_pdfs(front, contents, output):
    """
    replace front page with proper front page
    """
    pdf_writer = PdfFileWriter()

    front_page = PdfFileReader(front)
    pdf_writer.addPage(front_page.getPage(0))

    pdf_reader = PdfFileReader(contents)
    for page in range(1, pdf_reader.getNumPages()):
        pdf_writer.addPage(pdf_reader.getPage(page))
    with open(output, "wb") as fh:
        pdf_writer.write(fh)


def pdf_page_to_png(source_pdf, destination):
    doc = fitz.open(source_pdf)
    page = doc.loadPage(0)  # number of page
    pix = page.getPixmap()
    pix.writePNG(destination)


def create_thumbnail(source, destination, base_width=110):
    img = Image.open(source)
    wpercent = base_width / float(img.size[0])
    hsize = int((float(img.size[1]) * float(wpercent)))
    img = img.resize((base_width, hsize), Image.ANTIALIAS)
    img.save(destination)


def create_hero(source, destination, base_width=1024):
    print("resizing hero image")
    target_height = 680
    img = Image.open(source)
    wpercent = base_width / float(img.size[0])
    hsize = int((float(img.size[1]) * float(wpercent)))
    img = img.resize((base_width, hsize), Image.ANTIALIAS)
    height = img.size[1]
    img.save(destination, optimize=True, quality=95)


def select_doc(func):
    def inner(self, inp):

        protected_terms = ["--refresh"]
        inp = inp.strip().lower()
        inp = inp.split(" ")
        pass_down = " ".join([x for x in inp if x in protected_terms])
        inp = [x for x in inp if x not in protected_terms + [""]]
        # use current doc
        print(inp)
        if not inp:
            func(self, pass_down)
        # apply to all
        elif "all" in inp:
            print("running for all")
            for slug in self.loaded_docs():
                self.do_setdoc(slug)
                func(self, pass_down)
        else:
            # apply to space seperated names
            for i in inp:
                self.do_setdoc(i)
                func(self, pass_down)

    return inner


class SPPrompt(Cmd):
    def get_valid_doc_folders(self):
        root = Path(self.current_org.storage_dir, "_docs")
        return [x for x in root.iterdir() if (x / "settings.yaml").exists()]

    def print_status(self):
        if self.current_org:
            print("Current org: {0}".format(self.current_org.name))
        if self.current_doc:
            print("Current doc: {0}".format(self.current_doc))

    @property
    def doc_folder(self):
        return os.path.join(self.current_org.storage_dir, "_docs", self.current_doc)

    def __init__(self):
        self.current_org = None
        self.current_doc = None
        self.dir_lookup = {}
        super().__init__()

    def do_setorg(self, slug):
        self.current_org = Organisation.objects.get(slug=slug)
        self.do_listdocs("")
        self.do_setdoc("1")

    def do_setdoc(self, slug, silent=False):
        slug = self.dir_lookup.get(slug, slug)
        doc_folder = os.path.join(self.current_org.storage_dir, "_docs", slug)
        config_file = os.path.join(doc_folder, "settings.yaml")
        if os.path.exists(config_file) is False:
            print("No valid folder at: {0}".format(doc_folder))
            return
        self.current_doc = slug
        if silent is False:
            prompt.print_status()

    def loaded_docs(self):
        dir = os.path.join(self.current_org.storage_dir, "_docs")
        slugs = self.current_org.articles.all().values_list("slug", flat=True)
        x = 0
        for f in os.listdir(dir):
            doc_folder = os.path.join(dir, f)
            config_file = os.path.join(doc_folder, "settings.yaml")
            if os.path.exists(config_file):
                x += 1
                slugged = f in slugs
                if slugged:
                    yield f

    def do_listdocs(self, inp):
        docs_dir = os.path.join(self.current_org.storage_dir, "_docs")
        slugs = self.current_org.articles.all().values_list("slug", flat=True)
        x = 0
        for f in os.listdir(docs_dir):
            doc_folder = os.path.join(docs_dir, f)
            config_file = os.path.join(doc_folder, "settings.yaml")
            if os.path.exists(config_file):
                x += 1
                slugged = f in slugs
                if slugged:
                    print(x, f)
                else:
                    print(x, f + "(unloaded)")
                self.dir_lookup[str(x)] = f

    def do_load(self, inp):
        if inp is None and self.current_doc:
            self.do_process(inp)
        if inp == "all":
            self.do_loadall("")
        if inp == "unloaded":
            self.do_loadunloaded("")

    def do_loadall(self, inp):
        dir = os.path.join(self.current_org.storage_dir, "_docs")
        for f in os.listdir(dir):
            doc_folder = os.path.join(dir, f)
            config_file = os.path.join(doc_folder, "settings.yaml")
            if os.path.exists(config_file):
                self.do_setdoc(f)
                self.do_process(inp)

    def do_loadunloaded(self, inp):
        dir = os.path.join(self.current_org.storage_dir, "_docs")
        slugs = self.current_org.articles.all().values_list("slug", flat=True)

        for f in os.listdir(dir):
            doc_folder = os.path.join(dir, f)
            config_file = os.path.join(doc_folder, "settings.yaml")
            if os.path.exists(config_file):
                slugged = f in slugs
                if slugged is False:
                    self.do_setdoc(f)
                    self.do_process(inp)

    def do_listorgs(self, inp):
        for o in Organisation.objects.all():
            print(o.slug)

    def do_publish_updated(self, inp):

        for f in self.get_valid_doc_folders():
            self.do_setdoc(f.name, silent=True)
            needs_update = self.do_check_for_update(inp)
            if needs_update:
                print(f"Republishing {f.name}")
                # self.do_load()
                # self.do_process()
                # self.do_renderzip("refresh")
                # self.do_publish()

    def do_check_for_update(self, inp=""):
        """
        if document file or settings has been updated since last upload
        return true
        """
        import subprocess

        doc_folder = Path(self.doc_folder)
        root = doc_folder.parent.parent
        upload_time_file = doc_folder / "upload_time.txt"

        if upload_time_file.exists():
            txt_date = upload_time_file.open().read()
            upload_time = datetime.fromisoformat(txt_date)
        else:
            return False

        settings_file = doc_folder / "settings.yaml"
        data = get_yaml(settings_file)
        doc_file = doc_folder / data["file_source"]

        cmd = f"git log -1 --format=%ct -- {str(settings_file.relative_to(root))} {str(doc_file.relative_to(root))}"
        p = subprocess.check_output([cmd], shell=True)
        if p:
            last_commit = datetime.fromtimestamp(float(p))
            return last_commit > upload_time
        return False

    @select_doc
    def do_convertword(self, demote=None):

        if demote:
            demote = True
        else:
            demote = False
        f = self.doc_folder
        docxs = [x for x in os.listdir(f) if os.path.splitext(x)[1] == ".docx"]
        if len(docxs) > 1:
            print("More than one docx file")
        elif len(docxs) == 0:
            print("No Docx file")
        else:
            docx = os.path.join(f, docxs[0])
            dest = os.path.join(f, "document.md")
            convert_word(docx, dest, demote)

    @select_doc
    def do_process(self, inp):
        if "--refresh" in inp:
            refresh_header = True
        else:
            refresh_header = False
        doc, created = Article.objects.get_or_create(
            org=self.current_org, slug=self.current_doc
        )
        doc.load_from_yaml(self.doc_folder, refresh_header)
        doc.import_assets(os.path.join(self.doc_folder, "assets"), refresh_header)
        doc.load_from_file()
        doc.process()
        print("Finished Processing: {0}".format(doc.title))

    @select_doc
    def do_command(self, command):
        doc, created = Article.objects.get_or_create(
            org=self.current_org, slug=self.current_doc
        )
        doc.load_from_yaml(self.doc_folder)
        doc.run_command(command)
        print("Finished command {1}: {0}".format(doc.title, command))

    @select_doc
    def do_preprocess(self, inp):

        doc, created = Article.objects.get_or_create(
            org=self.current_org, slug=self.current_doc
        )
        doc.load_from_yaml(self.doc_folder)
        doc.run_command("preprocess")
        print("Finished pre-processing: {0}".format(doc.title))

    @select_doc
    def do_publish(self, inp):

        doc, created = Article.objects.get_or_create(
            org=self.current_org, slug=self.current_doc
        )
        doc.load_from_yaml(self.doc_folder)
        doc.run_command("publish")
        print("Finished publishing: {0}".format(doc.title))

    @select_doc
    def do_test(self, inp):
        print(self.current_doc)

    def do_quit(self, inp):
        quit()

    def do_exit(self, inp):
        quit()

    @select_doc
    def do_render(self, inp):
        refresh_all = "refresh" in inp.lower()
        slug = self.current_doc
        bake_folder = self.current_org.publish_dir
        path = os.path.join(bake_folder, slug)
        doc, created = Article.objects.get_or_create(
            org=self.current_org, slug=self.current_doc
        )
        doc.render(path, refresh_all=refresh_all)

    @select_doc
    def do_renderebook(self, inp):
        refresh_all = "refresh" in inp.lower()
        slug = self.current_doc
        bake_folder = self.current_org.publish_dir
        path = os.path.join(bake_folder, slug)
        doc, created = Article.objects.get_or_create(
            org=self.current_org, slug=self.current_doc
        )
        doc.create_ebook(path)

    @select_doc
    def do_renderkindle(self, inp):
        refresh_all = "refresh" in inp.lower()
        slug = self.current_doc
        bake_folder = self.current_org.publish_dir
        path = os.path.join(bake_folder, slug)
        doc, created = Article.objects.get_or_create(
            org=self.current_org, slug=self.current_doc
        )
        doc.create_kindle(path)

    @select_doc
    def do_renderzip(self, inp):
        refresh_all = "refresh" in inp.lower()
        slug = self.current_doc
        origin_folder = self.current_org.storage_dir
        path = os.path.join(origin_folder, "_docs", slug)
        zip_destination = os.path.join(path, slug)
        doc, created = Article.objects.get_or_create(
            org=self.current_org, slug=self.current_doc
        )
        zip_location = doc.render_to_zip(zip_destination, refresh_all=refresh_all)
        print("Zip created")

    @select_doc
    def do_mergepdf(self, inp):

        df = self.doc_folder
        front_page = os.path.join(df, "cover.pdf")
        contents = os.path.join(df, "contents.pdf")
        output = os.path.join(df, "{0}.pdf".format(self.current_doc))
        merge_pdfs(front_page, contents, output)

    @select_doc
    def do_pdfpng(self, inp):
        df = self.doc_folder
        front_page = os.path.join(df, "cover.pdf")
        output = os.path.join(df, "{0}-cover.png".format(self.current_doc))
        thumb = os.path.join(df, "{0}-thumbnail.png".format(self.current_doc))
        pdf_page_to_png(front_page, output)
        create_thumbnail(output, thumb)

    @select_doc
    def do_hero(self, inp):
        yaml_data = get_yaml(os.path.join(self.doc_folder, "settings.yaml"))
        hero_location = yaml_data["header"]["location"]
        hero_path = os.path.join(self.doc_folder, hero_location)
        destination = os.path.join(self.doc_folder, "hero.png")
        create_hero(hero_path, destination)

    def default(self, line):
        options = line.split(" ")
        first = options[0]
        if self.current_doc:
            doc, created = Article.objects.get_or_create(
                org=self.current_org, slug=self.current_doc
            )
        if first in self.current_org.commands or first in doc.commands:
            doc.load_from_yaml(self.doc_folder)
            doc.run_command(line)
            print("Finished command {1}: {0}".format(doc.title, line))
        else:
            return super().default(line)


if __name__ == "__main__":
    default_org = load_org_details()
    prompt = SPPrompt()
    prompt.do_setorg(default_org)
    continue_in_shell = False
    for a in sys.argv[1:]:
        a = a.replace(":", " ")
        if a == "continue":
            continue_in_shell = True
        else:
            prompt.onecmd(a)
    if not sys.argv[1:] or continue_in_shell:
        prompt.cmdloop()
