"""Legacy-compatible compiled document data and paragraph identities.

The class names and serialized attributes are the stored format. Template-facing
methods delegate to presentation helpers; parsing lives in tools.deepink.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
import string
from typing import Any, Iterator, List, Optional
from django.utils.safestring import SafeText
from stringprint2.serialization import SerialObject
from stringprint2.presentation import document as presentation
from stringprint2.services.document_compilation import CompilationContext


@dataclass
class FootnoteRegistry:
    """
    Own the footnotes belonging to one document compilation.
    """

    notes: list[Footnote] = field(default_factory=list)


class Footnote(SerialObject):
    def __init__(
        self,
        content: str = "",
        local_ref: str = "",
        registry: FootnoteRegistry | None = None,
    ) -> None:
        self.num = len(registry.notes) + 1 if registry is not None else 1
        self.section_num = self.num
        if "||" in local_ref:
            self.local_ref, self.named_reference = local_ref.split("||")
            self.named_reference = self.named_reference[:-1]
            self.local_ref += "]"
        else:
            self.local_ref = local_ref
            self.named_reference = None
        if registry is not None:
            registry.notes.append(self)

        self.content = ""
        self.set_content(content)

    def set_content(self, content):
        if "||" in content:
            self.named_reference, self.content = content.split("||")
        else:
            self.content = content

    def safe_content(self):
        return presentation.footnote_safe_content(self)

    def format(self, order):
        return presentation.footnote_format(self, order)

    def format_kindle(self):
        return presentation.footnote_format_kindle(self)

    def kindle_content(self):
        return presentation.footnote_kindle_content(self)


class Section(SerialObject):
    def __init__(self, *args, **kwargs) -> None:
        self.id = 0
        self.name = ""
        self.order = 0
        self.catch_up = ""
        self.grafs = []
        self.anchor_offset = ""
        self.visible = True
        self.nav = []
        self.header_asset = None
        self.__dict__.update(kwargs)
        self._version = None  # set during display

    def get_header_asset(self):
        return presentation.section_get_header_asset(self)

    def first_graf_id(self) -> int:
        if self.grafs:
            return self.grafs[0].order

    def save_process(self) -> None:
        """
        execute at the end of loading before being stashed in database
        """
        self.tagged = {x.tag: self.order for x in self.grafs if x.tag}

    def used_assets(self) -> List[Any]:
        """
        which assets are in this section
        """

        assets = [g.asset for g in self.grafs if g.asset]
        if self.header_asset:
            assets.append(self.header_asset)

        return assets

    def next_section(self):
        return presentation.section_next_section(self)

    def prev_section(self):
        return presentation.section_prev_section(self)

    def anchorless_nav_link(self):
        return presentation.section_anchorless_nav_link(self)

    def nav_url(self, include_anchor: bool = True) -> str:
        return presentation.section_nav_url(self, include_anchor)

    def prev_id(self) -> int:
        return self.order - 1

    def prev_if_single_page(self) -> int:
        return presentation.section_prev_if_single_page(self)

    def reduced_name(self):
        return presentation.section_reduced_name(self)

    def grafs_with_titles(self):
        return [x for x in self.grafs if x.title]

    def search_grafs(self) -> Iterator["Graf"]:
        return presentation.section_search_grafs(self)

    def get_grafs_with_titles(self) -> Iterator[Any]:
        return presentation.section_get_grafs_with_titles(self)

    def get_kindle_grafs(self) -> Iterator["Graf"]:
        return presentation.section_get_kindle_grafs(self)

    def get_kindle_extras(self) -> None:
        return presentation.section_get_kindle_extras(self)

    def has_grafs(self) -> int:
        if self.grafs:
            grafs = [x for x in self.grafs if len(x.plain_txt) > 1]
            if grafs:
                return len(grafs)
        return False

    def get_grafs(
        self, just_titles: bool = False, change_footnotes: bool = True
    ) -> Iterator["Graf"]:
        return presentation.section_get_grafs(self, just_titles, change_footnotes)

    def anchor(self) -> str:
        """
        returns an identifiable marker for this section
        from name
        """
        if self.name == "":
            return "start"

        def depuntuate(s):
            return re.sub(r"[^\w\s]", "", s)

        if hasattr(self, "anchor_title") and self.anchor_title:
            title = self.anchor_title
        else:
            title = self.name

        title = " ".join(title.split())
        new = depuntuate(title).replace(" ", "-").strip().lower()
        if self.anchor_offset:
            new += "_" + self.anchor_offset
        new = new.encode("ascii", "ignore").decode("utf-8")

        return new

    class Meta:
        ordering = ["order"]


class Graf(SerialObject):
    seed = 13
    NORMAL = "NO"
    EXTENDED_START = "ES"
    EXTENDED_MIDDLE = "EM"
    EXTENDED_END = "ED"
    EXTENDED_COMPLETE = "EC"
    types = [
        (NORMAL, "Normal"),
        (EXTENDED_START, "Extended Start"),
        (EXTENDED_MIDDLE, "Extended Middle"),
        (EXTENDED_END, "Extended End"),
        (EXTENDED_COMPLETE, "Extended Complete"),
    ]

    def __init__(self, *args, **kwargs) -> None:
        self.id = ""
        self.title = ""
        self.html = ""
        self.plain_txt = ""
        self.header_level = 0
        self.order = 0
        self.real_order = 0
        self.asset = None
        self.type = ""
        self.anchor_title = ""
        self.anchor_offset = ""
        self.blockquote = False
        self.key = ""
        self.start_key = ""
        self.letter_key = ""
        self.letter_seq = ""
        self.end_key = ""
        self.catch_up = ""
        self.footnotes = []
        self.custom_classes = []
        self.tag = None
        self.para_tag = None
        self.page_tag = None
        self.visible = True
        self.extra_grafs = []
        self.stored_grafs = []
        self.position_key = 0
        self.__dict__.update(kwargs)

    def get_element_tag(self) -> str:
        return presentation.graf_get_element_tag(self)

    def escape_text(self) -> str:
        return presentation.graf_escape_text(self)

    def paragraph_image_url(self) -> str:
        return presentation.graf_paragraph_image_url(self)

    def nav_url(self) -> str:
        return presentation.graf_nav_url(self)

    def opacity_visible(self):
        return presentation.graf_opacity_visible(self)

    def classes(self) -> str:
        return presentation.graf_classes(self)

    def social_cite_link(self) -> str:
        return presentation.graf_social_cite_link(self)

    def start_tag_class_type(self):
        return presentation.graf_start_tag_class_type(self)

    def extended(self) -> bool:
        """
        Boolean - is this an extended paragraph>
        """
        return "E" in self.type

    def has_content(self) -> bool:
        """
        is there any content in this graf?
        """
        for x in [self] + self.extra_grafs:
            if x.html:
                return True
        return False

    def self_and_extras(self) -> Iterator["Graf"]:
        """
        return this and any child paragraphs (in extended sections)
        """
        for x in [self] + self.extra_grafs:
            if x.html or x.title:
                yield x

    def long_combo_key(self) -> str:
        """
        key for this paragrah - including letter starts
        """
        return ".".join(
            [
                str(self.parent_id),
                str(self.position_key),
                self.key,
                self.start_key,
                self.end_key,
                self.letter_key,
                self.letter_seq,
            ]
        )

    def combo_key(self) -> str:
        """
        key for this paragrah
        """
        return ".".join(
            [
                str(self.parent_id),
                str(self.position_key),
                self.key,
                self.start_key,
                self.end_key,
                self.letter_key,
            ]
        )

    def connect_to_footnote(self, text: str, registry: FootnoteRegistry) -> None:
        from stringprint2.stringprint.tools.deepink import graf_connect_to_footnote

        return graf_connect_to_footnote(self, text, registry)

    def process(
        self,
        prev_type: str = "",
        article: CompilationContext | None = None,
        section: Optional[Section] = None,
        footnotes: FootnoteRegistry | None = None,
    ) -> None:
        from stringprint2.stringprint.tools.deepink import graf_process

        return graf_process(self, prev_type, article, section, footnotes)

    def end_expand_link(self, next_block_type: str = "") -> str:
        return presentation.graf_end_expand_link(self, next_block_type)

    def is_extended_start(self) -> bool:
        return presentation.graf_is_extended_start(self)

    def is_extended_end(self) -> bool:
        return presentation.graf_is_extended_end(self)

    def display(self) -> SafeText:
        return presentation.graf_display(self)

    def display_text(self) -> SafeText:
        return presentation.graf_display_text(self)

    def display_bare(self) -> str:
        return presentation.graf_display_bare(self)

    def display_kindle(self, remove_links: bool = True) -> SafeText:
        return presentation.graf_display_kindle(self, remove_links)

    def block_start(self, prev_block: Optional[bool] = None) -> None:
        return presentation.graf_block_start(self, prev_block)

    def block_end(self, next_block: Optional[bool] = None) -> bool:
        return presentation.graf_block_end(self, next_block)

    def anchor(self) -> str:
        """
        is there a named anchor for this graf
        """

        def depuntuate(s):
            return re.sub(r"[^\w\s]", "", s)

        if hasattr(self, "anchor_title") and self.anchor_title:
            title = self.anchor_title
        else:
            title = self.title

        for s in string.whitespace:
            title = title.replace(s, " ")

        new = depuntuate(title).replace(" ", "-").strip().lower()
        new = new.replace("%C2%A0", " ")
        if self.anchor_offset:
            new += "_" + self.anchor_offset
        return new
