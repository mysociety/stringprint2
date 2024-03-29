from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, TypeVar, Union

from PyPDF2 import PdfFileReader, PdfFileWriter
from stringprint.models import Article
from stringprint.tools.word_convert import convert_word
from useful_inkleby.files import QuickText

from .google_download import GoogleDownloader


def merge_pdfs(
    front: Path,
    contents: Path,
    output: Path,
    start_page: int = 1,
):
    """
    replace front page with proper front page
    """
    pdf_writer = PdfFileWriter()

    front_page = PdfFileReader(str(front))
    pdf_writer.addPage(front_page.getPage(0))

    pdf_reader = PdfFileReader(str(contents))
    for page in range(start_page, pdf_reader.getNumPages()):
        pdf_writer.addPage(pdf_reader.getPage(page))
    with open(output, "wb") as fh:
        pdf_writer.write(fh)


class SectionActionBase:
    def get_sections_order(
        self, qt: QuickText
    ) -> Tuple[Dict[str, List[str]], List[str]]:
        sections = {}
        current_header = "start"
        current_section = []
        order = []
        for l in qt.lines():
            if l.startswith("# "):
                sections[current_header] = current_section
                order.append(current_header)
                current_header = l.strip()
                current_section = []
            current_section.append(l)
        sections[current_header] = current_section
        order.append(current_header)

        return sections, order

    def process_text(self, qt: QuickText) -> QuickText:
        return qt

    def __call__(self, text: str) -> str:
        qt = self.process_text(QuickText(text))
        return qt.text


@dataclass
class SectionDelete(SectionActionBase):
    """
    Delete a named section from the document
    """

    section: str

    def process_text(self, qt: QuickText) -> QuickText:
        """
        Swap sections around in document
        """
        sections, order = self.get_sections_order(qt)

        if self.section not in order:
            raise ValueError("'{self.section}' not in section list.")

        order.pop(order.index(self.section))
        new_lines = []
        for s in order:
            new_lines.extend(sections[s])

        return QuickText("\n".join(new_lines))


@dataclass
class SectionMove(SectionActionBase):
    """
    Swap sections around in the document
    """

    section: str
    to_delete: Optional[str] = None
    after: Optional[str] = None

    def __post_init__(self):
        if self.before is None and self.after is None:
            raise ValueError("SectionMove requires 'before' or 'after' parameter")

    def process_text(self, qt: QuickText) -> QuickText:
        """
        Swap sections around in document
        """
        sections, order = self.get_sections_order(qt)

        if self.section not in order:
            raise ValueError("'{self.section}' not in section list.")

        if self.before and self.before not in order:
            raise ValueError("'{self.before}' not in section list.")

        if self.after and self.after not in order:
            raise ValueError("'{self.after}' not in section list.")

        order.pop(self.section)

        if self.before:
            pos = order.index(self.before)
        if self.after:
            pos = order.index(self.after) + 1

        order.insert(pos, self.section)

        new_lines = []
        for s in order:
            new_lines.extend(sections[s])

        return QuickText("\n".join(new_lines))


@dataclass
class SectionMove(SectionActionBase):
    section: str
    before: Optional[str] = None
    after: Optional[str] = None

    def __post_init__(self):
        if self.before is None and self.after is None:
            raise ValueError("SectionMove requires 'before' or 'after' parameter")

    def process_text(self, qt: QuickText) -> QuickText:
        """
        Swap sections around in document
        """
        sections, order = self.get_sections_order(qt)

        if self.section not in order:
            raise ValueError(f"'{self.section}' not in section list.")

        if self.before and self.before not in order:
            raise ValueError(f"'{self.before}' not in section list.")

        if self.after and self.after not in order:
            raise ValueError(f"'{self.after}' not in section list.")

        order.pop(order.index(self.section))

        if self.before:
            pos = order.index(self.before)
        if self.after:
            pos = order.index(self.after) + 1

        order.insert(pos, self.section)

        new_lines = []
        for s in order:
            new_lines.extend(sections[s])

        return QuickText("\n".join(new_lines))


class BaseTextAction:
    def __call__(self, text: str):
        return text


@dataclass
class TextSnip(BaseTextAction):
    """
    remove all text between start phrase and end phrase
    """

    start_snip: str
    end_snip: str

    def __call__(self, text: str) -> str:
        start_position = text.find(self.start_snip)
        end_position = text.find(self.end_snip, start_position) + len(self.end_snip)
        return text[:start_position] + text[end_position:]


general_find_replace = [("]][[", "]]\n\n[[")]


