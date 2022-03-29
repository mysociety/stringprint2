# -*- coding: utf-8 -*-

import cmd
import io
import os
import shutil
import signal
import sys
from datetime import datetime
from pathlib import Path
from subprocess import Popen
from typing import Any, Callable, List, Optional, Union

import django
import fitz
from cookiecutter.main import cookiecutter
from PIL import Image
from PyPDF2 import PdfFileReader, PdfFileWriter
from rich import print
from rich.prompt import Prompt
from ruamel.yaml import YAML
from useful_inkleby.files import QuickText

try:
    os.environ.pop("DJANGO_SETTINGS_MODULE")
except Exception:
    pass

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "proj.settings")
django.setup()

from django.conf import settings

from charts import Chart, ChartCollection
from frontend.views import ArticleSettingsView, HomeView
from stringprint.functions import compress_static
from stringprint.models import Article, Asset, Organisation
from stringprint.tools.word_convert import convert_word


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


def load_org_details() -> str:
    """
    ingest org details from files
    """
    default_slug = os.environ.get("DEFAULT_ORG")
    for k, v in settings.ORGS.items():
        org, created = Organisation.objects.get_or_create(slug=k)
        org.load_from_yaml()
        if default_slug is None:
            default_slug = k
    return default_slug


def merge_pdfs(
    front: Union[str, Path],
    contents: Union[str, Path],
    output: Union[str, Path],
    start_page: int = 1,
):
    """
    replace front page with proper front page
    """
    pdf_writer = PdfFileWriter()

    front_page = PdfFileReader(front)
    pdf_writer.addPage(front_page.getPage(0))

    pdf_reader = PdfFileReader(contents)
    for page in range(start_page, pdf_reader.getNumPages()):
        pdf_writer.addPage(pdf_reader.getPage(page))
    with open(output, "wb") as fh:
        pdf_writer.write(fh)


def pdf_page_to_png(source_pdf: Union[Path, str], destination: Union[Path, str]):
    """
    get front page png from pdf
    """
    doc = fitz.open(source_pdf)
    page = doc.loadPage(0)  # number of page
    pix = page.getPixmap()
    pix.writePNG(destination)


def create_thumbnail(
    source: Union[Path, str], destination: Union[Path, str], base_width: int = 110
):
    """
    get a thumbnail version of an image (in this case, front cover)
    """
    img = Image.open(source)
    wpercent = base_width / float(img.size[0])
    hsize = int((float(img.size[1]) * float(wpercent)))
    img = img.resize((base_width, hsize), Image.ANTIALIAS)
    img.save(destination)


def create_hero(
    source: Union[Path, str], destination: Union[Path, str], base_width: int = 1024
):
    """
    Create a hero image from the header image
    """
    print("resizing hero image")
    target_height = 680
    img = Image.open(source)
    wpercent = base_width / float(img.size[0])
    hsize = int((float(img.size[1]) * float(wpercent)))
    img = img.resize((base_width, hsize), Image.ANTIALIAS)
    height = img.size[1]
    img.save(destination, optimize=True, quality=95)


def select_doc(func: Callable) -> Callable:
    """
    decorator that allows a single or multiple documents to be processed
    by a keyword function that expects only the slug
    """

    def inner(self, inp):
        protected_terms = ["refresh"]
        inp = inp.strip().lower()
        inp = inp.split(" ")
        pass_down = " ".join([x for x in inp if x in protected_terms])
        inp = [x for x in inp if x not in protected_terms + [""]]
        # use current doc
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

    inner.__doc__ = func.__doc__

    return inner


cmd.input = Prompt.ask


class CatchOut:
    def write(self, text):
        print(text, end="")


