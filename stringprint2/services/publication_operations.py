"""Typed publication operations shared by command-line and web delivery."""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal, NamedTuple, Protocol, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from stringprint2.services.publication_rendering import (
    PublicationRenderFormat,
    RenderablePublication,
    render_publication,
)
from stringprint2.services.publication_workflow import (
    PublicationDocument,
    process_publication,
)


class PublicationOperationName(StrEnum):
    """Identify an operation that delivery interfaces may execute."""

    PROCESS = "process"
    RENDER = "render"


class PublicationOperationStage(StrEnum):
    """Describe stable, user-facing stages of an operation."""

    STARTING = "starting"
    PROCESSING = "processing"
    RENDERING = "rendering"
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


PublicationOperationRequest: TypeAlias = Annotated[
    ProcessPublicationRequest | RenderPublicationRequest,
    Field(discriminator="operation"),
]


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


PublicationOperationResult: TypeAlias = (
    ProcessPublicationResult | RenderPublicationResult
)
PublicationOperationHandler: TypeAlias = Callable[
    [PublicationOperationRequest, PublicationOperationContext],
    PublicationOperationResult,
]


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
    registry.register(PublicationOperationName.PROCESS, run_process_operation)
    registry.register(PublicationOperationName.RENDER, run_render_operation)
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
