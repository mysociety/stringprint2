"""
Persist and reconcile stable paragraph citation links.
"""

from __future__ import annotations

from pathlib import Path

import Levenshtein
from pydantic import BaseModel, ConfigDict
from ruamel.yaml import YAML

ParagraphLinkTarget = bool | str | None


def short_paragraph_key(key: str) -> str:
    """
    Return the six-component key used by rendered paragraph anchors.
    """
    return ".".join(key.split(".")[:6])


def paragraph_compatibility_map(
    links: dict[str, ParagraphLinkTarget],
) -> dict[str, str]:
    """
    Map historical paragraph keys onto current canonical anchor IDs.
    """
    compatibility: dict[str, str] = {}
    for historical, target in links.items():
        if target is None or target is False:
            continue
        current = historical if target is True else target
        canonical = short_paragraph_key(current)
        compatibility[historical] = canonical
        compatibility[short_paragraph_key(historical)] = canonical
    return compatibility


class ParagraphLink(BaseModel):
    """
    Map one historical paragraph key to its current destination.
    """

    model_config = ConfigDict(frozen=True)

    key: str
    target: ParagraphLinkTarget


class ParagraphLinkState(BaseModel):
    """
    Hold paragraph links in their stable persisted order.
    """

    model_config = ConfigDict(frozen=True)

    entries: tuple[ParagraphLink, ...] = ()

    @classmethod
    def from_legacy(cls, value: object) -> ParagraphLinkState:
        """
        Parse the historical list-of-single-item-mappings YAML structure.
        """

        if value is None:
            return cls()
        if not isinstance(value, list):
            raise ValueError("paragraph links must be a list")
        entries = []
        for item in value:
            if item is None:
                continue
            if not isinstance(item, dict) or len(item) != 1:
                raise ValueError("each paragraph link must contain one mapping")
            key, target = next(iter(item.items()))
            entries.append(ParagraphLink(key=str(key), target=target))
        return cls(entries=tuple(entries))

    def as_legacy(self) -> list[dict[str, ParagraphLinkTarget]]:
        """
        Return the committed YAML representation.
        """

        return [{entry.key: entry.target} for entry in self.entries]

    def lookup(self) -> dict[str, ParagraphLinkTarget]:
        """
        Return links keyed for reconciliation and route resolution.
        """

        return {entry.key: entry.target for entry in self.entries}


class ParagraphKey(BaseModel):
    """
    Parse the components used to match old and current paragraph keys.
    """

    model_config = ConfigDict(frozen=True)

    key: str
    section: str
    position: str
    paragraph: str
    start: str
    end: str
    letter: str | None = None
    sequence: str | None = None

    @classmethod
    def parse(cls, key: str) -> ParagraphKey:
        """
        Parse historical five-, six-, or seven-component keys.
        """

        parts: list[str | None] = list(key.split("."))
        if len(parts) < 5 or len(parts) > 7:
            raise ValueError(f"invalid paragraph key: {key}")
        parts.extend([None] * (7 - len(parts)))
        section, position, paragraph, start, end, letter, sequence = parts
        if None in (section, position, paragraph, start, end):
            raise ValueError(f"invalid paragraph key: {key}")
        return cls(
            key=key,
            section=str(section),
            position=str(position),
            paragraph=str(paragraph),
            start=str(start),
            end=str(end),
            letter=letter,
            sequence=sequence,
        )

    def value_for_rule(self, rule: str) -> str:
        """
        Return one deterministic matching value.
        """

        values = {
            "paragraph_position": self.position + self.paragraph,
            "paragraph": self.paragraph,
            "letter": self.letter or "",
            "start_end": self.start + self.end,
            "start_position": self.start + self.position,
            "end_position": self.end + self.position,
            "start": self.start,
            "end": self.end,
            "position_section": self.section + self.position,
        }
        return values[rule]


MATCH_RULES = (
    "paragraph_position",
    "paragraph",
    "letter",
    "start_end",
    "fuzzy",
    "start_position",
    "end_position",
    "start",
    "end",
    "position_section",
)


def match_orphan_paragraphs(
    current_keys: list[str],
    orphan_keys: list[str],
) -> dict[str, str | None]:
    """
    Match historical paragraph keys to unique current paragraphs.
    """

    candidates = [ParagraphKey.parse(key) for key in current_keys]
    mappings: dict[str, str | None] = {}
    for orphan_value in orphan_keys:
        orphan = ParagraphKey.parse(orphan_value)
        match: str | None = None
        for rule in MATCH_RULES:
            if rule == "fuzzy":
                if orphan.sequence:
                    fuzzy = []
                    for candidate in candidates:
                        if candidate.sequence:
                            distance = Levenshtein.distance(
                                orphan.sequence,
                                candidate.sequence,
                            )
                            if distance <= 7:
                                fuzzy.append((distance, candidate.key))
                    if fuzzy:
                        match = min(fuzzy, key=lambda item: item[0])[1]
            else:
                matches = [
                    candidate.key
                    for candidate in candidates
                    if candidate.value_for_rule(rule) == orphan.value_for_rule(rule)
                ]
                if len(matches) == 1:
                    match = matches[0]
            if match is not None:
                break
        mappings[orphan.key] = match
    return mappings


class ParagraphLinkStore(BaseModel):
    """
    Read, reconcile, and write one publication's paragraph link file.
    """

    model_config = ConfigDict(frozen=True)

    path: Path

    def load(self) -> ParagraphLinkState:
        """
        Load links, returning an empty state when no file exists.
        """

        if not self.path.is_file():
            return ParagraphLinkState()
        with self.path.open(encoding="utf-8") as file_handle:
            return ParagraphLinkState.from_legacy(YAML(typ="safe").load(file_handle))

    def save(self, state: ParagraphLinkState) -> None:
        """
        Write links in the historical reviewable YAML structure.
        """

        with self.path.open("w", encoding="utf-8") as file_handle:
            YAML().dump(state.as_legacy(), file_handle)

    def reconcile(
        self,
        state: ParagraphLinkState,
        current_keys: list[str],
        rendered_keys: list[str],
    ) -> ParagraphLinkState:
        """
        Preserve old links, add current links, and redirect matchable orphans.
        """

        lookup = state.lookup()
        for key in current_keys:
            if lookup.get(key) is None:
                lookup[key] = True

        short_keys = {".".join(key.split(".")[:6]) for key in lookup}
        new_rendered = [key for key in rendered_keys if key not in short_keys]
        for key in new_rendered:
            lookup[key] = None

        new_current = [key for key in current_keys if key not in state.lookup()]
        orphans = [
            key
            for key, target in lookup.items()
            if key not in current_keys and target not in current_keys
        ]
        lookup.update(match_orphan_paragraphs(current_keys, orphans))

        ordered_keys = [entry.key for entry in state.entries]
        ordered_keys.extend(new_current)
        ordered_keys.extend(new_rendered)
        return ParagraphLinkState(
            entries=tuple(
                ParagraphLink(key=key, target=lookup[key]) for key in ordered_keys
            )
        )
