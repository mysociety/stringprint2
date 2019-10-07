# -*- coding: utf-8 -*-
'''
Deep Ink Processor
classes and object
'''
import markdown
import math
import base64
import hashlib
import re
from bs4 import BeautifulSoup
from useful_inkleby.useful_django.serialisers import SerialObject
from django.utils.html import mark_safe, escape
import random
import string


tag_re_statement = re.compile('"#tag.(.*?)"')


class RandomAssignment(object):

    max = 10000

    def __init__(self, seed=13):
        """
        a seed of -1 will give direct numbers counting up
        """
        self.seed = seed
        self.already_given = []
        self.max = self.__class__.max
        random.seed(self.seed)
        self.simple = 0

    def get(self):
        if self.seed == -1:
            self.simple += 1
            return self.simple
        else:
            i = None
            while i == None:
                i = random.randint(1, self.max) + self.seed
                if i in self.already_given:
                    i = None
            self.already_given.append(i)
            return i


class Footnote(SerialObject):

    note_count = 0  # keep track of how many notes we've made
    all = []

    def __init__(self, content="", local_ref=""):
        self.num = self.__class__.note_count + 1
        self.local_ref = local_ref
        self.__class__.note_count += 1
        self.__class__.all.append(self)
        self.named_reference = None
        self.content = ""
        self.set_content(content)

    def set_content(self, content):
        if "||" in content:
            self.named_reference, self.content = content.split("||")
        else:
            self.content = content
            self.named_reference = None

    def safe_content(self):
        return mark_safe(self.content)

    def format(self, order):
        ref_format = '<sup><a name="ref{0}" href="#" \
                class = "expand-footnotes" id="{1}">{0}</a></sup>'
        named_format = '<a name="ref{2}" href="#" \
                class = "expand-footnotes" id="{1}">{0}</a>'

        if self.named_reference:
            return named_format.format(self.named_reference,
                                       order,
                                       self.num)
        else:
            return ref_format.format(self.num, order)

    def format_kindle(self):
        ref_format = '<a epub:type="noteref" href="#footnote-{0}" \
                        id="footnote-{0}-ref"><sup>{0}</sup></a>'
        named_format = '<a epub:type="noteref" href="#footnote-{0}" \
                        id="footnote-{0}-ref">{1}</a>'
        if self.named_reference:
            return named_format.format(self.num,
                                       self.named_reference)
        else:
            return ref_format.format(self.num)

    def kindle_content(self):
        text = self.content
        links = BeautifulSoup(text, features="html5lib").findAll({'a': True})

        if len(links) > 1:
            for l in links:
                new_text = "{0} ({1})"
                text = text.replace(str(l), new_text)
        elif len(links) > 0:
            l = links[0]
            href = l['href']
            text = text.replace(str(l), l.text) + \
                ' link: <a href="{0}">{0}</a>'.format(href)

        return mark_safe(text)


