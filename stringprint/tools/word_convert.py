# -*- coding: utf-8 -*-

import base64
import io
import os
import re
import warnings
from collections import OrderedDict
from typing import Tuple, List, Optional, Dict
import html2markdown
import mammoth
from bs4 import BeautifulSoup
from ruamel.yaml import YAML
from useful_inkleby.files import QuickGrid, QuickText
from django.utils.text import slugify

regex = re.compile(
    r"^(?:http|ftp)s?://"  # http:// or https://
    # domain...
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"
    r"localhost|"  # localhost...
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
    r"(?::\d+)?"  # optional port
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE,
)


class UniqueSlugify:
    """
    Quick tool to make sure slugs generated are unique
    """

    def __init__(self):
        self.previous: List[str] = []

    def unique(self, identifier: str) -> str:
        """
        given general string, return a valid slug that's unique
        """
        base_slug = slugify(identifier[:20])
        self.previous.append(base_slug)
        current_count = len([x for x in self.previous if x == base_slug])
        return f"{base_slug}-{current_count}"


def fix_url(url: str) -> str:
    if regex.match(url):
        return "Link: [{0}]({0})".format(url)
    return url


def fix_footnotes(block: str) -> str:
    """
    texttomarkdown doesn't do this right, fix manually
    """
    block = block.replace("<ol>", "")
    block = block.replace("</ol>", "")
    count = 0
    final = []
    for l in block.split("</li>"):
        nl = l.replace('<li id="footnote-{0}"><p>'.format(count), "")
        nl = nl.replace('<a href="#footnote-ref-{0}">↑</a></p>'.format(count), "")
        nl = nl.strip()
        nl = html2markdown.convert(nl).replace("\n", "")
        if l:
            final.append("[^{0}]: {1}".format(count + 1, nl))
        count += 1
    return "\n".join(final)


