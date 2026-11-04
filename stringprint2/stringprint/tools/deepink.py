"""Parse authored Markdown into legacy-compatible compiled document structures.

Document classes remain re-exported here for historical imports.
"""

from __future__ import annotations


import markdown
import base64
import hashlib
import re
from bs4 import BeautifulSoup

from stringprint2.services.document_compilation import CompilationContext
import random
import string
from bs4.element import NavigableString, Tag

from typing import Any, List, Optional, Union

from stringprint2.document_structure import Footnote, FootnoteRegistry, Graf, Section


class RandomAssignment(object):
    max = 10000

    def __init__(self, seed: int = 13) -> None:
        """
        a seed of -1 will give direct numbers counting up
        """
        self.seed = seed
        self.already_given = []
        self.max = self.__class__.max
        self.random = random.Random(self.seed)
        self.simple = 0

    def get(self) -> int:
        if self.seed == -1:
            self.simple += 1
            return self.simple
        else:
            i = None
            while i == None:
                i = self.random.randint(1, self.max) + self.seed
                if i in self.already_given:
                    i = None
            self.already_given.append(i)
            return i


def graf_connect_to_footnote(paragraph, text: str, registry: FootnoteRegistry) -> None:
    for l in text.split("\n"):
        ref = re.search(r"\[\^[0-9A-Za-z*_-]+\]\:", l)
        if ref:
            ref = ref.group()[:-1]
            note = l[l.find(":") + 1 :].strip()

            for f in registry.notes:
                if f.content == "" and f.local_ref == ref:
                    f.set_content(note)


def graf_process(
    paragraph,
    prev_type: str = "",
    article: CompilationContext | None = None,
    section: Optional[Section] = None,
    footnotes: FootnoteRegistry | None = None,
) -> None:
    if footnotes is None:
        footnotes = FootnoteRegistry()

    def depuntuate(s):
        return re.sub(r"[^\w\s]", "", s)

    def make_hash(txt):
        hasher = hashlib.sha1(depuntuate(txt).encode("utf-8"))
        return base64.urlsafe_b64encode(hasher.digest())[:5].lower().decode("utf-8")

    start_letters = [x[0].lower() for x in paragraph.plain_txt.split(" ") if x]
    start_letters = "".join([x for x in start_letters if x in string.ascii_lowercase])

    paragraph.key = make_hash(paragraph.plain_txt)
    # based on first letters (allows typo fixes)
    paragraph.letter_key = make_hash(start_letters)
    paragraph.letter_seq = start_letters
    paragraph.start_key = make_hash(paragraph.plain_txt[:10])
    paragraph.end_key = make_hash(paragraph.plain_txt[-10:])

    text = paragraph.html

    """
    processes paragraph type
    """
    paragraph.type = Graf.NORMAL

    if paragraph.h_name == "blockquote":
        paragraph.blockquote = True
    if re.search(r"\[\^[0-9A-Za-z*_-]+\]:", text):
        paragraph.connect_to_footnote(text, footnotes)
        paragraph.html = ""
        paragraph.type = None
        return None
    if text[:2] == "[[" and text[-2:] == "]]":
        text = text.replace("[[", "").replace("]]", "")
        paragraph.type = Graf.EXTENDED_COMPLETE
    if (
        text[:2] != "[["
        and text[-2:] != "]]"
        and prev_type in [Graf.EXTENDED_START, Graf.EXTENDED_MIDDLE]
    ):
        paragraph.type = Graf.EXTENDED_MIDDLE
    if text[:2] != "[[" and text[-2:] == "]]":
        text = text.replace("[[", "").replace("]]", "")
        paragraph.type = Graf.EXTENDED_END
    if text[:2] == "[[" and text[-2:] != "]]":
        text = text.replace("[[", "").replace("]]", "")
        paragraph.type = Graf.EXTENDED_START

    """ extract and add spans to all double quotes"""
    text = text.replace('=""', "%EMPTYHTMLTAG%")
    for q in re.findall('""([^"]*?)""', text):
        text = text.replace('""' + q + '""', '<span class="quote">"' + q + '"</span>')
    text = text.replace("%EMPTYHTMLTAG%", '=""')

    """ extract any tags """
    for q in re.findall(r"\[tag[^)]*?]", text):
        paragraph.tag = q.replace("[tag:", "").replace("]", "")
        text = text.replace(q, "")

    """ extract any para_tags """
    for q in re.findall(r"\[para[^)]*?]", text):
        paragraph.para_tag = q.replace("[para:", "").replace("]", "")
        text = text.replace(q, "")

    """ extract any page_tags """
    for q in re.findall(r"\[page[^)]*?]", text):
        paragraph.page_tag = q.replace("[page:", "").replace("]", "")
        text = text.replace(q, "")

    """ extract and replace header-assets """
    for q in re.findall(r"\[header-asset:[^)]*]", text):
        asset = q.replace("[header-asset:", "").replace("]", "")
        asset_id = article.resolve_asset(asset) if article else None
        if asset_id is not None:
            section.header_asset = asset_id
        text = text.replace(q, "")

    """ extract and replace assets """
    for q in re.findall(r"\[asset:[^)]*]", text):
        asset = q.replace("[asset:", "").replace("]", "")
        asset_id = article.resolve_asset(asset) if article else None
        if asset_id is not None:
            paragraph.asset = asset_id
            text = text.replace(q, str(asset_id))
        else:
            text = text.replace(q, "ASSET MISSING")

    # process footnotes - can't use an iter because amending size as we go
    match = True
    while match:
        match = re.search(r"\[\^.*?\]", text)
        if match:
            q = match.group()
            new_note = Footnote(local_ref=q, registry=footnotes)
            ref_html = "<footref>{0}</footref>".format(new_note.num)
            text = text[: match.start()] + ref_html + text[match.end() :]
            paragraph.footnotes.append(new_note)

    paragraph.html = text


