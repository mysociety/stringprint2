# -*- coding: utf-8 -*-

import cmd
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, List, Optional, Tuple, Union

PACKAGE_ROOT = str(Path(__file__).parent)
if PACKAGE_ROOT not in sys.path:
    sys.path.insert(0, PACKAGE_ROOT)

import django
import rich
from cookiecutter.main import cookiecutter
from rich.panel import Panel
from rich.prompt import Prompt
from stringprint2.cli_arguments import parse_shell_options
from stringprint2.configuration.loaders import validate_config
from stringprint2.configuration.models import PublicationConfig
from stringprint2.media_files import (
    create_hero,
    create_thumbnail,
    merge_pdfs,
    pdf_page_to_png,
)
from stringprint2.services.publication_workflow import run_publication_command
from stringprint2.services.publication_catalog import (
    PublicationCatalog,
    discover_publications,
)
from stringprint2.services.publication_freshness import publication_needs_update
from stringprint2.services.publication_rendering import PublicationRenderFormat
from publication_management.foreground import (
    run_foreground_publication_operation,
    run_locked_publication_action,
)
from stringprint2.services.publication_operations import (
    ArchivePublicationRequest,
    LoadPublicationRequest,
    ProcessPublicationRequest,
    PublishPublicationRequest,
    RenderPublicationRequest,
)
from stringprint2.services.process_supervisor import (
    LocalProcessSupervisor,
    ManagedProcessSpec,
)
from stringprint2.services.document_selection import (
    DocumentSelectionScope,
    parse_document_selection,
)

print = rich.print

os.environ.pop("DJANGO_SETTINGS_MODULE", None)


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "proj.settings")
django.setup()

from django.conf import settings

if TYPE_CHECKING:
    from stringprint2.stringprint.models import Article, Organisation
    from stringprint2.stringprint.tools.word_convert import convert_word

else:
    from stringprint.models import Article, Organisation
    from stringprint.tools.word_convert import convert_word


class PanelPrint:
    """
    Helper for printing list of items in a panel
    """

    def __init__(self, expand: bool = False, **kwargs):
        self.items: List[str] = []
        self.panel_properties = kwargs
        self.panel_properties["expand"] = expand

    def print(self, item: str) -> None:
        self.items.append(item)

    def display(self) -> None:
        panel = Panel("\n".join(self.items), **self.panel_properties)
        rich.print(panel)


def load_org_details() -> str | None:
    """
    ingest org details from files
    """
    default_slug = os.environ.get("DEFAULT_ORG")
    for k, v in settings.ORGS.items():
        org, created = Organisation.objects.get_or_create(slug=k)
        org: Organisation
        org.load_from_yaml()
        if default_slug is None:
            default_slug = k
    return default_slug


def select_doc(func: Callable) -> Callable:
    """
    decorator that allows a single or multiple documents to be processed
    by a keyword function that expects only the slug
    """

    def inner(self, inp):
        selection = parse_document_selection(inp)
        if selection.scope is DocumentSelectionScope.CURRENT:
            func(self, selection.option_text)
        elif selection.scope is DocumentSelectionScope.ALL:
            print("running for all")
            for slug in self.loaded_docs():
                self.do_setdoc(slug)
                func(self, selection.option_text)
        else:
            for slug in selection.slugs:
                self.do_setdoc(slug)
                func(self, selection.option_text)

    inner.__doc__ = func.__doc__

    return inner


cmd.input = Prompt.ask


class CatchOut:
    def write(self, text):
        print(text, end="")