class BasePreprocess:
    google_download: bool = True
    google_download_formats: list = ["contents.pdf", "doc_source.docx"]
    word_source_file: Optional[str] = None
    word_demote: bool = False  # push everyone down one header level
    word_convert: bool = True
    input_filename: str = "document-word.md"
    output_filename: str = "document.md"
    pdf_cover: str = "cover.pdf"
    pdf_contents: str = "contents.pdf"
    pdf_output_filename: Union[str, Callable] = lambda self: self.article.slug + ".pdf"
    pdf_start_page: int = 1
    pdf_merge: bool = True
    find_replace: Optional[List[Tuple[str, str]]] = None
    text_actions: Optional[List[Callable]] = None

    def from_article(cls, article: "Article") -> SubClassPreprocess:
        return cls(article)

    def __init__(self, article: Article):
        self.article: Article = article
        self.doc_folder: Path = Path(article.storage_dir)
        self.source_file: Path = self.doc_folder / self.__class__.input_filename
        self.dest_file: Path = self.doc_folder / self.__class__.output_filename

    def __call__(self):
        self.process()

    def process(self) -> None:
        """
        Run standard features
        """
        self.do_google_download()
        self.do_convert_word()
        self.import_markdown()
        self.combine_pdfs()
        self.preprocess()
        self.do_find_replace()
        self.do_text_actions()
        self.postprocess()
        self.output()

    def do_text_actions(self):
        """
        feed the text through a series of functions
        Generally classes defined here, but any function
        that expects a str and returns a str works
        """
        if self.__class__.text_actions == None:
            return None

        for action in self.__class__.text_actions:
            self.qt.text = action(self.qt.text)

    def do_google_download(self):
        """
        Download specified files through google api
        """
        if (
            self.__class__.google_download
            and "google_doc_url" in self.article.extra_values
        ):
            google_doc_url = self.article.extra_values["google_doc_url"]
            gd = GoogleDownloader()
            for f in self.__class__.google_download_formats:
                dest = self.doc_folder / f
                gd.download_file(dest=dest, url=google_doc_url)

    def import_markdown(self):
        """
        Import the source file as a QuickText object
        """
        self.qt = QuickText().open(self.source_file)

    def output(self) -> None:
        """
        Save to the destination file
        """
        comment = "<!--- This document is generated by the preprocess steps and should not be edited directly -->\n"
        self.qt.text = comment + self.qt.text
        self.qt.save(str(self.dest_file))
        print("outputted document")

    def combine_pdfs(self) -> None:
        """
        Combine the cover and contents pdfs
        """
        front_page = self.doc_folder / self.__class__.pdf_cover
        contents = self.doc_folder / self.__class__.pdf_contents

        start_page = self.__class__.pdf_start_page
        if callable(self.pdf_output_filename):
            filename = self.pdf_output_filename()
        else:
            filename = self.pdf_output_filename

        output = self.doc_folder / filename

        if not (any([front_page.exists(), contents.exists()])):
            print("neither source files for merging pdf, skipping")
            return

        if contents.exists() and not front_page.exists():
            print("no front page, just reusing contents page")
            shutil.copy(contents, output)
            return

        merge_pdfs(front_page, contents, output, start_page)
        print("combined pdfs")

    def do_find_replace(self) -> None:
        """
        do a find and replace on specified strings in the document
        """

        find_replace = general_find_replace + (self.__class__.find_replace or [])

        for old, new in find_replace:
            self.qt.text = self.qt.text.replace(old, new)
        print("Ran find replace")

    def do_convert_word(self) -> None:
        """
        Generate source doc from word document
        """
        if self.__class__.word_convert is False:
            return ""

        if self.__class__.word_source_file is None:
            docx_files = list(self.doc_folder.glob("*.docx"))
            if len(docx_files) == 0:
                raise ValueError(
                    f"Specified to convert from word, but no .docx files in {self.doc_folder}"
                )
            if len(docx_files) > 1:
                raise ValueError(
                    f"More than one word document in {self.doc_folder}, specify the exact file in 'convert_word_to_input'"
                )
            docx_file = docx_files[0]
        elif isinstance(self.__class__.word_source_file, str):
            docx_file = self.doc_folder / self.__class__.word_source_file
        else:
            raise ValueError(
                "Unrecognised input for convert_word_to_input : {word_input}"
            )

        convert_word(docx_file, self.source_file, self.word_demote)

    def preprocess(self) -> None:
        """
        Placeholder for subclassing

        modify or replace self.qt
        """
        pass

    def postprocess(self) -> None:
        """
        Placeholder for subclassing

        modify or replace self.qt
        """
        pass


SubClassPreprocess = TypeVar("SubClassPreprocess", bound=BasePreprocess)