def quote_fix(content: str) -> str:
    if not content:
        return content
    return (
        content.replace("“", '"')
        .replace("”", '"')
        .replace("’", "'")
        .replace("’", "'")
        .replace("’", "'")
    )


def move_extended_close(content: str) -> str:
    """
    moves ]] onto next line to escape difficulties.
    """
    final = []
    for l in content.split("\n"):
        if l.strip()[-2:] == "]]":
            final.append(l.strip()[:-2])
            final.append("]]")
        else:
            final.append(l)

    return "\n".join(final)


def hide_footnote_refs(content: str) -> str:
    # hide footnotes from markdown processor
    content = content.replace("[^", "!!footnotestandin!!")
    return content


def return_footnote_refs(content: str) -> str:
    content = content.replace("!!footnotestandin!!", "[^")
    return content


def get_classes(e: Tag) -> List[Any]:
    if e.has_attr("class"):
        return e.attrs["class"]
    return []


def get_content(e: Union[NavigableString, Tag]) -> str:
    good_to_extract = [
        "p",
        "ul",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "blockquote",
        "ol",
        "table",
    ]

    if isinstance(e, NavigableString) or e.name not in good_to_extract:
        return str(e)
    if e.contents:
        return "".join([get_content(x) for x in e.contents])
    else:
        return str(e)