def mammoth_adjust(qt: QuickText, demote: bool = True) -> None:
    """
    given the results of a mammoth conversion:
    fixes up footnotes
    extracts images and tables
    """
    text = qt.text

    def note_text(x):
        return '<sup><a href="#footnote-{0}" id="footnote-ref-{0}">\\[{0}\\]</a></sup>'.format(
            x
        )

    def note_text_new(x):
        return f'<sup><a href="#footnote-{x - 1}" id="footnote-ref-{x - 1}">\\[{x}\\]</a></sup>'

    count = 1

    special_characters = "[]'.,!-" + '"'

    text = text.replace("<sup><sup>", "<sup>")
    text = text.replace("</sup></sup>", "</sup>")

    text = text.replace("!!BLOCKQUOTE!!", ">")
    text = text.replace("&nbsp;", " ")

    last_line = text.split("\n")[-1]
    if "<ol>" in last_line:
        new_footnotes = fix_footnotes(last_line)
        text = text.replace(last_line, new_footnotes)

    while note_text(count) in text or note_text_new(count) in text:
        text = text.replace(note_text(count), "[^{0}]".format(count))
        text = text.replace(note_text_new(count), "[^{0}]".format(count))
        text = text.replace("<sup>[^{0}]</sup>".format(count), "[^{0}]".format(count))
        text = text.replace(
            '{0}. <a id="footnote-{0}"></a>'.format(count), "[^{0}]:".format(count)
        )
        text = text.replace(
            '[{0}]: <li id="footnote-{0}"><p>'.format(count), "[^{0}]:".format(count)
        )
        text = text.replace("[↑](#footnote-ref-{0})".format(count), "!!!FOOTNOTE!!!\n")
        text = text.replace(
            '<a href="#footnote-ref-{0}">↑</a></p></li>'.format(count),
            "!!!FOOTNOTE!!!\n",
        )
        count += 1

    # remove weird TOC links
    for r in re.findall('<a id="_Toc[\d]*"></a>', text):
        text = text.replace(r, "")
    for r in re.findall('<a id="_[\d\w]*"></a>', text):
        text = text.replace(r, "")

    # get correct markdown out of action
    for r in re.findall("\*\*(.*?)\*\*", text):
        if r and r[0] != " " and r[-1] != " ":
            text = text.replace(
                "**{0}**".format(r), "!!DOUBLE!!{0}!!DOUBLE!!".format(r)
            )
    for r in re.findall("\*(.*?)\*", text):
        if r and r[0] != " " and r[-1] != " ":
            text = text.replace("*{0}*".format(r), "!!SINGLE!!{0}!!SINGLE!!".format(r))

    # remove bad markdown conversion - removes spaces at end of formatting

    patterns = [
        ("(\*\*(.*?) \*\*)", "**{0}** "),
        ("(\*\* (.*?)\*\*)", " **{0}**"),
        ("(\*(.*?) \*)", "*{0}* "),
        ("(\* (.*?)\*)", " *{0}*"),
        ("(\_\_(._?) \_\_)", "__{0}__ "),
        ("(\_\_ (._?)\_\_)", " __{0}__"),
        ("(\_(._?) \_)", "_{0}_ "),
        ("(\_ (._?)\_)", " _{0}_"),
    ]
    count = 0
    for p, replace in patterns:
        for r in re.findall(p, text):
            full, contents = r
            if "*" in contents:
                continue
            replacement = replace.format(contents)
            text = text.replace(full, replacement)

    text = text.replace("!!DOUBLE!!", "**")
    text = text.replace("!!SINGLE!!", "*")

    # move any bold away from neighbouring text
    patterns = [("(\*\*(.+?)\*\*)\w", "**{0}** "), ("\w(\*\*(.+?)\*\*)", " **{0}**")]
    for p, replace_format in patterns:
        for full, contents in re.findall(p, text):
            if "*" not in r and len(r) < 15:
                replace = replace_format.format(contents)
                text = text.replace(full, replace)

    for s in special_characters:
        text = text.replace("\\" + s, s)

    text = text.replace("\n\r", "\n")

    # another fix to catch instances where things have been grouped wrong

    options = ["(\_{2})(.*)(\_{2})", "(\_{1})(.*)(\_{1})"]
    for o in options:
        for r in re.finditer(o, text):
            open_underline, contained, close_underline = r.groups()
            if contained.endswith(" "):
                new_line = open_underline + contained.strip() + close_underline + " "
                text = text.replace(r[0], new_line)

    qt.text = text

    normal_image_find = re.compile(
        r"\!\[(.*?)\]\(data:image/(.*?);base64,(.*?)\)", flags=re.DOTALL
    )
    alt_image_find = re.compile(
        r'<img src="data:image/(.*?);base64,(.*)\)(.*)"/>', flags=re.DOTALL
    )
    toc_find = re.compile(r"\[.*[0-9]\]\(#_Toc.*\)")

    ignore_before_h1 = True

    asset_count = 0
    qt.assets = []
    footnote_count = 0
    prev = None

    extra_map = {}

    slug_getter = UniqueSlugify()
    replace_list = []
    asset_count += 1
    for i in [normal_image_find, alt_image_find]:
        for search in i.finditer(qt.text):
            results = search.groups()
            alt_text = ""
            caption = ""
            if i is alt_image_find:
                image_type, content, caption = results
            if i is normal_image_find:
                alt_text, image_type, content = results

            if alt_text:
                slug = slug_getter.unique(alt_text)
            else:
                slug = "doc-asset-{0}".format(asset_count)
            di = {
                "content_type": "image",
                "type": image_type,
                "content": content,
                "caption": caption,
                "alt_text": alt_text,
                "slug": slug,
            }
            print("asset found {0}".format(asset_count))
            qt.assets.append(di)
            new_asset = "[asset:{0}]".format(slug)
            replace_list.append((search[0], new_asset))
            asset_count += 1

    for old, new in replace_list:
        qt.text = qt.text.replace(old, new)

    for line in qt:
        new_asset = None
        l_line = line.lower().strip()
        if line and line.strip() == "":
            line.update(None)
        if list(set(l_line)) == ["#"]:
            line.update(None)
        if l_line and l_line[0] == "#":
            line.update(fix_header(line))
            ignore_before_h1 = False
        toc = toc_find.search(line)
        if l_line and l_line[0] == "_" and l_line[-1] == "_" and len(l_line) > 50:
            # assume this is a blockquote paragraph
            if "asset:" not in prev:
                line.update(">" + line)
        if l_line and l_line[0] == "_" and l_line[-1] == "]":
            # assume this is a blockquote paragraph ending in a quote
            if "_[^" in l_line[-7:]:
                if "asset:" not in prev:
                    line.update(">" + line)
        if toc:
            line.update(None)
        if l_line in ["table of contents", "contents"]:
            line.update(None)
        if line and line[0] == "[" and "(#_" in line:
            # assume this is google docs TOC and remove
            line.update(None)
        if "!!!footnote!!!" in l_line:
            footnote_count += 1
            new_line = line.replace("!!!FOOTNOTE!!!", "")
            new_line = remove_supports(new_line)
            new_line = fix_url(new_line)
            line.update(new_line)
        if line and line[0] == "-" and prev and prev.strip()[0] != "-":
            line.update("\n" + line)
        if line and line[0] == "#" and demote:
            line.update("#" + line)
        if len(line) > 2 and line[-2:] == " _":
            # fixing where italics haven't been ended right
            nl = line[:-2] + "_"
            line.update(nl)
        if ignore_before_h1:
            # blank all lines before first h1
            line.update(None)
        if line:
            prev = line
        if new_asset:
            prev = new_asset

    while "\n\n\n" in qt.text:
        qt.text = qt.text.replace("\n\n\n", "\n\n")

    qt.text = qt.text.replace("\n", "\r\n")
    for k, v in extra_map.items():
        qt.text = qt.text.replace(k, v)

    qt.text = qt.text.replace(">[asset:", "[asset:")
    qt.text = qt.text.replace(">_Table", "_Table")
    qt.text = qt.text.replace("</sup>", "")
    qt.text = qt.text.replace("<sup>", "")
    qt.text = qt.text.replace("<sup", "")


