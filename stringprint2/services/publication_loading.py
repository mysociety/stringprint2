"""
Prepare validated publication configuration for persistence.
"""

from __future__ import annotations

from collections.abc import Collection
from typing import NamedTuple, Protocol

from pydantic import BaseModel, ConfigDict
from stringprint2.configuration.models import (
    HeaderConfig,
    OrganisationConfig,
    PublicationConfig,
)

ARTICLE_FIELDS = frozenset(
    {
        "authors",
        "byline",
        "cite_as",
        "commands",
        "copyright",
        "description",
        "display_footnotes_at_foot",
        "display_notes",
        "file_source",
        "multipage",
        "pdf_file",
        "pdf_location",
        "production_url",
        "publish_date",
        "seed",
        "short_title",
        "subtitle",
        "title",
    }
)


class TemplateRenderer(Protocol):
    """
    Render an organisation default against authored publication values.
    """

    def __call__(self, template: str, publication: dict[str, object]) -> str:
        """
        Return the rendered default value.
        """
        ...


class FieldAssignment(NamedTuple):
    """
    Assign one configuration value to a Django Article field.
    """

    name: str
    value: object


class PublicationLoadPlan(BaseModel):
    """
    Describe all persistence and file actions needed to load a publication.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    field_assignments: list[FieldAssignment]
    extra_values: dict[str, object]
    header: HeaderConfig | None
    book_cover: str | None
    clear_pdf_file: bool
    use_default_production_url: bool


def build_publication_load_plan(
    publication: PublicationConfig,
    organisation: OrganisationConfig,
    existing_extra_keys: Collection[str],
    render_template: TemplateRenderer,
) -> PublicationLoadPlan:
    """
    Convert authored configuration into an explicit persistence plan.

    Legacy aliases and organisation defaults are resolved here without
    mutating either validated input model.
    """
    authored = publication.model_dump(exclude_unset=True)
    header = publication.header if "header" in publication.model_fields_set else None
    book_cover = (
        publication.book_cover if "book_cover" in publication.model_fields_set else None
    )
    authored.pop("header", None)
    authored.pop("book_cover", None)

    if "sections_over_pages" in authored:
        authored["multipage"] = authored.pop("sections_over_pages")
    if "pdf" in authored:
        authored["pdf_file"] = authored.pop("pdf")

    for name, template in organisation.default_values.items():
        if name not in authored:
            authored[name] = render_template(template, authored)

    existing_extra_keys = set(existing_extra_keys)
    assignments = []
    extra_values = {}
    for name, value in authored.items():
        if name in ARTICLE_FIELDS and name not in existing_extra_keys:
            assignments.append(FieldAssignment(name, value))
        else:
            extra_values[name] = value

    return PublicationLoadPlan(
        field_assignments=assignments,
        extra_values=extra_values,
        header=header,
        book_cover=book_cover,
        clear_pdf_file="pdf_file" not in authored,
        use_default_production_url="production_url" not in authored,
    )
