"""
Pydantic models for Stringprint's authored configuration files.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator


class ConfigurationModel(BaseModel):
    """
    Reject configuration keys that Stringprint does not understand.
    """

    model_config = ConfigDict(extra="forbid")


class RepositoryOrganisationConfig(ConfigurationModel):
    """
    Locate one organisation's source and optional publication directory.
    """

    storage_dir: Path
    publish_dir: Path | None = None

    @field_validator("publish_dir", mode="before")
    @classmethod
    def empty_publish_directory(cls, value: object) -> object:
        return None if value == "" else value


class RepositoryConfig(ConfigurationModel):
    """
    Configure the Django application for a document repository.
    """

    chrome_driver: Path | None = Field(default=None, alias="CHROME_DRIVER")
    kindlegen_location: Path | None = Field(default=None, alias="KINDLEGEN_LOC")
    site_name: str = Field(alias="SITE_NAME")
    secret_key: str = Field(alias="SECRET_KEY")
    tiny_png_key: str = Field(default="", alias="TINY_PNG_KEY")
    media_root: Path | None = Field(default=None, alias="MEDIA_ROOT")
    organisations: dict[str, RepositoryOrganisationConfig] = Field(
        alias="ORGS", min_length=1
    )


class OrganisationLinkConfig(ConfigurationModel):
    """
    Define a named external link and its display order.
    """

    link: str
    order: int


class OrganisationConfig(ConfigurationModel):
    """
    Configure organisation-wide publication defaults and branding.
    """

    name: str
    twitter: str | None = None
    ga_code: str | None = None
    ga_cookies: bool = True
    publish_root: str
    icon: str | None = None
    include_favicon: bool = True
    orglinks: dict[str, OrganisationLinkConfig] = Field(default_factory=dict)
    commands: dict[str, str] = Field(default_factory=dict)
    default_values: dict[str, str] = Field(default_factory=dict)


class HeaderConfig(ConfigurationModel):
    """
    Configure a publication's title image.
    """

    location: str
    size: int | Literal["background"] = 6
    alt_text: str | None = None
    source_url: str | None = None
    credit: str | None = None
    description: str | None = None
    unsplash_id: str | None = None


class PublicationConfig(ConfigurationModel):
    """
    Describe one long-form publication.
    """

    title: str
    short_title: str
    description: str
    byline: str | None
    authors: str | None
    cite_as: str
    file_source: str
    publish_date: date
    sections_over_pages: bool = False
    display_notes: bool = False
    display_footnotes_at_foot: bool = True
    repo_slug: str
    subtitle: str | None = None
    copyright: str | None = None
    header: HeaderConfig | None = None
    book_cover: str | None = None
    seed: int = 13
    pdf: str | None = None
    pdf_location: str | None = None
    production_url: str | None = None
    repo_entry: str | None = None
    commands: dict[str, str] = Field(default_factory=dict)
    web_operations: list[Literal["publish"]] = Field(default_factory=list)
    google_doc_url: str | None = None
    unsplash_title_image_url: str | None = None
    bottom_iframe: str | None = None
    skip_epub: bool = False
    files: list[str] = Field(default_factory=list)


class AssetConfig(ConfigurationModel):
    """
    Define fields shared by every publication asset.
    """

    caption: str | None = None
    alt_text: str | None = None
    longdesc: str | None = None


class ImageAssetConfig(AssetConfig):
    """
    Define a raster image asset.
    """

    content_type: Literal["image"]
    type: Literal["jpeg", "jpg", "png"]
    size: int = 6


class TableAssetConfig(AssetConfig):
    """
    Define a spreadsheet rendered with a header row.
    """

    content_type: Literal["table"]
    type: Literal["xls", "xlsx"]


class HeaderlessTableAssetConfig(AssetConfig):
    """
    Define a spreadsheet rendered without a header row.
    """

    content_type: Literal["table-no-header"]
    type: Literal["xls", "xlsx"]


class HtmlAssetConfig(AssetConfig):
    """
    Define an authored HTML fragment.
    """

    content_type: Literal["html"]
    type: Literal["html"]


PublicationAssetConfig = Annotated[
    ImageAssetConfig | TableAssetConfig | HeaderlessTableAssetConfig | HtmlAssetConfig,
    Field(discriminator="content_type"),
]


class AssetCollection(RootModel[list[dict[str, PublicationAssetConfig]]]):
    """
    Preserve the authored ordered list of single-name asset mappings.
    """
