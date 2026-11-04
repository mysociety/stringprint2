"""Compile authored text into publication data without persistence or requests."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from stringprint2.document_structure import Section


@dataclass
class CompilationContext:
    seed: int
    assets: Mapping[str, int]
    sections: list[Section] = field(default_factory=list)
    used_asset_ids: set[int] = field(default_factory=set)
    diagnostics: list[str] = field(default_factory=list)
    has_notes: bool = False

    def resolve_asset(self, slug: str) -> int | None:
        asset_id = self.assets.get(slug)
        if asset_id is None:
            self.diagnostics.append(f"Asset missing: {slug}")
        else:
            self.used_asset_ids.add(asset_id)
        return asset_id


@dataclass(frozen=True)
class CompiledPublication:
    sections: tuple[Section, ...]
    has_notes: bool
    used_asset_ids: frozenset[int]
    diagnostics: tuple[str, ...]


def compile_document(
    source: str, *, seed: int, assets: Mapping[str, int]
) -> CompiledPublication:
    """Return the legacy-compatible document tree and its referenced assets."""
    from stringprint2.stringprint.tools.deepink import parse_ink

    context = CompilationContext(seed=seed, assets=assets)
    parse_ink(context, source)
    return CompiledPublication(
        sections=tuple(context.sections),
        has_notes=context.has_notes,
        used_asset_ids=frozenset(context.used_asset_ids),
        diagnostics=tuple(context.diagnostics),
    )