class Section(SerialObject):

    def __init__(self, *args, **kwargs):
        self.id = 0
        self.name = ""
        self.order = 0
        self.catch_up = ""
        self.grafs = []
        self.anchor_offset = ""
        self.visible = True
        self.nav = []
        self.__dict__.update(kwargs)
        self._version = None  # set during display

    def first_graf_id(self):
        if self.grafs:
            return self.grafs[0].order

    def save_process(self):
        """
        execute at the end of loading before being stashed in database
        """
        self.tagged = {x.tag: self.order for x in self.grafs if x.tag}

    def used_assets(self):
        """
        which assets are in this section
        """
        return [g.asset for g in self.grafs if g.asset]

    def next_section(self):
        """
        returns the next section in the order
        """
        for x in self._version.sections:
            if x.order == self.order + 1:
                return x
        return None

    def prev_section(self):
        """
        returns the previous section in the order
        """
        for x in self._version.sections:
            if x.order == self.order - 1:
                return x
        return None

    def anchorless_nav_link(self):
        return self.nav_url(False)

    def nav_url(self, include_anchor=True):
        """
        link to this section (either as anchor or link to new page).
        """
        article = self._version.article
        if hasattr(article, "baking") and article.baking:
            """
            disregard url structure when dealing with baking
            """
            if article.sections_over_pages:
                if include_anchor:
                    return self.anchor() + ".html" + "#" + self.anchor()
                else:
                    return self.anchor() + ".html"
            else:
                if article.search:
                    return "index.html#" + self.anchor()
                else:
                    return "#" + self.anchor()
        else:
            if article.sections_over_pages:
                if include_anchor:
                    return article.url(self.anchor()) + "#" + self.anchor()
                else:
                    return article.url(self.anchor())
            else:
                if article.search:
                    return "index#" + self.anchor()
                else:
                    return "#" + self.anchor()

    def prev_id(self):
        return self.order - 1

    def prev_if_single_page(self):
        """
        returns own order in multi-page system
        """
        if self._version.article.sections_over_pages:
            return self.order
        else:
            return self.prev_id()

    def reduced_name(self):
        """
        reduced name for space limited display
        """
        if len(self.name) > 25:
            return self.name[:25] + "[...]"
        else:
            return self.name

    def grafs_with_titles(self):
        return [x for x in self.grafs if x.title]

    def search_grafs(self):
        last_title = self.name
        for g in self.get_grafs():
            if g.title:
                last_title = g.title
            g.current_title = last_title
            if g.visible:
                yield g

    def get_grafs_with_titles(self):
        return self.get_grafs(just_titles=True)

    def get_kindle_grafs(self):
        self.kindle_extras = []
        if self._article.display_notes:
            for g in self.get_grafs():
                all = [x for x in g.self_and_extras()]
                if len(all) > 1:
                    all[-1].type = Graf.EXTENDED_END
                for a in all:
                    yield a
        else:
            for g in self.get_grafs():
                if g.type in [Graf.EXTENDED_START, Graf.EXTENDED_COMPLETE]:
                    self.kindle_extras.append(g)
                else:
                    yield g

    def get_kindle_extras(self):
        for g in self.kindle_extras:
            yield g

    def has_grafs(self):
        if self.grafs:
            return True
        return False

    def get_grafs(self, just_titles=False):

        if hasattr(self, "stored_grafs"):
            for g in self.stored_grafs:
                yield g
            return
        else:
            self.stored_grafs = []

        """
        does some proprocessing to get ready for template
        """
        if just_titles:
            temp_grafs = self.grafs_with_titles()
        else:
            temp_grafs = self.grafs
        last_title = None
        prev_block_is_block = False
        expanded_block = None
        for x, p in enumerate(temp_grafs):
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
            p._section = self
            p.start_tag = p.block_start(prev_block=prev_block_is_block)
            p.end_tag = p.block_end(next_block=next_block_is_block)
            p.expand_link = [p.end_expand_link(
                next_block_type=next_block_type), next_id]
            if p.title:
                last_title = p
                p.last_title_order = self.order
            elif last_title == None:
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
                self.stored_grafs.append(expanded_block)
                if expanded_block.visible:
                    yield expanded_block
                expanded_block = None
            else:
                self.stored_grafs.append(p)
                if p.visible:
                    yield p

    def anchor(self):
        """
        returns an identifiable marker for this paragraph
        from name
        """
        if self.name == "":
            return "start"

        def depuntuate(s):
            return re.sub(r'[^\w\s]', '', s)

        new = depuntuate(self.name).replace(" ", "-").strip().lower()
        if self.anchor_offset:
            new += "_" + self.anchor_offset
        return new

    class Meta:
        ordering = ['order']


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
        (EXTENDED_COMPLETE, "Extended Complete")
    ]

    def __init__(self, *args, **kwargs):
        self.id = ""
        self.title = ""
        self.html = ""
        self.plain_txt = ""
        self.header_level = 0
        self.order = 0
        self.real_order = 0
        self.asset = None
        self.type = ""
        self.anchor_offset = ""
        self.blockquote = False
        self.key = ""
        self.start_key = ""
        self.letter_key = ""
        self.letter_seq = ""
        self.end_key = ""
        self.catch_up = ""
        self.footnotes = []
        self.tag = None
        self.para_tag = None
        self.page_tag = None
        self.visible = True
        self.extra_grafs = []
        self.stored_grafs = []
        self.position_key = 0
        self.__dict__.update(kwargs)

    def escape_text(self):
        txt = self.plain_txt.encode('ascii', 'xmlcharrefreplace')
        txt = txt.replace(b"[", b"").replace(b"]", b"").replace(b"\n", b"")
        return txt.decode('utf-8')

    def paragraph_image_url(self):
        return "/media/paragraphs/{0}.png".format(self.combo_key())

    def nav_url(self):
        """
        nav url to this graf
        """
        anchor = self.anchor()
        if anchor == "":
            anchor = self.combo_key()

        if self._section._version.article.sections_over_pages:
            return self._section.nav_url(include_anchor=False) + "#" + anchor
        else:
            if self._section._version.article.search:
                if self._section._version.article.baking:
                    return "index.html#" + anchor
                else:
                    return "./#" + anchor
            else:
                return "#" + anchor

    def opacity_visible(self):
        """
        Called by template. 
        if visiblity has an opacity class - inject it
        """
        if self.visible != True:
            if 'opacity' in self.visible:
                return self.visible
        return ""

    def classes(self):
        """
        Called by template. 
        classes to inject into row object
        """
        if self.start_tag == "StartNotes":
            return "extended-row"
        else:
            return ""

    def anchor_code(self):
        """
        produces the code used to anchor the magic_cite system
        """
        properties = {"class": "anchor",
                      "name": self.order,
                      "position_key": self.position_key,
                      "key": self.key,
                      "start_key": self.start_key,
                      "end_key": self.end_key,
                      "parent": self._section.order,
                      "last_title": self.last_title_order,
                      "letter_key": self.letter_key,
                      "tag": self.tag,
                      "para_tag": self.para_tag,
                      "page_tag": self.page_tag,
                      }

        lines = ['{0} = "{1}"'.format(x, y)
                 for x, y in properties.items() if y]
        code = "<a {0}></a>".format(" ".join(lines))
        return mark_safe(code)

    def social_cite_link(self):
        return self._article.social_cite_link(self)

    def start_tag_class_type(self):
        if self.start_tag == "StartBlockQuote":
            return "blockquote"
        elif self.start_tag == "StartNotes":
            return "extended"
        return ""
            
        
    def extended(self):
        """
        Boolean - is this an extended paragraph>
        """
        return "E" in self.type

    def has_content(self):
        """
        is there any content in this graf?
        """
        for x in [self] + self.extra_grafs:
            if x.html:
                return True
        return False

    def self_and_extras(self):
        """
        return this and any child paragraphs (in extended sections)
        """
        for x in [self] + self.extra_grafs:
            if x.html:
                yield x

    def long_combo_key(self):
        """
        key for this paragrah - including letter starts
        """
        return ".".join([str(self.parent_id),
                         str(self.position_key),
                         self.key,
                         self.start_key,
                         self.end_key,
                         self.letter_key,
                         self.letter_seq
                         ])

    def combo_key(self):
        """
        key for this paragrah
        """
        return ".".join([str(self.parent_id),
                         str(self.position_key),
                         self.key,
                         self.start_key,
                         self.end_key,
                         self.letter_key,
                         ])

    def connect_to_footnote(self, text):

        for l in text.split("\n"):
            ref = re.search('\[\^[0-9\*]+\]\:', l)
            if ref:
                ref = ref.group()[:-1]
                note = l[l.find(":") + 1:].strip()

                for f in Footnote.all:
                    if f.content == "" and f.local_ref == ref:
                        f.set_content(note)

    def process(self, prev_type="", article=None):

        def depuntuate(s):
            return re.sub(r'[^\w\s]', '', s)

        def make_hash(txt):
            hasher = hashlib.sha1(depuntuate(txt).encode("utf-8"))
            return base64.urlsafe_b64encode(hasher.digest())[:5].lower().decode("utf-8")

        start_letters = [x[0].lower() for x in self.plain_txt.split(" ") if x]
        start_letters = "".join(
            [x for x in start_letters if x in string.ascii_lowercase])

        self.key = make_hash(self.plain_txt)
        # based on first letters (allows typo fixes)
        self.letter_key = make_hash(start_letters)
        self.letter_seq = start_letters
        self.start_key = make_hash(self.plain_txt[:10])
        self.end_key = make_hash(self.plain_txt[-10:])

        text = self.html

        """
        processes paragraph type
        """
        self.type = Graf.NORMAL

        if self.h_name == "blockquote":
            self.blockquote = True
        if re.search('\[\^[0-9\*]+\]\:', text):
            self.connect_to_footnote(text)
            self.html = ""
            self.type = None
            return None
        if text[:2] == "[[" and text[-2:] == "]]":
            text = text.replace("[[", "").replace("]]", "")
            self.type = Graf.EXTENDED_COMPLETE
        if text[:2] != "[[" and text[-2:] != "]]" and prev_type in [Graf.EXTENDED_START,
                                                                    Graf.EXTENDED_MIDDLE]:
            self.type = Graf.EXTENDED_MIDDLE
        if text[:2] != "[[" and text[-2:] == "]]":
            text = text.replace("[[", "").replace("]]", "")
            self.type = Graf.EXTENDED_END
        if text[:2] == "[[" and text[-2:] != "]]":
            text = text.replace("[[", "").replace("]]", "")
            self.type = Graf.EXTENDED_START

        """ extract and add spans to all double quotes"""
        for q in re.findall('""([^"]*?)""', text):
            text = text.replace(
                '""' + q + '""', '<span class="quote">"' + q + '"</span>')

        """ extract any tags """
        for q in re.findall('\[tag[^\)]*?]', text):
            self.tag = q.replace("[tag:", "").replace("]", "")
            text = text.replace(q, "")

        """ extract any para_tags """
        for q in re.findall('\[para[^\)]*?]', text):
            self.para_tag = q.replace("[para:", "").replace("]", "")
            text = text.replace(q, "")

        """ extract any page_tags """
        for q in re.findall('\[page[^\)]*?]', text):
            self.page_tag = q.replace("[page:", "").replace("]", "")
            text = text.replace(q, "")

        """ extract and replace assets """
        for q in re.findall('\[asset:[^\)]*]', text):
            asset = q.replace("[asset:", "").replace("]", "")
            real_asset = article.article.assets.filter(slug=asset)
            if real_asset.exists():
                obj = real_asset[0]
                obj.active = True
                obj.save()
                self.asset = obj.id
                text = text.replace(q, "{0}".format(obj.id))
            else:
                text = text.replace(q, "ASSET MISSING")

        # process footnotes - can't use an iter because amending size as we go
        match = True
        while match:
            match = re.search('\[\^[0-9\*]+\]', text)
            if match:
                q = match.group()
                new_note = Footnote(local_ref=q)
                ref_html = '<footref>{0}</footref>'.format(new_note.num)
                text = text[:match.start()] + ref_html + text[match.end():]
                self.footnotes.append(new_note)

        self.html = text

    def end_expand_link(self, next_block_type=""):
        if next:
            if next_block_type in [Graf.EXTENDED_START, Graf.EXTENDED_COMPLETE]:
                link_type = "expand"
            elif self.type in [Graf.EXTENDED_END, Graf.EXTENDED_COMPLETE]:
                link_type = "hide"
            else:
                link_type = ""
        return link_type

    def is_extended_start(self):
        return self.type in [Graf.EXTENDED_START, Graf.EXTENDED_COMPLETE]

    def is_extended_end(self):
        return self.type in [Graf.EXTENDED_END, Graf.EXTENDED_COMPLETE]

    def display(self):
        """
        render for display
        """
        text = self.html
        refs = BeautifulSoup(text, "html.parser").findAll({'footref': True})

        footnotes = self.footnotes
        footnote_lookup = {x.num: x for x in footnotes}

        for l in refs:
            ref_no = int(l.text)
            footnote = footnote_lookup[ref_no]
            new_ref = footnote.format(self.order)
            text = text.replace(str(l), new_ref)

        """
        swap out tag references so they can cross pages for multi-part articles
        """
        version = self._section._version
        if version.article.sections_over_pages:

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
                        url = version.sections[order -
                                               1].nav_url(include_anchor=False)
                        url += "#tag." + tag
                        text = text.replace('#tag.{0}'.format(tag), url)

        # make first sentence bold for screenshotting
        making_screenshot = False
        if hasattr(self._section._version.article, "making_screenshot"):
            making_screenshot = getattr(
                self._section._version.article, "making_screenshot")

        if making_screenshot:
            beg = 50
            if len(text) < beg:
                beg = 0
            try:
                end_of_sentence = text.index(".")
            except Exception:
                end_of_sentence = None
            if not end_of_sentence:
                try:
                    end_of_sentence = text.index(",", beg)
                except Exception:
                    end_of_sentence = None

            if end_of_sentence:
                text = '<span class="first-sentence">' + \
                    text[:end_of_sentence + 1] + "</span>" + \
                    text[end_of_sentence + 1:]

        return mark_safe(text)

    def display_text(self):
        return self.display_kindle(remove_links=False)

    def display_bare(self):
        text = self.html
        text = BeautifulSoup(text).text
        if len(text) > 420:
            text = text[:417] + "..."
        return text

    def display_kindle(self, remove_links=True):

        text = self.html
        links = BeautifulSoup(text, features="html5lib").findAll({'a': True})

        if remove_links:
            for l in links:
                if "href" in l and "#tag." not in l['href']:
                    text = text.replace(str(l), l.text)

        refs = BeautifulSoup(text, features="html5lib").findAll(
            {'footref': True})

        footnotes = self.footnotes
        footnote_lookup = {x.num: x for x in footnotes}

        for l in refs:
            ref_no = int(l.text)
            footnote = footnote_lookup[ref_no]
            new_ref = footnote.format_kindle()
            text = text.replace(str(l), new_ref)

        return mark_safe(text)

    def block_start(self, prev_block=None):
        """
        special start to block if start of note or blockquote section

        """

        if self.blockquote and prev_block is False:
            return "StartBlockQuote"
        if self.type == Graf.EXTENDED_START or self.type == Graf.EXTENDED_COMPLETE:
            return "StartNotes"

    def block_end(self, next_block=None):

        if self.blockquote and next_block is False:
            return True
        elif self.type == Graf.EXTENDED_END or self.type == Graf.EXTENDED_COMPLETE:
            return True
        else:
            return False

    def anchor(self):

        def depuntuate(s):
            return re.sub(r'[^\w\s]', '', s)

        new = depuntuate(self.title).replace(" ", "-").strip().lower()
        if self.anchor_offset:
            new += "_" + self.anchor_offset
        return new


