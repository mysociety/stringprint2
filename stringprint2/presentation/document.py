"""HTML, links, and template preparation for compiled document objects.

The legacy document methods delegate here to preserve template and file APIs.
"""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterator, Optional, TYPE_CHECKING
from bs4 import BeautifulSoup
from django.utils.html import mark_safe
from django.utils.safestring import SafeText

if TYPE_CHECKING:
    from stringprint2.document_structure import Graf

tag_re_statement = re.compile('"#tag.(.*?)"')
internal_links_re_statement = re.compile('"#(.*?)"')


@dataclass
class DocumentPresentation:
    """Own a detached tree so rendering never annotates compiled source objects."""

    sections: list[Any]

    @classmethod
    def for_version(cls, version, slugs=(), *, display_first_section=False):
        sections = deepcopy(version.sections, {id(version): version})
        for section in sections:
            section._version = version
            section.active_section = (
                section.order == 1
                if display_first_section
                else not slugs or section.anchor() in slugs
            )
        return cls(sections)


def graf_get_element_tag(paragraph) -> str:
    if paragraph.asset and paragraph.h_name == "p":
        return "div"
    else:
        return paragraph.h_name


def graf_escape_text(paragraph) -> str:
    txt = paragraph.plain_txt.encode("ascii", "ignore")
    txt = txt.replace(b"[", b"").replace(b"]", b"").replace(b"\n", b"")
    return txt.decode("utf-8")


def graf_paragraph_image_url(paragraph) -> str:
    return "/media/paragraphs/{0}.png".format(paragraph.combo_key())


def graf_nav_url(paragraph) -> str:
    """
    nav url to this graf
    """
    anchor = paragraph.anchor()
    if anchor == "":
        anchor = paragraph.combo_key()

    if paragraph._section._version.article.multipage:
        return paragraph._section.nav_url(include_anchor=False) + "#" + anchor
    else:
        if paragraph._section._version.article.search:
            if paragraph._section._version.article.baking:
                return "index.html#" + anchor
            else:
                return paragraph._section._version.article.url() + "#" + anchor
        else:
            return "#" + anchor


def graf_opacity_visible(paragraph):
    """
    Called by template.
    if visiblity has an opacity class - inject it
    """
    if paragraph.visible != True:
        if "opacity" in paragraph.visible:
            return paragraph.visible
    return ""


def graf_classes(paragraph) -> str:
    """
    Called by template.
    classes to inject into row object
    """
    if paragraph.start_tag == "StartNotes":
        return "extended-row"
    else:
        return ""


def graf_social_cite_link(paragraph) -> str:
    return paragraph._article.social_cite_link(paragraph)


def graf_start_tag_class_type(paragraph):
    if paragraph.start_tag == "StartBlockQuote":
        return "blockquote"
    elif paragraph.start_tag == "StartNotes":
        return "extended"
    return ""


def graf_end_expand_link(paragraph, next_block_type: str = "") -> str:
    if next:
        if next_block_type in [paragraph.EXTENDED_START, paragraph.EXTENDED_COMPLETE]:
            link_type = "expand"
        elif paragraph.type in [paragraph.EXTENDED_END, paragraph.EXTENDED_COMPLETE]:
            link_type = "hide"
        else:
            link_type = ""
    return link_type


def graf_is_extended_start(paragraph) -> bool:
    return paragraph.type in [paragraph.EXTENDED_START, paragraph.EXTENDED_COMPLETE]


def graf_is_extended_end(paragraph) -> bool:
    return paragraph.type in [paragraph.EXTENDED_END, paragraph.EXTENDED_COMPLETE]


def graf_display(paragraph) -> SafeText:
    """
    render for display
    """
    text = paragraph.html
    refs = BeautifulSoup(text, "html.parser").find_all({"footref": True})

    footnotes = paragraph.footnotes
    footnote_lookup = {x.num: x for x in footnotes}

    for l in refs:
        ref_no = int(l.text)
        footnote = footnote_lookup[ref_no]
        new_ref = footnote.format(paragraph.order)
        text = text.replace(str(l), new_ref)

    """
    swap out tag references so they can cross pages for multi-part articles
    """
    version = paragraph._section._version
    if version.article.multipage:
        tags = tag_re_statement.findall(text)
        if tags:
            tag_lookup = version.tag_lookup()
            for tag in tags:
                try:
                    order = tag_lookup[tag]
                except KeyError:
                    order = None
                print(order)
                if order:
                    url = version.sections[order - 1].nav_url(include_anchor=False)
                    url += "#tag." + tag
                    text = text.replace("#tag.{0}".format(tag), url)
        internal_links = internal_links_re_statement.findall(text)
        if internal_links:
            sections = version.section_link_lookup()
            for link in internal_links:
                if link in sections:
                    s = sections[link]
                    url = s.nav_url(include_anchor=False)
                    url += "#" + link
                    text = text.replace("#" + link, url)

    return mark_safe(text)


