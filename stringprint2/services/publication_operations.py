"""Typed publication operations shared by command-line and web delivery."""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal, NamedTuple, Protocol, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from stringprint2.services.publication_archiving import render_publication_archive
from stringprint2.services.publication_rendering import (
    PublicationRenderFormat,
    RenderablePublication,
    render_publication,
)
from stringprint2.services.publication_workflow import (
    PublicationDocument,
    load_publication,
    process_publication,
    run_publication_command,
)


class PublicationOperationName(StrEnum):
    """Identify an operation that delivery interfaces may execute."""

    LOAD = "load"
    PROCESS = "process"
    RENDER = "render"
    ARCHIVE = "archive"
    PUBLISH = "publish"


class PublicationOperationStage(StrEnum):
    """Describe stable, user-facing stages of an operation."""

    STARTING = "starting"
    LOADING = "loading"
    PROCESSING = "processing"
    RENDERING = "rendering"
    ARCHIVING = "archiving"
    PUBLISHING = "publishing"
    COMPLETE = "complete"


class ManagedPublication(PublicationDocument, RenderablePublication, Protocol):
    """Expose the publication behaviour required by managed operations."""


class ProgressReporter(Protocol):
    """Receive durable stage changes from an operation runner."""

    def update(self, stage: PublicationOperationStage, detail: str = "") -> None:
        """Record the operation's current stage and optional detail."""


class NullProgressReporter:
    """Ignore progress for foreground callers that do not need it."""

    def update(self, stage: PublicationOperationStage, detail: str = "") -> None:
        """Accept a progress update without storing it."""


class PublicationOperationContext(NamedTuple):
    """Provide runtime dependencies that should not be serialized."""

    publication: ManagedPublication
    source_folder: Path
    publish_folder: Path
    progress: ProgressReporter


class LoadPublicationRequest(BaseModel):
    """Request configuration loading without source compilation."""

    model_config = ConfigDict(frozen=True)

    operation: Literal[PublicationOperationName.LOAD] = PublicationOperationName.LOAD
    organisation_slug: str
    publication_slug: str
    refresh_header: bool = False


class ProcessPublicationRequest(BaseModel):
    """Request compilation of one publication's authored source."""

    model_config = ConfigDict(frozen=True)

    operation: Literal[PublicationOperationName.PROCESS] = (
        PublicationOperationName.PROCESS
    )
    organisation_slug: str
    publication_slug: str
    refresh_header: bool = True
    preprocess: bool = True


class RenderPublicationRequest(BaseModel):
    """Request one rendered output format for a publication."""

    model_config = ConfigDict(frozen=True)

    operation: Literal[PublicationOperationName.RENDER] = (
        PublicationOperationName.RENDER
    )
    organisation_slug: str
    publication_slug: str
    output_format: PublicationRenderFormat = PublicationRenderFormat.WEB
    refresh: bool = False


class ArchivePublicationRequest(BaseModel):
    """Request a ZIP archive of a rendered web publication."""

    model_config = ConfigDict(frozen=True)

    operation: Literal[PublicationOperationName.ARCHIVE] = (
        PublicationOperationName.ARCHIVE
    )
    organisation_slug: str
    publication_slug: str
    refresh: bool = False


class PublishPublicationRequest(BaseModel):
    """Request the fixed configured publication workflow."""

    model_config = ConfigDict(frozen=True)

    operation: Literal[PublicationOperationName.PUBLISH] = (
        PublicationOperationName.PUBLISH
    )
    organisation_slug: str
    publication_slug: str
    render_archive: bool = True
    refresh: bool = False


PublicationOperationRequest: TypeAlias = Annotated[
    LoadPublicationRequest
    | ProcessPublicationRequest
    | RenderPublicationRequest
    | ArchivePublicationRequest
    | PublishPublicationRequest,
    Field(discriminator="operation"),
]


class LoadPublicationResult(BaseModel):
    """Describe a completed configuration-loading operation."""

    model_config = ConfigDict(frozen=True)

    operation: Literal[PublicationOperationName.LOAD] = PublicationOperationName.LOAD
    title: str


class ProcessPublicationResult(BaseModel):
    """Describe a completed source-processing operation."""

    model_config = ConfigDict(frozen=True)

    operation: Literal[PublicationOperationName.PROCESS] = (
        PublicationOperationName.PROCESS
    )
    title: str


class RenderPublicationResult(BaseModel):
    """Describe a completed rendering operation and its artefact."""

    model_config = ConfigDict(frozen=True)

    operation: Literal[PublicationOperationName.RENDER] = (
        PublicationOperationName.RENDER
    )
    destination: Path
    output_format: PublicationRenderFormat


class ArchivePublicationResult(BaseModel):
    """Describe a completed publication archive artefact."""

    model_config = ConfigDict(frozen=True)

    operation: Literal[PublicationOperationName.ARCHIVE] = (
        PublicationOperationName.ARCHIVE
    )
    location: Path


class PublishPublicationResult(BaseModel):
    """Describe a completed configured publish and optional archive artefact."""

    model_config = ConfigDict(frozen=True)

    operation: Literal[PublicationOperationName.PUBLISH] = (
        PublicationOperationName.PUBLISH
    )
    title: str
    archive_location: Path | None = None


PublicationOperationResult: TypeAlias = (
    LoadPublicationResult
    | ProcessPublicationResult
    | RenderPublicationResult
    | ArchivePublicationResult
    | PublishPublicationResult
)
PublicationOperationHandler: TypeAlias = Callable[
    [PublicationOperationRequest, PublicationOperationContext],
    PublicationOperationResult,
]