class SPPrompt(cmd.Cmd):
    intro = "🔥🔥🔥 [green]Stringprint document manager.[/green] Type [green]help[/green] or [green]?[/green] to list commands. 🔥🔥🔥\n"
    prompt = "[blue](stringprint)[/blue] "

    def __init__(self, *args, **kwargs):
        self.current_org: Optional[str] = None
        self.current_doc: Optional[str] = None
        self.avaliable_docs: List[str] = []
        self.running_server: Optional[int] = None
        self.full_refresh: bool = False
        super().__init__(*args, **kwargs)

    def do_startserver(self, inp):
        """
        Start the preview server
        """
        if self.running_server is not None:
            print("Stop server first")
            return None

        f = open(os.devnull, "w")

        cmd = "python manage.py runserver 0.0.0.0:8000"
        p = Popen(cmd.split(), cwd="stringprint2", stdout=f, stderr=f, stdin=f)
        print(f"Started server with pid {p.pid}")
        self.running_server = p.pid
        self.print_status()

    def do_stopserver(self, inp):
        """
        Stop the preview server
        """
        if self.running_server:
            print("No server running")
            return None
        print("Stopping preview server")
        os.kill(self.running_server, signal.SIGTERM)  # or signal.SIGKILL
        self.running_server = None

    def do_status(self, imp):
        """
        print current document status
        """
        self.print_status()

    def print_status(self):
        print("")
        if self.current_org:
            print(f"Current org: [green]{self.current_org.name}[/green]")
        if self.current_doc:
            print(f"Current doc: [green]{self.current_doc}[/green]")
            status = self.current_org.articles.filter(slug=self.current_doc).exists()
            if status:
                last_load = str(
                    self.current_org.articles.get(slug=self.current_doc).last_updated
                )

                upload_time_file = self.doc_folder / "upload_time.txt"

                if upload_time_file.exists():
                    txt_date = upload_time_file.open().read()
                    upload_time = datetime.fromisoformat(txt_date)
                    txt_date = str(upload_time)
                else:
                    txt_date = "Never uploaded."

                print(f"Document status: [green]Loaded[/green]")
                print(
                    f"Last loaded from file: [green]{last_load.split('.')[0]}[/green]"
                )
                print(f"Last published: [green]{txt_date.split('.')[0]}[/green]")
                if self.running_server:
                    print(f"Preview: http://127.0.0.1:8000/preview/{self.current_doc}/")
                else:
                    print("[red]Preview server not started.[/red]")
            else:
                print(f"Document status: [red]Unloaded[/red]")

            print("")

    @property
    def doc_folder(self) -> Path:
        return Path(self.current_org.storage_dir, "_docs", self.current_doc)

    def do_refresh(self, inp):
        """
        set default render to full refresh
        """
        self.full_refresh = True

    def do_setorg(self, slug: str):
        """
        set the current org being examined
        """
        self.current_org = Organisation.objects.get(slug=slug)
        self.avaliable_docs = [x.name for x in self.get_valid_doc_folders()]
        if self.avaliable_docs:
            self.do_setdoc(self.avaliable_docs[0])

    def complete_setdoc(self, text, line, start_index, end_index):
        """
        Auto complete based on campaign names
        """
        docs = self.avaliable_docs
        if text:
            return [x for x in docs if x.startswith(text)]
        else:
            return docs

    def do_setdoc(self, slug, silent=False):
        """
        set the current document being processed
        """
        if slug.isdigit():
            slug = self.avaliable_docs[int(slug) + 1]
        doc_folder = Path(self.current_org.storage_dir, "_docs", slug)
        config_file = doc_folder / "settings.yaml"
        if config_file.exists() is False:
            print("No valid folder at: {0}".format(doc_folder))
            return
        self.current_doc = slug
        if silent is False:
            prompt.print_status()

    def loaded_docs(self) -> List[str]:
        dir = Path(self.current_org.storage_dir, "_docs")
        slugs = self.current_org.articles.all().values_list("slug", flat=True)
        return [x.name for x in self.get_valid_doc_folders() if x.name in slugs]

    def unloaded_docs(self) -> List[str]:
        dir = Path(self.current_org.storage_dir, "_docs")
        slugs = self.current_org.articles.all().values_list("slug", flat=True)
        return [x.name for x in self.get_valid_doc_folders() if x.name in slugs]

    def get_valid_doc_folders(self) -> List[Path]:
        special = ["_template"]
        root = Path(self.current_org.storage_dir, "_docs")
        l = [x for x in root.iterdir() if (x / "settings.yaml").exists() and x.name not in [special]]

        l.sort()
        return l

    def do_listdocs(self, silent: bool = False):
        """
        List all documents for the current org
        """
        slugs = self.current_org.articles.all().values_list("slug", flat=True)
        x = 0
        for doc_folder in self.get_valid_doc_folders():
            x += 1
            slugged = doc_folder.name in slugs
            if slugged:
                if not silent:
                    print(f"{x}. [blue]{doc_folder.name}[/blue]")
            else:
                if not silent:
                    print(f"{x}. [red]{doc_folder.name}  (unloaded)[/red]")

    def do_load(self, inp):
        """
        Load current doc if one set
        if input is 'all' or 'unloaded' load
        all or all unloaded documents.
        """
        if inp is None and self.current_doc:
            self.do_process(inp)
        if inp == "all":
            self.do_loadall("")
        if inp == "unloaded":
            self.do_loadunloaded("")

    def do_loadall(self, inp):
        """
        Load all unloaded documents for the current org
        """
        dir = Path(self.current_org.storage_dir, "_docs")
        for f in os.listdir(dir):
            doc_folder = Path(dir, f)
            config_file = Path(doc_folder, "settings.yaml")
            if os.path.exists(config_file):
                self.do_setdoc(f)
                self.do_process(inp)

    def do_loadunloaded(self, inp):
        """
        Load all unloaded documents for the current org
        """
        dir = Path(self.current_org.storage_dir, "_docs")
        slugs = self.current_org.articles.all().values_list("slug", flat=True)
        unloaded = self.unloaded_docs()
        for doc in unloaded:
            self.do_setdoc(doc)
            self.do_process(inp)

    def do_listorgs(self, inp):
        """
        List valid organisations.
        Generally should just be one org these days.
        Multiple orgs is a legacy function.
        """
        for n, o in enumerate(Organisation.objects.all()):
            print(f"{n}. {o.slug}")

    def do_publish_updated(self, inp):
        """
        ### unfinished
        republish any that have been updated since last time
        they were published
        """
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
        """
        Convert word document to markdown for current doc
        Expects there is only one word document in the doc directory.
        exports to 'document.md'
        """
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
            docx = Path(f, docxs[0])
            dest = Path(f, "document.md")
            convert_word(docx, dest, demote)

    @select_doc
    def do_process(self, refresh: str):
        """
        Load and process current script
        """
        if "--refresh" in refresh:
            refresh_header = True
        else:
            refresh_header = False
        doc, created = Article.objects.get_or_create(
            org=self.current_org, slug=self.current_doc
        )
        doc.load_from_yaml(self.doc_folder, refresh_header)
        doc.import_assets(Path(self.doc_folder, "assets"), refresh_header)
        doc.load_from_file()
        doc.process()
        print("Finished Processing: {0}".format(doc.title))
        self.print_status()

    @select_doc
    def do_command(self, command):
        """
        Run arbitary python script from 'script' directory of org working dir.
        """
        doc, created = Article.objects.get_or_create(
            org=self.current_org, slug=self.current_doc
        )
        doc.load_from_yaml(self.doc_folder)
        doc.run_command(command)
        print("Finished command {1}: {0}".format(doc.title, command))

    @select_doc
    def do_preprocess(self, inp):
        """
        Run preprocess script as configured for this document.
        """
        doc, created = Article.objects.get_or_create(
            org=self.current_org, slug=self.current_doc
        )
        doc.load_from_yaml(self.doc_folder)
        doc.run_command("preprocess")
        print("Finished pre-processing: {0}".format(doc.title))

    @select_doc
    def do_publish(self, inp):
        """
        Run publish script as configured for this org.
        """
        doc, created = Article.objects.get_or_create(
            org=self.current_org, slug=self.current_doc
        )
        doc.load_from_yaml(self.doc_folder)
        doc.run_command("publish")
        print("Finished publishing: {0}".format(doc.title))

    def do_quit(self, inp):
        """
        quit shortcut
        """
        quit()

    def do_exit(self, inp):
        """
        quit shortcut
        """
        quit()

    @select_doc
    def do_render(self, inp):
        """
        render web format of current document
        """
        if self.running_server is None:
            print("Need preview server to render documents")
            return None
        refresh_all = "refresh" in inp.lower() or self.full_refresh
        slug = self.current_doc
        bake_folder = self.current_org.publish_dir
        path = Path(bake_folder, slug)
        doc, created = Article.objects.get_or_create(
            org=self.current_org, slug=self.current_doc
        )
        doc.render(path, refresh_all=refresh_all)

    @select_doc
    def do_renderebook(self, inp):
        """
        render ebook file of current document
        """
        refresh_all = "refresh" in inp.lower() or self.full_refresh
        slug = self.current_doc
        bake_folder = self.current_org.publish_dir
        path = Path(bake_folder, slug)
        doc, created = Article.objects.get_or_create(
            org=self.current_org, slug=self.current_doc
        )
        doc.create_ebook(path)

    @select_doc
    def do_renderkindle(self, inp):
        """
        render kindle file of current document
        """
        refresh_all = "refresh" in inp.lower() or self.full_refresh
        slug = self.current_doc
        bake_folder = self.current_org.publish_dir
        path = Path(bake_folder, slug)
        doc, created = Article.objects.get_or_create(
            org=self.current_org, slug=self.current_doc
        )
        doc.create_kindle(path)

    @select_doc
    def do_renderzip(self, inp):
        """
        Create zip archive of complete published
        version of current document
        """
        if self.running_server is None:
            print("Need preview server to render documents")
            return None
        refresh_all = "refresh" in inp.lower() or self.full_refresh
        slug = self.current_doc
        origin_folder = self.current_org.storage_dir
        path = Path(origin_folder, "_docs", slug)
        zip_destination = Path(path, slug)
        doc, created = Article.objects.get_or_create(
            org=self.current_org, slug=self.current_doc
        )
        zip_location = doc.render_to_zip(zip_destination, refresh_all=refresh_all)
        print(f"Zip created at {zip_location}")

    @select_doc
    def do_mergepdf(self, inp):
        """
        merge 'cover.pdf' and page 2 onwards of 'contents.pdf' for current document.
        """
        df = self.doc_folder
        front_page = Path(df, "cover.pdf")
        contents = Path(df, "contents.pdf")
        output = Path(df, "{0}.pdf".format(self.current_doc))
        merge_pdfs(front_page, contents, output)

    @select_doc
    def do_pdfpng(self, inp):
        """
        Create png of front page for current document
        """
        df = self.doc_folder
        front_page = Path(df, "cover.pdf")
        output = Path(df, "{0}-cover.png".format(self.current_doc))
        thumb = Path(df, "{0}-thumbnail.png".format(self.current_doc))
        pdf_page_to_png(front_page, output)
        create_thumbnail(output, thumb)

    @select_doc
    def do_hero(self, inp):
        """
        Create hero image for current document
        """
        yaml_data = get_yaml(Path(self.doc_folder, "settings.yaml"))
        hero_location = yaml_data["header"]["location"]
        hero_path = Path(self.doc_folder, hero_location)
        destination = Path(self.doc_folder, "hero.png")
        create_hero(hero_path, destination)

    def do_newdoc(self, inp):
        """
        Create a new document from the template
        """
        template_path = str(Path(self.current_org.storage_dir, "_docs", "_template"))
        output_dir = str(Path(self.current_org.storage_dir, "_docs"))

        cookiecutter(template_path, output_dir=output_dir )

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

    args = sys.argv[1:]

    special_args = ["--no-server", "--continue"]

    dont_start_server = "--no-server" in args
    continue_in_shell = "--continue" in args
    do_refresh = "--refresh" in args
    args = [x for x in args if x not in special_args]

    instructions = []
    current_instruction = []
    for n, a in enumerate(args):
        if a.startswith("--"):
            if current_instruction:
                instructions.append(current_instruction)
                current_instruction = []
            current_instruction.append(a[2:])
        else:
            current_instruction.append(a)
    instructions.append(current_instruction)

    print(SPPrompt.intro)
    default_org = load_org_details()
    prompt = SPPrompt(stdout=CatchOut())
    prompt.do_startserver("args")
    prompt.do_setorg(default_org)
    if do_refresh:
        prompt.do_refresh("")
    for i in instructions:
        prompt.onecmd(" ".join(i))
    if not sys.argv[1:] or continue_in_shell:
        prompt.cmdloop(intro="")
