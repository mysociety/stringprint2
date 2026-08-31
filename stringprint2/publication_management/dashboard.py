"""Typed publication dashboard assembly from source and persisted state."""

from __future__ import annotations

from pathlib import Path
from subprocess import SubprocessError

from pydantic import BaseModel, ConfigDict

from publication_management.models import PublicationOperation
from stringprint.models import Organisation
from stringprint2.configuration.loaders import (
    load_organisation_config,
    load_publication_config,
)
from stringprint2.services.publication_catalog import discover_publications
from stringprint2.services.publication_freshness import publication_needs_update


class PublicationDashboardEntry(BaseModel):
    """Describe source, load, freshness, and operation state for one publication."""

    model_config = ConfigDict(frozen=True)

    slug: str
    title: str
    loaded: bool
    needs_update: bool | None
    configuration_error: str = ""
    latest_operation_id: int | None = None
    latest_operation_state: str = ""


def build_publication_dashboard(
    organisation: Organisation,
) -> tuple[PublicationDashboardEntry, ...]:
    """Combine authored folders with database and latest-operation state."""
    articles = {
        article.slug: article
        for article in organisation.articles.only("id", "slug", "title")
    }
    documents_root = Path(organisation.storage_dir, "_docs")
    catalog = discover_publications(documents_root, articles)
    latest_operations: dict[str, PublicationOperation] = {}
    for operation in PublicationOperation.objects.filter(
        organisation=organisation
    ).order_by("publication_slug", "-created_at", "-pk"):
        latest_operations.setdefault(operation.publication_slug, operation)

    entries = []
    organisation_config = load_organisation_config(
        Path(organisation.storage_dir, "_conf", "settings.yaml")
    )
    for source in catalog.entries:
        article = articles.get(source.slug)
        latest = latest_operations.get(source.slug)
        needs_update = None
        configuration_error = ""
        try:
            config = load_publication_config(
                source.folder / "settings.yaml",
                organisation_config,
            )
            needs_update = publication_needs_update(source.folder, config)
        except (OSError, RuntimeError, SubprocessError, ValueError) as error:
            configuration_error = str(error)
        entries.append(
            PublicationDashboardEntry(
                slug=source.slug,
                title=article.title if article is not None else source.slug,
                loaded=source.loaded,
                needs_update=needs_update,
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
                title=article.title,
                loaded=True,
                needs_update=None,
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