def run_load_operation(
    request: PublicationOperationRequest,
    context: PublicationOperationContext,
) -> PublicationOperationResult:
    """Execute a validated publication-loading request."""
    if not isinstance(request, LoadPublicationRequest):
        raise TypeError("The load handler requires a load request")
    context.progress.update(PublicationOperationStage.LOADING, request.publication_slug)
    result = load_publication(
        context.publication,
        context.source_folder,
        refresh_header=request.refresh_header,
    )
    return LoadPublicationResult(title=result.title)


def run_process_operation(
    request: PublicationOperationRequest,
    context: PublicationOperationContext,
) -> PublicationOperationResult:
    """Execute a validated publication-processing request."""
    if not isinstance(request, ProcessPublicationRequest):
        raise TypeError("The process handler requires a process request")
    context.progress.update(
        PublicationOperationStage.PROCESSING, request.publication_slug
    )
    result = process_publication(
        context.publication,
        context.source_folder,
        refresh_header=request.refresh_header,
        preprocess=request.preprocess,
    )
    return ProcessPublicationResult(title=result.title)


def run_render_operation(
    request: PublicationOperationRequest,
    context: PublicationOperationContext,
) -> PublicationOperationResult:
    """Execute a validated publication-rendering request."""
    if not isinstance(request, RenderPublicationRequest):
        raise TypeError("The render handler requires a render request")
    context.progress.update(
        PublicationOperationStage.RENDERING, request.output_format.value
    )
    result = render_publication(
        context.publication,
        context.publish_folder,
        request.output_format,
        refresh=request.refresh,
    )
    return RenderPublicationResult(
        destination=result.destination,
        output_format=result.format,
    )


def run_archive_operation(
    request: PublicationOperationRequest,
    context: PublicationOperationContext,
) -> PublicationOperationResult:
    """Execute a validated publication archive request."""
    if not isinstance(request, ArchivePublicationRequest):
        raise TypeError("The archive handler requires an archive request")
    context.progress.update(
        PublicationOperationStage.ARCHIVING, request.publication_slug
    )
    result = render_publication_archive(
        context.publication,
        context.source_folder,
        request.publication_slug,
        refresh=request.refresh,
    )
    return ArchivePublicationResult(location=result.location.with_suffix(".zip"))


def run_publish_operation(
    request: PublicationOperationRequest,
    context: PublicationOperationContext,
) -> PublicationOperationResult:
    """Execute the fixed configured publish workflow."""
    if not isinstance(request, PublishPublicationRequest):
        raise TypeError("The publish handler requires a publish request")
    archive_location = None
    if request.render_archive:
        context.progress.update(
            PublicationOperationStage.ARCHIVING, request.publication_slug
        )
        archive = render_publication_archive(
            context.publication,
            context.source_folder,
            request.publication_slug,
            refresh=request.refresh,
        )
        archive_location = archive.location.with_suffix(".zip")
    context.progress.update(
        PublicationOperationStage.PUBLISHING, request.publication_slug
    )
    published = run_publication_command(
        context.publication,
        context.source_folder,
        "publish",
    )
    return PublishPublicationResult(
        title=published.title,
        archive_location=archive_location,
    )


class PublicationOperationRegistry:
    """Resolve the fixed set of publication operations to typed handlers."""

    def __init__(self) -> None:
        self.handlers: dict[PublicationOperationName, PublicationOperationHandler] = {}

    def register(
        self,
        name: PublicationOperationName,
        handler: PublicationOperationHandler,
    ) -> None:
        """Register one explicitly supported operation handler."""
        if name in self.handlers:
            raise ValueError(f"Operation already registered: {name}")
        self.handlers[name] = handler

    def execute(
        self,
        request: PublicationOperationRequest,
        context: PublicationOperationContext,
    ) -> PublicationOperationResult:
        """Execute a request and report its stable lifecycle stages."""
        handler = self.handlers.get(request.operation)
        if handler is None:
            raise ValueError(f"Unsupported publication operation: {request.operation}")
        context.progress.update(
            PublicationOperationStage.STARTING, request.publication_slug
        )
        result = handler(request, context)
        context.progress.update(
            PublicationOperationStage.COMPLETE, request.publication_slug
        )
        return result


def create_publication_operation_registry() -> PublicationOperationRegistry:
    """Build the standard operation registry used by delivery interfaces."""
    registry = PublicationOperationRegistry()
    registry.register(PublicationOperationName.LOAD, run_load_operation)
    registry.register(PublicationOperationName.PROCESS, run_process_operation)
    registry.register(PublicationOperationName.RENDER, run_render_operation)
    registry.register(PublicationOperationName.ARCHIVE, run_archive_operation)
    registry.register(PublicationOperationName.PUBLISH, run_publish_operation)
    return registry


def validate_publication_operation(value: object) -> PublicationOperationRequest:
    """Validate serialized input as one supported operation request."""
    return TypeAdapter(PublicationOperationRequest).validate_python(value)


publication_operation_registry = create_publication_operation_registry()


def run_publication_operation(
    request: PublicationOperationRequest,
    publication: ManagedPublication,
    source_folder: Path,
    publish_folder: Path,
    progress: ProgressReporter | None = None,
) -> PublicationOperationResult:
    """Execute one publication operation through the standard registry."""
    context = PublicationOperationContext(
        publication=publication,
        source_folder=source_folder,
        publish_folder=publish_folder,
        progress=progress or NullProgressReporter(),
    )
    return publication_operation_registry.execute(request, context)