def fix_header(line: str) -> str:
    level = "".join([x for x in line if x == "#"])
    text = line.replace("#", "").strip()
    if len(text) == 0:
        return ""
    if text and text == text.upper():
        text = text[0] + text[1:].lower()
    return "{0} {1}".format(level, text)


def remove_supports(t):
    return t
    for x in range(0, 100):
        t = t.replace("footnote-{0}".format(x), "")
    t = t.replace('<li id=""><p>', "")
    t = t.replace("</p></li>", "")
    return t


def markdown_table_contents(x, multi_line=False):
    """
    extracts table row contents and converts to markdown
    """
    contents = x.contents
    html = ""
    if contents:
        for c in contents:
            nhtml = html2markdown.convert(str(c))
            nhtml = nhtml.replace("&nbsp;", " ")
            nhtml = nhtml.replace("&amp;", " ")
            nhtml = nhtml.strip()
            if multi_line is False:
                return nhtml
            else:
                html += nhtml + "\n\n"
        return html
    else:
        return ""


def get_tables(html: str) -> Tuple[str, List[Dict]]:
    new_html = html

    # treat header as row
    new_html = new_html.replace("<th>", "<td>")
    new_html = new_html.replace("</th>", "</td>")
    new_html = new_html.replace("<thead>", "")
    new_html = new_html.replace("</thead>", "")
    new_html = new_html.replace("<tbody>", "")
    new_html = new_html.replace("</tbody>", "")
    soup = BeautifulSoup(new_html, features="html5lib")
    tables = soup.findAll("table")
    slug_format = "table-asset-{0}"
    table_count = 0
    asset_format = "<p>[asset:{0}]</p>"
    assets = []
    for table in tables:

        table_count += 1
        print(f"getting table {table_count}")
        slug = slug_format.format(table_count)
        table_data = []
        markdown_header = []
        for n, row in enumerate(table.find_all("tr")):
            if n == 0:  # header:
                table_data.append([td.get_text() for td in row.find_all("td")])
                markdown_header.append(
                    [
                        markdown_table_contents(td, multi_line=True)
                        for td in row.find_all("td")
                    ]
                )
            else:
                table_data.append(
                    [markdown_table_contents(td) for td in row.find_all("td")]
                )
        qg = QuickGrid()
        qg.header = table_data[0]
        qg.data = table_data[1:]
        di = {
            "content_type": "table",
            "type": "xls",
            "content": qg,
            "caption": "",
            "slug": slug,
        }
        if len(qg.data) == 0:
            if len(qg.header) == 1:
                replacement = "[[\n" + "\n".join(markdown_header[0]) + "\n]]"
                replacement = replacement.replace("\\[", "[")
                replacement = replacement.replace("\\]", "]")
                table_html = str(table).replace("<tbody>", "").replace("</tbody>", "")
                new_html = new_html.replace(table_html, replacement)
            if len(qg.header) == 2:
                replacement = "!!BLOCKQUOTE!! **{0}**: {1}".format(*qg.header)
                table_html = str(table).replace("<tbody>", "").replace("</tbody>", "")
                new_html = new_html.replace(table_html, replacement)
        else:
            assets.append(di)
            table_html = str(table).replace("<tbody>", "").replace("</tbody>", "")
            new_html = new_html.replace(table_html, asset_format.format(slug))
            # if asset_format.format(slug) not in new_html:
            #    raise ValueError("Table slug not successfully inserted.")
    return new_html, assets