def graf_display_text(paragraph) -> SafeText:
    return paragraph.display_kindle(remove_links=False)


def graf_display_bare(paragraph) -> str:
    text = paragraph.html
    text = BeautifulSoup(text, features="html5lib").text
    if len(text) > 420:
        text = text[:417] + "..."
    return text


def graf_display_kindle(paragraph, remove_links: bool = True) -> SafeText:
    text = paragraph.html
    links = BeautifulSoup(text, features="html5lib").find_all({"a": True})

    if remove_links:
        for l in links:
            if "href" in l and "#tag." not in l["href"]:
                text = text.replace(str(l), l.text)

    refs = BeautifulSoup(text, features="html5lib").find_all({"footref": True})

    footnotes = paragraph.footnotes
    footnote_lookup = {x.num: x for x in footnotes}

    text = text.replace("&", "&amp;")

    for l in refs:
        ref_no = int(l.text)
        footnote = footnote_lookup[ref_no]
        new_ref = footnote.format_kindle()
        text = text.replace(str(l), new_ref)

    return mark_safe(text)


def graf_block_start(paragraph, prev_block: Optional[bool] = None) -> None:
    """
    special start to block if start of note or blockquote section

    """

    if paragraph.blockquote and prev_block is False:
        return "StartBlockQuote"
    if (
        paragraph.type == paragraph.EXTENDED_START
        or paragraph.type == paragraph.EXTENDED_COMPLETE
    ):
        return "StartNotes"


def graf_block_end(paragraph, next_block: Optional[bool] = None) -> bool:
    if paragraph.blockquote and next_block is False:
        return True
    elif (
        paragraph.type == paragraph.EXTENDED_END
        or paragraph.type == paragraph.EXTENDED_COMPLETE
    ):
        return True
    else:
        return False


def section_get_header_asset(section):
    if section.header_asset:
        return section._article.assets.get(id=section.header_asset)


def section_next_section(section):
    """
    returns the next section in the order
    """
    for x in section._version.sections:
        if x.order == section.order + 1:
            return x
    return None


def section_prev_section(section):
    """
    returns the previous section in the order
    """
    for x in section._version.sections:
        if x.order == section.order - 1:
            return x
    return None


def section_anchorless_nav_link(section):
    return section.nav_url(False)


def section_nav_url(section, include_anchor: bool = True) -> str:
    """
    link to this section (either as anchor or link to new page).
    """
    article = section._version.article
    anchor = section.anchor()
    if hasattr(article, "baking") and article.baking:
        """
        disregard url structure when dealing with baking
        """
        if article.multipage:
            if section.order == 1:
                # if first page in a multipage article
                if include_anchor:
                    return "./#" + section.anchor()
                else:
                    return "./"
            else:
                if include_anchor:
                    return anchor + ".html" + "#" + anchor
                else:
                    return anchor + ".html"
        else:
            if article.search:
                return "index.html#" + anchor
            else:
                return "#" + anchor
    else:
        if article.multipage:
            if section.order == 1:
                anchor = ""
            if include_anchor:
                return article.url(anchor) + "#" + anchor
            else:
                return article.url(anchor)
        else:
            if article.search:
                return article.url() + "#" + anchor
            else:
                return "#" + anchor


def section_prev_if_single_page(section) -> int:
    """
    returns own order in multi-page system
    """
    if section._version.article.multipage:
        return section.order
    else:
        return section.prev_id()


def section_reduced_name(section):
    """
    reduced name for space limited display
    """
    if len(section.name) > 25:
        return section.name[:25] + "[...]"
    else:
        return section.name


def section_search_grafs(section) -> Iterator["Graf"]:
    assets = section._version.article.assets.all()
    assets = {x.id: x for x in assets}

    last_title = section.name
    for g in section.get_grafs():
        if g.title:
            last_title = g.title
        g.current_title = last_title
        if g.asset:
            g.asset = assets[g.asset]
        if g.visible:
            yield g


def section_get_grafs_with_titles(section) -> Iterator[Any]:
    return section.get_grafs(just_titles=True)


