# -*- coding: utf-8 -*-

import mammoth
import re
import os
import io
import tomd

from collections import OrderedDict
from ruamel.yaml import YAML


from bs4 import BeautifulSoup
from useful_inkleby.files import QuickText, QuickGrid
import base64

regex = re.compile(
    r'^(?:http|ftp)s?://'  # http:// or https://
    # domain...
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
    r'localhost|'  # localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)


def fix_url(url):
    if regex.match(url):
        return "Link: [{0}]({0})".format(url)
    return url


def mammoth_adjust(qt, demote=True):
    """
    given the results of a mammoth conversion:
    fixes up footnotes
    extracts images and tables
    """
    text = qt.text

    def note_text(x):
        return '<sup>[[{0}]](#footnote-{0})</sup>'.format(x)

    def note_text_new(x):
        return '<sup>[[{0}]](#footnote-{1})</sup>'.format(x, x - 1)
    count = 1

    special_characters = "[]'.,!-" + '"'

    text = text.replace("<sup><sup>", "<sup>")
    text = text.replace("</sup></sup>", "</sup>")

    while note_text(count) in text or note_text_new(count) in text:
        text = text.replace(note_text(count),
                            "[^{0}]".format(count))
        text = text.replace(note_text_new(count),
                            "[^{0}]".format(count))
        text = text.replace("<sup>[^{0}]</sup>".format(count),
                            "[^{0}]".format(count))
        text = text.replace('{0}. <a id="footnote-{0}"></a>'.format(count),
                            "[^{0}]:".format(count))
        text = text.replace("[↑](#footnote-ref-{0})".format(count),
                            "!!!FOOTNOTE!!!\n")
        count += 1

    # remove weird TOC links
    for r in re.findall('<a id="_Toc[\d]*"></a>', text):
        text = text.replace(r, "")
    for r in re.findall('<a id="_[\d\w]*"></a>', text):
        text = text.replace(r, "")

    # get correct markdown out of action
    for r in re.findall('\*\*(.*?)\*\*', text):
        if r and r[0] != " " and r[-1] != " ":
            text = text.replace("**{0}**".format(r),
                                "!!DOUBLE!!{0}!!DOUBLE!!".format(r))
    for r in re.findall('\*(.*?)\*', text):
        if r and r[0] != " " and r[-1] != " ":
            text = text.replace("*{0}*".format(r),
                                "!!SINGLE!!{0}!!SINGLE!!".format(r))

    # remove bad markdown conversion - removes spaces at end of formatting
    #text = text.replace("****","**")
    patterns = [("(\*\*(.*?) \*\*)", "**{0}** "),
                ("(\*\* (.*?)\*\*)", " **{0}**"),
                ("(\*(.*?) \*)", "*{0}* "),
                ("(\* (.*?)\*)", " *{0}*")]

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

    print ("hold aways")
    # move any bold away from neighbouring text
    patterns = [("(\*\*(.+?)\*\*)\w", "**{0}** "),
                ("\w(\*\*(.+?)\*\*)", " **{0}**")]
    for p, replace_format in patterns:
        for full, contents in re.findall(p, text):
            if "*" not in r and len(r) < 15:
                replace = replace_format.format(contents)
                print (full)
                print (replace)
                text = text.replace(full, replace)

    for s in special_characters:
        text = text.replace("\\" + s, s)

    text = text.replace("\n\r", "\n")

    qt.text = text

    image_find = re.compile(r"\(data:image/(.*?);base64,(.*)\)(.*)")
    toc_find = re.compile(r"\[.*[0-9]\]\(#_Toc.*\)")

    asset_count = 0
    qt.assets = []
    footnote_count = 0
    prev = None
    for line in qt:
        l_line = line.lower().strip()
        if list(set(l_line)) == ["#"]:
            line.update(None)
        if "(data:" in line:
            asset_count += 1
            search = image_find.search(line)
            image_type, content, caption = search.groups()
            slug = "word-asset-{0}".format(asset_count)
            di = {"content_type": "image",
                  "type": image_type,
                  "content": content,
                  "caption": caption,
                  "slug": slug}
            print ("asset found")
            print (di)
            qt.assets.append(di)
            line.update("[asset:{0}]".format(slug))
        toc = toc_find.search(line)
        if toc:
            line.update(None)
        if l_line in ["table of contents", "contents"]:
            line.update(None)
        if "!!!footnote!!!" in l_line:
            footnote_count += 1
            new_line = line.replace("!!!FOOTNOTE!!!", "")
            new_line = new_line[2:].strip()
            new_line = fix_url(new_line)
            new_line = "[^{0}]:".format(footnote_count) + new_line
            line.update(new_line)
        if line and line[0] == "-" and prev and prev.strip()[0] != "-":
            line.update("\n" + line)
        if line and line[0] == "#" and demote:
            line.update("#" + line)
        prev = line

    qt.text = qt.text.replace("\n", "\r\n")


def get_tables(html):
    new_html = html
    soup = BeautifulSoup(html, features="html5lib")
    tables = soup.findAll("table")
    slug_format = "table-asset-{0}"
    table_count = 0
    asset_format = "<p>[asset:{0}]</p>"
    assets = []
    for table in tables:
        table_count += 1
        slug = slug_format.format(table_count)
        table_data = []
        for row in table.find_all("tr"):
            table_data.append([td.get_text() for td in row.find_all("td")])
        qg = QuickGrid()
        qg.header = table_data[0]
        qg.data = table_data[1:]
        di = {"content_type": "table",
              "type": "xls",
              "content": qg,
              "caption": "",
              "slug": slug}
        assets.append(di)
        table_html = str(table).replace("<tbody>", "").replace("</tbody>", "")
        new_html = new_html.replace(table_html, asset_format.format(slug))
    return new_html, assets


def get_asset_captions(qt):
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


def convert_docx(file_path, demote=False):
    """
    given a word file as a file object, converts to markdown
    and then does post processing for stringprint specific features
    """
    with open(file_path, "rb") as docx_file:
        m_conversion = mammoth.convert_to_html(docx_file)
    html = m_conversion.value
    html, assets = get_tables(html)

    markdown = tomd.convert(html)
    q = QuickText()
    q.filename = file_path
    q.text = markdown
    mammoth_adjust(q, demote)
    q.assets.extend(assets)
    get_asset_captions(q)

    for m in m_conversion.messages:
        print(m)

    return q


def extract_assets(q):

    folder = os.path.dirname(q.filename)
    asset_folder = os.path.join(folder, "assets")
    if not os.path.exists(asset_folder):
        os.makedirs(asset_folder)

    for a in q.assets:
        if a["content_type"] == "table":
            print ("table")
            print (a["slug"])
            a["content"].save([asset_folder, a["slug"] + ".xls"])
        if a["content_type"] == "image":
            print (a["slug"])
            image_output = io.BytesIO()
            # Write decoded image to buffer
            base64_content = base64.b64decode(a["content"].encode("utf-8"))
            image_output.write(base64_content)
            image_output.seek(0)  # seek beginning of the image string
            file_path = os.path.join(asset_folder, a["slug"] + "." + a["type"])
            with open(file_path, "wb") as image_file:
                image_file.write(image_output.read())

    props = ["content_type", "type", "caption"]
    yaml_output = []
    for a in q.assets:
        item = {}
        for p in props:
            item[p] = a[p]
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
    print ("done")


if __name__ == "__main__":
    pass