def quote_fix(content):
    if not content:
        return content
    return content.replace("“", '"').replace("”", '"').replace("’", "'").replace("’", "'").replace("’", "'")


def move_extended_close(content):
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


def hide_footnote_refs(content):
    # hide footnotes from markdown processor
    content = content.replace("[^", "!!footnotestandin!!")
    return content


def return_footnote_refs(content):
    content = content.replace("!!footnotestandin!!", "[^")
    return content


def process_ink(version, content):

    Footnote.note_count = 0

    processors = [quote_fix,
                  move_extended_close,
                  hide_footnote_refs,
                  markdown.markdown,
                  return_footnote_refs]

    """
    #these are set back to active later if used
    """

    version.article.assets.all().update(active=False)
    processed = content
    for p in processors:
        processed = p(processed)

    lines = BeautifulSoup(processed, features="html5lib").findAll({'p': True,
                                                                   'ul': True,
                                                                   'h1': True,
                                                                   'h2': True,
                                                                   'h3': True,
                                                                   'h4': True,
                                                                   'h5': True,
                                                                   'blockquote': True,
                                                                   'ul': True,
                                                                   'ol': True,
                                                                   'table': True})

    order = 1
    s_order = 1
    version.sections = []
    s = Section(order=s_order)
    last_title = []
    last_type = ""
    section_title = ""
    catchup = ""
    inject_notes_start = False
    rand = RandomAssignment(version.article.seed)

    existing_anchors = []
    previous_anchors = {}
    
    def get_anchor_offset(v):
        if not v:
            return ""
        if v in existing_anchors:
            current = previous_anchors.get(v, 0)
            current += 1
            print (v + " already used")
            previous_anchors[v] = current
            return str(current)
        else:
            existing_anchors.append(v)
            return ""

    def extract_p_if_first(s):
        extract_ok = ["p", "blockquote"]
        for e in extract_ok:
            if s.name == e:
                return s.__unicode__().replace("<{0}>".format(e), "").replace("</{0}>".format(e), "")

        return s.__unicode__()
    header_level = 0
    for x, p in enumerate(lines):
        # doesn't give us double entries for <p> contained within these
        if p.text != "" and p.parent.name not in ["blockquote", "li"]:
            if p.name in ["h2", "h3", "h4"]:
                if section_title:
                    #if multiple headers straight after each other
                    ng = Graf(title=section_title,
                              order=order,
                              header_level=header_level,
                              parent_id=s.order,
                              anchor_offset=get_anchor_offset(section_title))
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
                s = Section(order=s_order,
                            name=p.text,
                            anchor_offset=get_anchor_offset(p.text))
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
                    ng = Graf(title=section_title,
                              plain_txt=plain_txt,
                              html=html,
                              h_name=p.name,
                              order=order,
                              header_level=header_level,
                              parent_id=s.order,
                              catch_up=catchup,
                              anchor_offset=get_anchor_offset(section_title))

                    catchup = ""
                    if section_title:
                        last_title = ng
                    ng.process(last_type, version)
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