def get_asset_captions(qt: QuickText) -> None:
    """
    if there's an italic line beneath an asset, uses it as a
    """
    lookup = {}
    for x, a in enumerate(qt.assets):
        lookup[a["slug"]] = x

    last_asset = None
    for l in qt.lines():
        if last_asset and l.strip() and l.strip()[0] == "*":
            caption = l.strip()
            if caption[0] == "*":
                caption = caption[1:]
            if caption[-1] == "*":
                caption = caption[:-1]
            qt.assets[lookup[last_asset]]["caption"] = caption
            l.update(None)
        if l.strip():
            if "[asset" in l:
                last_asset = l.strip().replace("[asset:", "")[:-1]
            else:
                last_asset = None


def convert_docx(file_path, demote=False) -> QuickText:
    """
    given a word file as a file object, converts to markdown
    and then does post processing for stringprint specific features
    """
    with open(file_path, "rb") as docx_file:
        m_conversion = mammoth.convert_to_html(docx_file)

    html = m_conversion.value
    html, assets = get_tables(html)

    markdown = html2markdown.convert(html)
    q = QuickText()
    q.filename = file_path
    q.text = markdown
    q.assets = []
    mammoth_adjust(q, demote)
    q.assets.extend(assets)
    get_asset_captions(q)

    for m in m_conversion.messages:
        print(m)

    return q


def extract_assets(q: QuickText) -> None:

    folder = os.path.dirname(q.filename)
    asset_folder = os.path.join(folder, "assets")
    if not os.path.exists(asset_folder):
        os.makedirs(asset_folder)

    for a in q.assets:
        if a["content_type"] == "table":
            print("table", a["slug"])
            a["content"].save([asset_folder, a["slug"] + ".xls"])
        if a["content_type"] == "image":
            print("image", a["slug"])
            image_output = io.BytesIO()
            # Write decoded image to buffer
            base64_content = base64.b64decode(a["content"].encode("utf-8") + b"===")
            image_output.write(base64_content)
            image_output.seek(0)  # seek beginning of the image string
            file_path = os.path.join(asset_folder, a["slug"] + "." + a["type"])
            with open(file_path, "wb") as image_file:
                image_file.write(image_output.read())

    props = ["content_type", "type", "caption", "alt_text"]
    yaml_output = []
    for a in q.assets:
        item = {}
        for p in props:
            item[p] = a.get(p, "")
        yaml_output.append({a["slug"]: item})

    yaml_file = os.path.join(asset_folder, "assets.yaml")
    yaml = YAML()
    yaml.default_flow_style = False

    with open(yaml_file, "wb") as f:
        yaml.dump(yaml_output, f)


def convert_word(source, dest, demote=False):
    q = convert_docx(source, demote)
    extract_assets(q)
    q.save(dest)
    print("done")
