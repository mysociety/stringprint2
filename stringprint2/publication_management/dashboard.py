"""Typed publication dashboard assembly from source and persisted state."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

from pydantic import BaseModel, ConfigDict

from .models import PublicationOperation
from stringprint2.configuration.loaders import (
    load_organisation_config,
    load_publication_config,
)
from stringprint2.services.publication_catalog import discover_publications

if TYPE_CHECKING:
    from django.db.models import Manager

    from stringprint2.stringprint.models import Article, Organisation


class PublicationDashboardEntry(BaseModel):
    """Describe source, load, configuration, and operation state for one publication."""

    model_config = ConfigDict(frozen=True)

    slug: str
    title: str
    loaded: bool
    configuration_error: str = ""
    latest_operation_id: int | None = None
    latest_operation_state: str = ""


def build_publication_dashboard(
    organisation: Organisation,
) -> tuple[PublicationDashboardEntry, ...]:
    """Combine authored folders with database and latest-operation state."""
    article_manager = cast("Manager[Article]", getattr(organisation, "articles"))
    articles: dict[str, Article] = {
        article.slug: article
        for article in article_manager.only("id", "slug", "title")
        if article.slug is not None
    }
    documents_root = Path(organisation.storage_dir, "_docs")
    catalog = discover_publications(documents_root, articles)
    latest_operations: dict[str, PublicationOperation] = {}
    for operation in PublicationOperation.objects.filter(
        organisation=organisation
    ).order_by("publication_slug", "-created_at", "-pk"):
        latest_operations.setdefault(operation.publication_slug, operation)

    entries = []
    load_organisation_config(Path(organisation.storage_dir, "_conf", "settings.yaml"))
    for source in catalog.entries:
        article = articles.get(source.slug)
        latest = latest_operations.get(source.slug)
        configuration_error = ""
        try:
            load_publication_config(source.folder / "settings.yaml")
        except (OSError, RuntimeError, ValueError) as error:
            configuration_error = str(error)
        entries.append(
            PublicationDashboardEntry(
                slug=source.slug,
                title=(article.title or source.slug)
                if article is not None
                else source.slug,
                loaded=source.loaded,
                configuration_error=configuration_error,
                latest_operation_id=latest.pk if latest is not None else None,
                latest_operation_state=latest.state if latest is not None else "",
            )
        )
    source_slugs = {entry.slug for entry in catalog.entries}
    for slug, article in sorted(articles.items()):
        if slug in source_slugs:
            continue
        latest = latest_operations.get(slug)
        entries.append(
            PublicationDashboardEntry(
                slug=slug,
                title=article.title or slug,
                loaded=True,
                configuration_error="Publication source folder not found",
                latest_operation_id=latest.pk if latest is not None else None,
                latest_operation_state=latest.state if latest is not None else "",
            )
        )
    return tuple(sorted(entries, key=lambda entry: entry.slug))


def publication_source_exists(organisation: Organisation, slug: str) -> bool:
    """Validate a requested source slug against discovered publication folders."""
    root = Path(organisation.storage_dir, "_docs")
    catalog = discover_publications(root, ())
    return any(entry.slug == slug for entry in catalog.entries)
