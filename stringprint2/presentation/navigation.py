"""Template-facing navigation objects built from a publication's sections."""

from __future__ import annotations

from dataclasses import dataclass, field
from django.utils.safestring import mark_safe


@dataclass
class NavigationLink:
    _toc: TableOfContents = field(repr=False, compare=False)
    id: int = 0
    order: int = 0
    anchor: str = ""
    nav_url: str = ""
    name: str = ""
    level: int = 1
    reduced_diff: int = 0

    @property
    def collection(self):
        return self._toc.items

    def future(self):
        if self.order + 1 < len(self.collection):
            return self.collection[self.order + 1]
        return None

    def future_level_difference(self):
        f = self.future()
        if not f:
            return 0
        return f.level - self.level

    def has_children(self):
        f = self.future()
        return f is not None and f.level > self.level

    def caret_title(self):
        """
        splits title into layers based on words
        to stop very long horizontal titles in submenus
        """

        groups = []
        current = []
        count = 0
        for word in self.name.split(" "):
            count += len(word)
            current.append(word)
            if count > 35:
                groups.append(" ".join(current))
                current = []
                count = 0
        if current:
            groups.append(" ".join(current))
        return mark_safe("<br>".join(groups))

    def children(self):
        future = self._toc.items[self.order + 1 :]
        children = []
        for i in future:
            if i.level == self.level:
                break
            if i.level == self.level + 1:
                children.append(i)
        return children


class TableOfContents:
    def __init__(self):
        self.items: list[NavigationLink] = []

    def final_level(self):
        return self.items[-1].level

    def final_level_range(self):
        return range(0, self.final_level())

    def final_level_range_left_open(self, offset=1):
        item = 0
        for i in self.items[::-1]:
            if i.level in [1, 2]:
                item = i.level
                break
        return range(0, item - offset)

    def final_level_range_left_open_minus_one(self):
        return self.final_level_range_left_open(2)

    def add(self, *, name: str, anchor: str, nav_url: str, id: int, level: int):
        item = NavigationLink(
            _toc=self, name=name, anchor=anchor, nav_url=nav_url, id=id, level=level
        )
        item.order = len(self.items)
        self.items.append(item)

    def top_two_levels(self):
        items = [item for item in self.items if item.level in (1, 2)]
        for index, current in enumerate(items):
            next_level = items[index + 1].level if index + 1 < len(items) else 0
            current.reduced_diff = next_level - current.level
            yield current

    def __iter__(self):
        for i in self.items:
            yield i

    def level_1(self):
        """
        get just top level (sections)
        """
        for s in self:
            if s.level == 1:
                yield s


def build_table_of_contents(sections) -> TableOfContents:
    toc = TableOfContents()

    stand_in_introduction = "Introduction"

    for s in sections:
        if s.name == stand_in_introduction:
            stand_in_introduction = "Summary"
            break

    for s in sections:
        if s.has_grafs():
            name = s.name
            if s.order == 1 and not name:
                name = stand_in_introduction
            if name:
                toc.add(
                    name=name,
                    anchor=s.anchor(),
                    nav_url=s.nav_url(),
                    id=s.order,
                    level=1,
                )
            for g in s.get_grafs():
                if g.title:
                    toc.add(
                        name=g.title,
                        anchor=g.anchor(),
                        nav_url=g.nav_url(),
                        id=g.order,
                        level=g.header_level,
                    )
    return toc
