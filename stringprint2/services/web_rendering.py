"""
Render persisted publications as self-contained static websites.
"""

from __future__ import annotations

import shutil
from copy import copy
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Protocol

from django.conf import settings
from django.contrib.staticfiles import finders
from django.http import HttpRequest
from dirsync import sync  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict

from stringprint2.services.static_rendering import write_baked_file


class WebPublicationOrganisation(Protocol):
    """
    Organisation paths required when assembling a static publication.
    """

    slug: str
    storage_dir: str


class WebPublication(Protocol):
    """
    Publication state and operations required by the web renderer.
    """

    assets: Any
    compressed_files: list[str]
    extra_values: dict[str, Any]
    images: Any
    multipage: bool
    org: WebPublicationOrganisation
    pdf_file: Any
    production_url: str
    slug: str

    def save(self) -> None:
        """
        Persist a changed production URL.
        """

        ...

    def tinify_headers(self) -> None:
        """
        Prepare small header images.
        """

        ...

    def export_paragraph_images(self, folder: str, refresh_all: bool = False) -> None:
        """
        Export social images for rendered paragraphs.
        """

        ...

    def display_content(self) -> Any:
        """
        Return compiled display content.
        """

        ...

    def create_kindle(self, destination: Path, use_temp: bool = False) -> object:
        """
        Render the optional Kindle output.
        """

        ...

    def create_ebook(self, destination: Path) -> object:
        """
        Render the optional EPUB output.
        """

        ...


class WebRenderResult(BaseModel):
    """
    Describe routes and redirects emitted by a static web render.
    """

    model_config = ConfigDict(frozen=True)

    destination: Path
    page_count: int
    redirect_count: int
    copied_media_count: int


def require_static_file(name: str) -> Path:
    """
    Resolve one configured static file or fail with its logical name.
    """

    located = finders.find(name)
    if located is None:
        raise FileNotFoundError(f"Could not find static file: {name}")
    return Path(located)


def create_web_directories(
    publication: WebPublication,
    destination: Path,
) -> Path | None:
    """
    Create the publication output tree and return any organisation static root.
    """

    directories = (
        destination,
        destination / "static" / "css",
        destination / "static" / "CACHE" / "css",
        destination / "static" / "CACHE" / "js",
        destination / "static" / "js",
        destination / "static" / "images",
        destination / "media" / "paragraphs",
        destination / "l",
    )
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    organisation_static = Path(publication.org.storage_dir) / "_static"
    if not organisation_static.exists():
        return None
    (destination / "static" / "orgs" / publication.org.slug).mkdir(
        parents=True,
        exist_ok=True,
    )
    return organisation_static