class SPPrompt(cmd.Cmd):
    intro = "🧶🧶🧶 [green]Stringprint document manager.[/green] Type [green]help[/green] or [green]?[/green] to list commands. 🧶🧶🧶\n"
    prompt = "[blue](stringprint)[/blue] "

    def __init__(self, *args, **kwargs):
        self.current_org: Optional[str] = None
        self.current_doc: Optional[str] = None
        self.avaliable_docs: List[str] = []
        self.process_supervisor = LocalProcessSupervisor()
        self.running_server: Optional[int] = None
        self.running_worker: Optional[int] = None
        self.full_refresh: bool = False
        super().__init__(*args, **kwargs)

    def do_startserver(self, inp="noprint"):
        """Start the preview server and publication operation worker."""
        if self.running_server is not None or self.running_worker is not None:
            print("Stop the local services first")
            return None

        working_directory = Path("stringprint2", "stringprint2")
        log_directory = Path(".stringprint", "logs")
        worker = self.process_supervisor.start(
            ManagedProcessSpec(
                name="worker",
                arguments=(sys.executable, "manage.py", "run_publication_operations"),
                working_directory=working_directory,
                log_path=log_directory / "worker.log",
            )
        )
        try:
            server = self.process_supervisor.start(
                ManagedProcessSpec(
                    name="server",
                    arguments=(
                        sys.executable,
                        "manage.py",
                        "runserver",
                        "0.0.0.0:8000",
                    ),
                    working_directory=working_directory,
                    log_path=log_directory / "server.log",
                )
            )
        except Exception:
            self.process_supervisor.stop("worker")
            raise

        self.running_worker = worker.process_id
        self.running_server = server.process_id
        message = (
            f"Started server with pid {server.process_id} and worker with pid "
            f"{worker.process_id}"
        )
        if "noprint" not in inp:
            print(message)
            self.print_status()
            return None
        return message

    def do_stopserver(self, inp):
        """Stop the preview server and publication operation worker."""
        if self.running_server is None and self.running_worker is None:
            print("No local services running")
            return None
        print("Stopping preview server and worker")
        self.process_supervisor.stop_all()
        self.running_server = None
        self.running_worker = None

    def do_status(self, imp):
        """
        print current document status
        """
        self.print_status()

    def print_status(self):
        """
        Print the current status of the document
        """

        panel = PanelPrint(title="Current document status", padding=1)
        print = panel.print

        for name, label, attribute in (
            ("server", "Preview server", "running_server"),
            ("worker", "Operation worker", "running_worker"),
        ):
            if getattr(self, attribute) is None:
                print(f"{label}: [red]not running[/red]")
                continue
            status = self.process_supervisor.status(name)
            if status.running:
                print(
                    f"{label}: [green]running[/green] "
                    f"(pid {status.process_id}, log {status.log_path})"
                )
            else:
                print(
                    f"{label}: [red]stopped[/red] "
                    f"(exit {status.return_code}, log {status.log_path})"
                )
                setattr(self, attribute, None)

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
                    upload_time = datetime.fromisoformat(txt_date.strip())
                    txt_date = str(upload_time)
                else:
                    txt_date = "Never uploaded."

                print(f"Document status: [green]Loaded[/green]")
                print(
                    f"Last loaded from file: [green]{last_load.split('.')[0]}[/green]"
                )
                print(f"Last published: [green]{txt_date.split('.')[0]}[/green]")
                if self.running_server:
                    print(
                        f"Preview: [bright_blue]http://127.0.0.1:8000/preview/{self.current_doc}/[/bright_blue]"
                    )
                else:
                    print("[red]Preview server not started.[/red]")
            else:
                print(f"Document status: [red]Unloaded[/red]")
        panel.display()

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
            print("Run `preprocess` and `process` to load document.")
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
            slug = self.avaliable_docs[int(slug) - 1]
        doc_folder = Path(self.current_org.storage_dir, "_docs", slug)
        config_file = doc_folder / "settings.yaml"
        if config_file.exists() is False:
            print("No valid folder at: {0}".format(doc_folder))
            return
        self.current_doc = slug
        if silent is False:
            self.print_status()

    def publication_catalog(self) -> PublicationCatalog:
        """
        Return source publications classified by their database load state.
        """

        root = Path(self.current_org.storage_dir, "_docs")
        loaded_slugs = self.current_org.articles.values_list("slug", flat=True)
        return discover_publications(root, loaded_slugs)

    def loaded_docs(self) -> list[str]:
        return list(self.publication_catalog().loaded_slugs)

    def unloaded_docs(self) -> list[str]:
        return list(self.publication_catalog().unloaded_slugs)

    def get_valid_doc_folders(self) -> list[Path]:
        return [entry.folder for entry in self.publication_catalog().entries]

    def do_listdocs(self, silent: bool = False):
        """
        List all documents for the current org
        """

        panel = PanelPrint(
            padding=1,
            style="yellow",
            title="Document list",
            subtitle=r"(set document using 'setdoc \[slug or number]')",
        )
        print = panel.print
        slugs = self.current_org.articles.all().values_list("slug", flat=True)
        x = 0
        for doc_folder in self.get_valid_doc_folders():
            x += 1
            slugged = doc_folder.name in slugs
            if slugged:
                if not silent:
                    print(f"{x}. [bright_blue]{doc_folder.name}[/bright_blue]")
            else:
                if not silent:
                    print(
                        f"{x}. [bright_red]{doc_folder.name}  (unloaded)[/bright_red]"
                    )
        panel.display()

    def do_load(self, refresh):
        """
        Load current doc if one set
        Does not process input file or assets
        'process' does all three.

        Call load to get details before running preprocess
        """
        if "--refresh" in refresh or self.full_refresh:
            refresh_header = True
        else:
            refresh_header = False
        doc, created = Article.objects.get_or_create(
            org=self.current_org, slug=self.current_doc
        )
        request = LoadPublicationRequest(
            organisation_slug=self.current_org.slug,
            publication_slug=self.current_doc,
            refresh_header=refresh_header,
        )
        run_foreground_publication_operation(
            request,
            doc,
            self.doc_folder,
            Path(self.current_org.publish_dir, self.current_doc),
        )

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
        Process and republish documents changed since their last publication.
        """
        for f in self.get_valid_doc_folders():
            self.do_setdoc(f.name, silent=True)
            needs_update = self.do_check_for_update(inp)
            if needs_update:
                print(f"Republishing {f.name}")
                self.do_process("refresh")
                self.do_renderzip("refresh")
                self.do_publish("no-render-zip")

    def do_check_for_update(self, inp=""):
        """
        if document file or settings has been updated since last upload
        return true
        """
        doc_folder = Path(self.doc_folder)
        settings_file = doc_folder / "settings.yaml"
        config = validate_config(settings_file, PublicationConfig)
        return publication_needs_update(doc_folder, config)

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
            run_locked_publication_action(
                self.doc_folder, lambda: convert_word(docx, dest, demote)
            )

    @select_doc
    def do_process(self, refresh: str):
        """
        Load and process the current document
        """
        if "--no-refresh" in refresh:
            refresh_header = False
        else:
            refresh_header = True
        preprocess = "--no-preprocess" not in refresh
        doc, created = Article.objects.get_or_create(
            org=self.current_org, slug=self.current_doc
        )
        request = ProcessPublicationRequest(
            organisation_slug=self.current_org.slug,
            publication_slug=self.current_doc,
            refresh_header=refresh_header,
            preprocess=preprocess,
        )
        result = run_foreground_publication_operation(
            request,
            doc,
            self.doc_folder,
            Path(self.current_org.publish_dir, self.current_doc),
        )
        print(f"Finished Processing: {result.title}")
        self.print_status()

    @select_doc
    def do_command(self, command):
        """
        Run arbitary python script from 'script' directory of org working dir.
        Or specified in the current document's yaml.
        """
        doc, created = Article.objects.get_or_create(
            org=self.current_org, slug=self.current_doc
        )
        result = run_locked_publication_action(
            self.doc_folder,
            lambda: run_publication_command(doc, self.doc_folder, command),
        )
        print(f"Finished command {command}: {result.title}")

    @select_doc
    def do_preprocess(self, inp):
        """
        Run the preprocess steps (if present).
        The preprocess steps are those that *create*
        the markdown file and the assets list.

        """
        doc, created = Article.objects.get_or_create(
            org=self.current_org, slug=self.current_doc
        )
        result = run_locked_publication_action(
            self.doc_folder,
            lambda: run_publication_command(doc, self.doc_folder, "preprocess"),
        )
        print(f"Finished pre-processing: {result.title}")

    @select_doc
    def do_publish(self, inp):
        """
        Run publish script as configured for this org.
        Add 'no-render-zip' as an argument not to render a zip as part of this stpe.
        """
        if not "no-render-zip" in inp:
            self.do_renderzip("")

        doc, created = Article.objects.get_or_create(
            org=self.current_org, slug=self.current_doc
        )
        request = PublishPublicationRequest(
            organisation_slug=self.current_org.slug,
            publication_slug=self.current_doc,
            render_archive=False,
        )
        result = run_foreground_publication_operation(
            request,
            doc,
            self.doc_folder,
            Path(self.current_org.publish_dir, self.current_doc),
        )
        print(f"Finished publishing: {result.title}")

    def do_quit(self, inp):
        """Stop owned services and leave the interactive shell."""
        if self.running_server is not None or self.running_worker is not None:
            self.do_stopserver("")
        return True

    def do_exit(self, inp):
        """Stop owned services and leave the interactive shell."""
        return self.do_quit(inp)

    def do_EOF(self, inp):
        """Treat end-of-input as a clean managed shutdown."""
        return self.do_quit(inp)

    @select_doc
    def do_render(self, inp):
        """
        render web format of current document
        """
        if self.running_server is None:
            print("Need preview server to render documents")
            return None
        refresh_all = "refresh" in inp.lower() or self.full_refresh
        path = Path(self.current_org.publish_dir, self.current_doc)
        doc, created = Article.objects.get_or_create(
            org=self.current_org, slug=self.current_doc
        )
        request = RenderPublicationRequest(
            organisation_slug=self.current_org.slug,
            publication_slug=self.current_doc,
            output_format=PublicationRenderFormat.WEB,
            refresh=refresh_all,
        )
        run_foreground_publication_operation(
            request,
            doc,
            self.doc_folder,
            path,
        )

    @select_doc
    def do_renderebook(self, inp):
        """
        render ebook file of current document
        """
        path = Path(self.current_org.publish_dir, self.current_doc)
        doc, created = Article.objects.get_or_create(
            org=self.current_org, slug=self.current_doc
        )
        request = RenderPublicationRequest(
            organisation_slug=self.current_org.slug,
            publication_slug=self.current_doc,
            output_format=PublicationRenderFormat.EPUB,
        )
        run_foreground_publication_operation(
            request,
            doc,
            self.doc_folder,
            path,
        )

    @select_doc
    def do_renderkindle(self, inp):
        """
        render kindle file of current document
        """
        path = Path(self.current_org.publish_dir, self.current_doc)
        doc, created = Article.objects.get_or_create(
            org=self.current_org, slug=self.current_doc
        )
        request = RenderPublicationRequest(
            organisation_slug=self.current_org.slug,
            publication_slug=self.current_doc,
            output_format=PublicationRenderFormat.KINDLE,
        )
        run_foreground_publication_operation(
            request,
            doc,
            self.doc_folder,
            path,
        )

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
        path = self.doc_folder
        doc, created = Article.objects.get_or_create(
            org=self.current_org, slug=self.current_doc
        )
        # specify some extra files to dump in the zip

        if not "no-hero" in inp:
            self.do_hero("")
        if not "no-thumbnail" in inp:
            self.do_pdfpng("")

        request = ArchivePublicationRequest(
            organisation_slug=self.current_org.slug,
            publication_slug=slug,
            refresh=refresh_all,
        )
        result = run_foreground_publication_operation(
            request,
            doc,
            path,
            Path(self.current_org.publish_dir, slug),
        )
        print(f"Zip created at {result.location}")

    @select_doc
    def do_mergepdf(self, inp):
        """
        merge 'cover.pdf' and page 2 onwards of 'contents.pdf' for current document.
        """
        df = self.doc_folder
        front_page = Path(df, "cover.pdf")
        contents = Path(df, "contents.pdf")
        output = Path(df, "{0}.pdf".format(self.current_doc))
        run_locked_publication_action(
            self.doc_folder, lambda: merge_pdfs(front_page, contents, output)
        )

    @select_doc
    def do_pdfpng(self, inp):
        """
        Create png of front page for current document
        """
        df = self.doc_folder
        front_page = Path(df, "cover.pdf")
        output = Path(df, "{0}-cover.png".format(self.current_doc))
        thumb = Path(df, "{0}-thumbnail.png".format(self.current_doc))
        if front_page.exists() is False:
            print(
                "[red]No cover.pdf found in {0}[/red], not generating thumbnail".format(
                    df
                )
            )
            return None

        def create_images() -> None:
            pdf_page_to_png(front_page, output)
            create_thumbnail(output, thumb)

        run_locked_publication_action(self.doc_folder, create_images)

    @select_doc
    def do_hero(self, inp):
        """
        Create hero image for current document
        """
        config = validate_config(
            self.doc_folder / "settings.yaml",
            PublicationConfig,
        )
        if config.header is not None:
            hero_path = self.doc_folder / config.header.location
            destination = Path(self.doc_folder, "hero.png")
            run_locked_publication_action(
                self.doc_folder, lambda: create_hero(hero_path, destination)
            )

    def do_newdoc(self, inp):
        """
        Create a new document from the template
        """
        template_path = str(Path(self.current_org.storage_dir, "_docs", "_template"))
        output_dir = str(Path(self.current_org.storage_dir, "_docs"))

        final_dir = cookiecutter(template_path, output_dir=output_dir)
        if final_dir:
            dir_name = Path(final_dir).parts[-1]
            self.do_setdoc(dir_name)

    def default(self, line):
        options = line.split(" ")
        first = options[0]
        if self.current_doc:
            doc, created = Article.objects.get_or_create(
                org=self.current_org, slug=self.current_doc
            )
        if first in self.current_org.commands or first in doc.commands:
            run_locked_publication_action(
                self.doc_folder,
                lambda: run_publication_command(doc, self.doc_folder, line),
            )
            print("Finished command {1}: {0}".format(doc.title, line))
        else:
            return super().default(line)


def main(arguments: list[str] | None = None) -> None:
    """Run requested commands, then optionally enter the interactive shell."""
    passed_arguments = sys.argv[1:] if arguments is None else arguments
    options = parse_shell_options(passed_arguments)

    panel = PanelPrint(padding=1, style="green")
    panel.print(SPPrompt.intro)
    default_org = load_org_details()
    if default_org is None:
        raise RuntimeError("No organisations are configured")

    prompt = SPPrompt(stdout=CatchOut())
    if options.start_server:
        panel.print(prompt.do_startserver("noprint"))
    panel.print("")
    panel.print("List available documents with .listdocs.")
    panel.display()

    prompt.do_setorg(default_org)
    if options.refresh:
        prompt.do_refresh("")
    for command in options.commands:
        prompt.onecmd(" ".join(command))
    if not passed_arguments or options.continue_in_shell:
        prompt.cmdloop(intro="")


if __name__ == "__main__":
    main()
