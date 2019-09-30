# -*- coding: utf-8 -*-

import os
import sys
import django
import shutil
from cmd import Cmd
import io
import requests

import fitz
import tinify

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
from charts import ChartCollection, GoogleChart


def upload_zip(url, slug, filepath, token):

    filename = os.path.split(filepath)[1]
    url = url + slug
    headers = {'Content-Disposition': 'attachment; filename={0}'.format(filename),
               'Content-type': 'application/zip',
               'Authorization': 'Token {0}'.format(token)}
    with open(filepath, 'rb') as filedata:
        r = requests.put(url, data=filedata, headers=headers)
    print (r.content)

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
    #data = fix_yaml(data)
    return data


def load_org_details():
    """
    ingest org details from files
    """
    print ("refreshing org details")
    first_org = None
    for k, v in settings.ORGS.items():
        org, created = Organisation.objects.get_or_create(slug=k)
        org.load_from_yaml()
        if first_org is None:
            first_org = k
    return first_org


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
    with open(output, 'wb') as fh:
        pdf_writer.write(fh)


def pdf_page_to_png(source_pdf, destination):
    doc = fitz.open(source_pdf)
    page = doc.loadPage(0)  # number of page
    pix = page.getPixmap()
    pix.writePNG(destination)


def create_thumbnail(source, destination, base_width=110):
    img = Image.open(source)
    wpercent = (base_width / float(img.size[0]))
    hsize = int((float(img.size[1]) * float(wpercent)))
    img = img.resize((base_width, hsize), Image.ANTIALIAS)
    img.save(destination)


def create_hero(source, destination, base_width=1024):
    print ("resizing hero image")
    target_height = 680
    img = Image.open(source)
    wpercent = (base_width / float(img.size[0]))
    hsize = int((float(img.size[1]) * float(wpercent)))
    img = img.resize((base_width, hsize), Image.ANTIALIAS)
    height = img.size[1]
    img.save(destination)
    tinify.key = settings.TINY_PNG_KEY
    tiny_destination = "{0}-tiny{1}".format(*os.path.splitext(destination))
    print ("shrinking")
    source = tinify.from_file(destination)
    source.to_file(tiny_destination)


def select_doc(func):
    
        def inner(self, inp):
            
            protected_terms = ["--refresh"]
            inp = inp.strip().lower()
            inp = inp.split(" ")
            pass_down = " ".join([x for x in inp if x in protected_terms])
            inp = [x for x in inp if x not in protected_terms + [""]]
            # use current doc
            print (inp)
            if not inp: #
                func(self,pass_down)
            # apply to all
            elif "all" in inp:
                for slug in self.loaded_docs():
                    self.do_setdoc(slug)
                    func(self,pass_down)
            else:
                # apply to space seperated names
                for i in inp:
                    self.do_setdoc(i)
                    func(self,pass_down)
        return inner


class SPPrompt(Cmd):


    def print_status(self):
        if self.current_org:
            print ("Current org: {0}".format(self.current_org.name))
        if self.current_doc:
            print ("Current doc: {0}".format(self.current_doc))

    @property
    def doc_folder(self):
        return os.path.join(self.current_org.storage_dir, self.current_doc)

    def __init__(self):
        self.current_org = None
        self.current_doc = None
        self.dir_lookup = {}
        super().__init__()

    def do_setorg(self, slug):
        self.current_org = Organisation.objects.get(slug=slug)
        prompt.print_status()

    def do_setdoc(self, slug):
        slug = self.dir_lookup.get(slug, slug)
        doc_folder = os.path.join(self.current_org.storage_dir, slug)
        config_file = os.path.join(doc_folder, "settings.yaml")
        if os.path.exists(config_file) is False:
            print ("No valid folder at: {0}".format(doc_folder))
            return
        self.current_doc = slug
        prompt.print_status()

    def loaded_docs(self):
        dir = self.current_org.storage_dir
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
        dir = self.current_org.storage_dir
        slugs = self.current_org.articles.all().values_list("slug", flat=True)
        x = 0
        for f in os.listdir(dir):
            doc_folder = os.path.join(dir, f)
            config_file = os.path.join(doc_folder, "settings.yaml")
            if os.path.exists(config_file):
                x += 1
                slugged = f in slugs
                if slugged:
                    print (x, f)
                else:
                    print (x, f + "(unloaded)")
                self.dir_lookup[str(x)] = f

    def do_load(self, inp):
        if inp is None and self.current_doc:
            self.do_process(inp)
        if inp == "all":
            self.do_loadall("")
        if inp == "unloaded":
            self.do_loadunloaded("")

    def do_loadall(self, inp):
        dir = self.current_org.storage_dir
        for f in os.listdir(dir):
            doc_folder = os.path.join(dir, f)
            config_file = os.path.join(doc_folder, "settings.yaml")
            if os.path.exists(config_file):
                self.do_setdoc(f)
                self.do_process(inp)

    def do_loadunloaded(self, inp):
        dir = self.current_org.storage_dir
        slugs = self.org.articles.all().values_list("slug", flat=True)

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
            print (o.slug)

    @select_doc
    def do_convertword(self, demote=None):

        if demote:
            demote = True
        else:
            demote = False
        f = self.doc_folder
        docxs = [x for x in os.listdir(f) if os.path.splitext(x)[1] == ".docx"]
        if len(docxs) > 1:
            print ("More than one docx file")
        elif len(docxs) == 0:
            print ("No Docx file")
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
        doc, created = Article.objects.get_or_create(org=self.current_org,
                                                     slug=self.current_doc)
        doc.load_from_yaml(self.doc_folder, refresh_header)
        doc.import_assets(os.path.join(self.doc_folder, "assets"))
        doc.load_from_file()
        doc.process()
        print ("Finished Processing: {0}".format(doc.title))

    @select_doc
    def do_test(self, inp):
        print (self.current_doc)

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
        doc, created = Article.objects.get_or_create(org=self.current_org,
                                                     slug=self.current_doc)
        doc.render(path, refresh_all=refresh_all)

    @select_doc
    def do_renderzip(self, inp):
        refresh_all = "refresh" in inp.lower()
        slug = self.current_doc
        origin_folder = self.current_org.storage_dir
        path = os.path.join(origin_folder, slug)
        zip_destination = os.path.join(path,
                                       slug)
        doc, created = Article.objects.get_or_create(org=self.current_org,
                                                     slug=self.current_doc)
        zip_location = doc.render_to_zip(
            zip_destination, refresh_all=refresh_all)
        print ("Zip created")

    @select_doc
    def do_uploadzip(self, inp):
        token = self.current_org.token
        upload_url = self.current_org.upload_url
        slug = self.current_doc
        origin_folder = self.current_org.storage_dir
        path = os.path.join(origin_folder, slug)
        zip_destination = os.path.join(path,
                                       slug) + ".zip"
        doc, created = Article.objects.get_or_create(org=self.current_org,
                                                     slug=self.current_doc)
        repo_slug = doc.repo_entry.split("/")[-1]
        print ("using {0} as slug".format(repo_slug))
        upload_zip(upload_url, repo_slug, zip_destination, token)

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
            
if __name__ == "__main__":
    default_org = load_org_details()
    prompt = SPPrompt()
    prompt.do_setorg(default_org)
    prompt.do_listdocs("")
    continue_in_shell = False
    for a in sys.argv[1:]:
        a = a.replace(":", " ")
        if a == "continue":
            continue_in_shell = True
        else:
            prompt.onecmd(a)
    if not sys.argv[1:] or continue_in_shell:
        prompt.cmdloop()