def parse_ink(version: CompilationContext, content: str) -> None:
    footnotes = FootnoteRegistry()

    processors = [
        quote_fix,
        move_extended_close,
        hide_footnote_refs,
        markdown.markdown,
        return_footnote_refs,
    ]

    """
    #these are set back to active later if used
    """

    processed = content
    for p in processors:
        processed = p(processed)

    good_to_extract = [
        "p",
        "ul",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "blockquote",
        "ol",
        "table",
    ]

    lines = BeautifulSoup(processed, features="html5lib").find_all(
        {x: True for x in good_to_extract}
    )

    order = 1
    s_order = 1
    version.sections = []
    s = Section(order=s_order)
    last_title = []
    last_type = ""
    section_title = ""
    catchup = ""
    inject_notes_start = False
    rand = RandomAssignment(version.seed)

    existing_anchors = []
    previous_anchors = {}

    def get_anchor_offset(v):
        if not v:
            return ""
        if v in existing_anchors:
            current = previous_anchors.get(v, 0)
            current += 1
            print(v + " already used")
            previous_anchors[v] = current
            return str(current)
        else:
            existing_anchors.append(v)
            return ""

    def extract_p_if_first(s):
        if s.name != "blockquote":
            for e in good_to_extract:
                if s.name == e:
                    return get_content(s)
        return s.__unicode__()

    header_level = 0
    current_h1_title = "start"
    for x, p in enumerate(lines):
        # doesn't give us double entries for <p> contained within these
        if p.text != "" and p.parent.name not in ["blockquote", "li"]:
            if p.name in ["h2", "h3", "h4"]:
                if section_title:
                    # if multiple headers straight after each other
                    anchor_title = current_h1_title + " " + section_title
                    print("creating anchor title:{0}".format(anchor_title))
                    ng = Graf(
                        title=section_title,
                        order=order,
                        header_level=header_level,
                        h_name=p.name,
                        parent_id=s.order,
                        anchor_title=anchor_title,
                        anchor_offset=get_anchor_offset(anchor_title),
                    )
                    order += 1
                    s.grafs.append(ng)
                section_title = p.text  # assigns title to next graf we find
                header_level = int(p.name[1])
            elif p.name == "h1":
                # stash previous section, start new one
                if s.name or s.grafs:
                    s.save_process()
                    version.sections.append(s)
                    s_order += 1
                s = Section(
                    order=s_order, name=p.text, anchor_offset=get_anchor_offset(p.text)
                )
                current_h1_title = p.text
                last_title = None
            elif "[catchup:" in p.text.lower():
                # extract catch up information and append it to last uploaded
                # graf or section if are none
                catchup = p.text.strip().replace("[catchup:", "")
                if catchup[-1] == "]":
                    catchup = catchup[:-1].strip()
                if last_title and last_title.title == section_title:
                    last_title.catch_up = catchup
                elif section_title:
                    pass
                else:
                    s.catch_up = catchup

            else:
                if p.text.strip() == "[[":
                    # lone plain paragraph start
                    inject_notes_start = True
                else:
                    if inject_notes_start:
                        plain_txt = "[[" + p.text
                        html = "[[" + extract_p_if_first(p)
                        inject_notes_start = False
                    else:
                        plain_txt = p.text
                        html = extract_p_if_first(p)
                    if section_title:
                        anchor_title = current_h1_title + " " + section_title
                    else:
                        anchor_title = ""
                    ng = Graf(
                        title=section_title,
                        plain_txt=plain_txt,
                        html=html,
                        h_name=p.name,
                        custom_classes=get_classes(p),
                        order=order,
                        header_level=header_level,
                        parent_id=s.order,
                        catch_up=catchup,
                        anchor_title=anchor_title,
                        anchor_offset=get_anchor_offset(anchor_title),
                    )

                    catchup = ""
                    if section_title:
                        last_title = ng
                    ng.process(last_type, version, s, footnotes)
                    if ng.type:
                        order += 1
                        last_type = ng.type
                        ng.position_key = rand.get()
                        s.grafs.append(ng)
                    section_title = ""
                    header_level = 0

    s.save_process()
    version.sections.append(s)  # stash final section

    """set the has notes variable to control if we enable global notes controls"""
    version.has_notes = False
    for s in version.sections:
        for g in s.grafs:
            if g.type in [Graf.EXTENDED_COMPLETE, Graf.EXTENDED_START]:
                version.has_notes = True
                break