def section_get_kindle_grafs(section) -> Iterator["Graf"]:
    from stringprint2.document_structure import Graf

    section.kindle_extras = []
    if section._article.display_notes:
        for g in section.get_grafs(change_footnotes=False):
            all = [x for x in g.self_and_extras()]
            if len(all) > 1:
                all[-1].type = Graf.EXTENDED_END
            for a in all:
                yield a
    else:
        for g in section.get_grafs(change_footnotes=False):
            if g.type in [Graf.EXTENDED_START, Graf.EXTENDED_COMPLETE]:
                section.kindle_extras.append(g)
            else:
                yield g


def section_get_kindle_extras(section) -> None:
    for g in section.kindle_extras:
        yield g


def section_get_grafs(
    section, just_titles: bool = False, change_footnotes: bool = True
) -> Iterator["Graf"]:
    from stringprint2.document_structure import Graf

    if hasattr(section, "stored_grafs"):
        if section._version.article.multipage and change_footnotes is False:
            for t in section.stored_grafs:
                for f in t.footnotes:
                    f.section_num = f.num
        for g in section.stored_grafs:
            yield g
        return
    else:
        section.stored_grafs = []

    """
    does some proprocessing to get ready for template
    """
    if just_titles:
        temp_grafs = section.grafs_with_titles()
    else:
        temp_grafs = section.grafs

    if section._version.article.multipage and change_footnotes:
        count = 1
        for t in temp_grafs:
            for f in t.footnotes:
                f.section_num = count
                count += 1

    last_title = None
    prev_block_is_block = False
    expanded_block = None
    has_titles = False
    for p in temp_grafs:
        if p.title:
            has_titles = True
        break
    for x, p in enumerate(temp_grafs):
        p.is_first_title = False
        p.is_last_graf = False
        p.section_has_titles = has_titles
        if x == len(temp_grafs) - 1:
            p.is_last_graf = True

        if x + 1 < len(temp_grafs) - 1:
            n = temp_grafs[x + 1]
            next_block_type = n.type
            next_block_is_block = n.blockquote
            next_id = n.order
        else:
            n = None
            next_block_type = ""
            next_block_is_block = False
            next_id = ""
        p._section = section
        p.start_tag = p.block_start(prev_block=prev_block_is_block)
        p.end_tag = p.block_end(next_block=next_block_is_block)
        p.expand_link = [
            p.end_expand_link(next_block_type=next_block_type),
            next_id,
        ]
        if p.title:
            if last_title is None:
                p.is_first_title = True
            last_title = p
            p.last_title_order = section.order
        elif last_title is None:
            p.last_title_order = 0
        else:
            p.last_title_order = last_title.order
        prev_block_is_block = p.blockquote

        # combine all expanded grafs into one super block
        if p.type == Graf.EXTENDED_START:
            expanded_block = p
        elif p.type == Graf.EXTENDED_MIDDLE:
            expanded_block.extra_grafs.append(p)
        elif p.type == Graf.EXTENDED_END:
            if not expanded_block:
                raise ValueError("paragraph end without start: {0}".format(p.plain_txt))
            expanded_block.extra_grafs.append(p)
            expanded_block.end_tag = p.end_tag
            section.stored_grafs.append(expanded_block)
            if expanded_block.visible:
                yield expanded_block
            expanded_block = None
        else:
            section.stored_grafs.append(p)
            if p.visible or p.title:
                yield p


def footnote_safe_content(note):
    return mark_safe(note.content)


def footnote_format(note, order):
    ref_format = '<sup><a name="ref{2}" href="#" \
            class = "expand-footnotes" id="{1}">{0}</a></sup>'
    named_format = '<a name="ref{2}" href="#" \
            class = "expand-footnotes" id="{1}">{0}</a>'

    if note.named_reference:
        return named_format.format(note.named_reference, order, note.num)
    else:
        return ref_format.format(note.section_num, order, note.num)


def footnote_format_kindle(note):
    ref_format = '<a epub:type="noteref" href="#footnote-{0}" \
                    id="footnote-{0}-ref"><sup>{0}</sup></a>'
    named_format = '<a epub:type="noteref" href="#footnote-{0}" \
                    id="footnote-{0}-ref">{1}</a>'
    if note.named_reference:
        return named_format.format(note.section_num, note.named_reference)
    else:
        return ref_format.format(note.section_num)


def footnote_kindle_content(note):
    text = note.content
    links = BeautifulSoup(text, features="html5lib").find_all({"a": True})
    text = text.replace("&", "&amp;")
    if len(links) > 1:
        for l in links:
            new_text = "{0} ({1})"
            text = text.replace(str(l), new_text)
    elif len(links) > 0:
        l = links[0]
        href = l["href"]
        text = text.replace(str(l), l.text) + ' link: <a href="{0}">{0}</a>'.format(
            href
        )

    return mark_safe(text)