def render_web_publication_staging(
    publication: WebPublication,
    destination: Path,
    *,
    url: str | None = None,
    plain: bool = True,
    kindle: bool = False,
    epub: bool = True,
    refresh_all: bool = False,
) -> WebRenderResult:
    """
    Render a publication and all supporting files to a static directory.
    """

    from stringprint2.stringprint.views import (  # type: ignore[import-not-found]
        ArticleView,
        ParagraphMapView,
        RedirectLink,
        SearchContentView,
        SearchView,
        TextView,
        TOCView,
    )

    publication = copy(publication)
    publication.compressed_files = []
    target_url = publication.production_url if url is None else url
    if url is not None and url != publication.production_url:
        publication.production_url = url
        publication.save()
    if not target_url:
        raise ValueError("No valid sharing URL stated.")

    publication.tinify_headers()
    organisation_static = create_web_directories(publication, destination)
    if kindle:
        publication.create_kindle(destination, use_temp=True)
    if epub and not publication.extra_values.get("skip_epub", False):
        publication.create_ebook(destination)
    render_context: dict[str, object] = {
        "SITE_ROOT": target_url,
        "debug": False,
        "publication_bake": True,
        "epub": (destination / f"{publication.slug}.epub").is_file(),
        "kindle": (destination / f"{publication.slug}.mobi").is_file(),
        "plain": plain,
    }

    if publication.pdf_file:
        source = (
            Path(publication.org.storage_dir)
            / "_docs"
            / publication.slug
            / str(publication.pdf_file)
        )
        shutil.copyfile(source, destination / f"{publication.slug}.pdf")
    for filename in publication.extra_values.get("copy_files", []):
        source = (
            Path(publication.org.storage_dir) / "_docs" / publication.slug / filename
        )
        shutil.copyfile(source, destination / filename)

    publication.export_paragraph_images(
        str(destination / "media" / "paragraphs"),
        refresh_all=refresh_all,
    )
    vars(publication).update(publication.extra_values)
    current_publication = publication

    class BakeArticleView(ArticleView):  # type: ignore[misc]
        share_image = "{{SITE_ROOT}}/{{article.get_share_image}}"
        twitter_share_image = "{{SITE_ROOT}}/{{article.get_share_image}}"
        article_settings_override = {
            "paywall": False,
            "baking": True,
            "search": False,
        }

        def get_article(
            self,
            request: HttpRequest,
            article_slug: str,
        ) -> WebPublication:
            return current_publication

    class BakeSearchContentView(SearchContentView):  # type: ignore[misc]
        article_settings_override = {
            "paywall": False,
            "baking": True,
            "search": True,
        }

    class BakeSearchView(SearchView):  # type: ignore[misc]
        article_settings_override = {
            "paywall": False,
            "baking": True,
            "search": True,
        }

        def get_article(
            self,
            request: HttpRequest,
            article_slug: str,
        ) -> WebPublication:
            return current_publication

    class BakeParagraphMapView(ParagraphMapView):  # type: ignore[misc]
        article_settings_override = {
            "paywall": False,
            "baking": True,
            "search": False,
        }

        def get_article(
            self,
            request: HttpRequest,
            article_slug: str,
        ) -> WebPublication:
            return current_publication

    class BakeTOCView(TOCView):  # type: ignore[misc]
        article_settings_override = {
            "paywall": False,
            "baking": True,
            "search": False,
        }

    class BakePlainView(TextView):  # type: ignore[misc]
        article_settings_override = {
            "paywall": False,
            "baking": True,
            "search": False,
        }

    for view in (
        BakeArticleView,
        BakeSearchView,
        BakeSearchContentView,
        BakeParagraphMapView,
        BakeTOCView,
        BakePlainView,
    ):
        view.render_context = render_context

    setattr(publication, "baking", True)
    content = publication.display_content()
    grafs = {graf.long_combo_key(): graf for graf in content.all_grafs()}
    grafs.update({graf.combo_key(): graf for graf in content.all_grafs()})
    paragraph_lookup = content.paragraph_lookup()
    redirect_count = 0

    for key, value in paragraph_lookup.items():
        shorter_link = ".".join(key.split(".")[:6])

        class BakeRedirectLinkView(RedirectLink):  # type: ignore[misc]
            def load_article(
                self,
                request: HttpRequest,
                article_slug: str,
                paragraph_slug: str,
            ) -> None:
                self.article = current_publication
                setattr(self.article, "baking", True)
                self.content = content
                self.graf = None
                if value is True:
                    self.graf = grafs.get(key)
                elif value is not None:
                    self.graf = grafs.get(value)
                if self.graf:
                    self.graf._article = current_publication
                self.paragraph_tag = shorter_link

        BakeRedirectLinkView.render_context = render_context

        write_baked_file(
            BakeRedirectLinkView,
            destination / "l" / f"{shorter_link}.html",
            ("blah", "blah"),
            destination,
        )
        redirect_count += 1

    page_count = 0
    if publication.multipage:
        for section in content.sections:
            anchor = section.anchor()
            write_baked_file(
                BakeArticleView,
                destination / f"{anchor}.html",
                (publication.slug, anchor),
                destination,
            )
            page_count += 1

    arguments = (publication.slug,)
    targets = (
        (BakeArticleView, destination / "index.html"),
        (BakeSearchView, destination / "search.html"),
        (BakeSearchContentView, destination / "search_content.js"),
        (BakeParagraphMapView, destination / "paragraph_map.json"),
        (BakeTOCView, destination / "toc.json"),
    )
    for view, path in targets:
        write_baked_file(view, path, arguments, destination)
        page_count += 1
    if plain:
        write_baked_file(
            BakePlainView,
            destination / "plain.html",
            arguments,
            destination,
        )
        page_count += 1

    compress_url = str(getattr(settings, "COMPRESS_URL", settings.STATIC_URL))
    publication.compressed_files = [
        name[len(compress_url) :] for name in publication.compressed_files
    ]
    static_files = [
        "js//sweetalert2.all.min.js",
        "js//picturefill.min.js",
        "css//kindle.css",
        "css//text_mode.css",
        "css//fa_reduced.css",
        *publication.compressed_files,
    ]
    for filename in static_files:
        target = destination / "static" / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(require_static_file(filename), target)
    for folder in ("favicon", "licences", "font"):
        target = destination / "static" / folder
        target.mkdir(parents=True, exist_ok=True)
        sync(str(require_static_file(folder)), str(target), "sync")
    if organisation_static is not None:
        sync(
            str(organisation_static),
            str(destination / "static" / "orgs" / publication.org.slug),
            "sync",
        )

    media_root = Path(settings.MEDIA_ROOT)
    copied_media_count = 0
    for image in publication.images.all():
        for filename in image.get_all_files():
            source = media_root / filename
            if source.exists():
                shutil.copyfile(source, destination / "media" / filename)
                copied_media_count += 1
    for asset in publication.assets.filter(active=True):
        if asset.image:
            for filename in asset.get_all_files():
                shutil.copyfile(
                    media_root / filename,
                    destination / "media" / filename,
                )
                copied_media_count += 1
        if asset.image_chart:
            shutil.copyfile(
                media_root / asset.image_chart.name,
                destination / "media" / asset.image_chart.name,
            )
            copied_media_count += 1

    return WebRenderResult(
        destination=destination,
        page_count=page_count,
        redirect_count=redirect_count,
        copied_media_count=copied_media_count,
    )


def render_web_publication(
    publication: WebPublication,
    destination: Path,
    *,
    url: str | None = None,
    plain: bool = True,
    kindle: bool = False,
    epub: bool = True,
    refresh_all: bool = False,
) -> WebRenderResult:
    """
    Build in sibling staging and atomically replace the live publication.
    """

    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(
        dir=destination.parent,
        prefix=f".{destination.name}-",
    ) as temporary_directory:
        temporary_root = Path(temporary_directory)
        staging = temporary_root / "next"
        previous = temporary_root / "previous"
        result = render_web_publication_staging(
            publication,
            staging,
            url=url,
            plain=plain,
            kindle=kindle,
            epub=epub,
            refresh_all=refresh_all,
        )
        if destination.exists():
            destination.rename(previous)
        try:
            staging.rename(destination)
        except Exception:
            if previous.exists() and not destination.exists():
                previous.rename(destination)
            raise
        return result.model_copy(update={"destination": destination})
