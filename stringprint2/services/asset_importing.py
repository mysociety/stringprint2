"""
Prepare validated asset configuration for Django persistence.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict
from stringprint2.configuration.models import AssetCollection


class AssetImportItem(BaseModel):
    """
    Describe one asset file and its normalized persistence values.
    """

    model_config = ConfigDict(frozen=True)

    slug: str
    content_type: Literal["image", "table", "html"]
    extension: str
    caption: str | None
    alt_text: str | None
    long_description: str
    no_header: bool = False
    size: int = 6


class AssetImportPlan(BaseModel):
    """
    Contain all asset imports in authored order.
    """

    model_config = ConfigDict(frozen=True)

    items: list[AssetImportItem]


def build_asset_import_plan(collection: AssetCollection) -> AssetImportPlan:
    """
    Normalize discriminated asset models without losing authored semantics.
    """
    items = []
    for asset_group in collection.root:
        for slug, asset in asset_group.items():
            content_type = asset.content_type
            if content_type == "table-no-header":
                normalized_content_type: Literal["image", "table", "html"] = "table"
                no_header = True
            else:
                normalized_content_type = content_type
                no_header = False
            alt_text = (
                asset.alt_text
                if "alt_text" in asset.model_fields_set
                else asset.caption
            )
            items.append(
                AssetImportItem(
                    slug=slug,
                    content_type=normalized_content_type,
                    extension=asset.type,
                    caption=asset.caption,
                    alt_text=alt_text,
                    long_description=asset.longdesc or "",
                    no_header=no_header,
                    size=getattr(asset, "size", 6),
                )
            )
    return AssetImportPlan(items=items)
