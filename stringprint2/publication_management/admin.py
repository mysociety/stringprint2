"""Django admin diagnostics for publication operations and workers."""

from django.contrib import admin

from .models import PublicationOperation, PublicationWorker


@admin.register(PublicationOperation)
class PublicationOperationAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Expose operation state and ownership for operational diagnosis."""

    list_display = (
        "id",
        "publication_slug",
        "operation_name",
        "state",
        "stage",
        "requested_by",
        "created_at",
        "finished_at",
    )
    list_filter = ("state", "operation_name", "request_source")
    search_fields = ("publication_slug", "worker_id", "error_summary")
    readonly_fields = (
        "created_at",
        "started_at",
        "heartbeat_at",
        "finished_at",
        "parameters",
        "result",
    )


@admin.register(PublicationWorker)
class PublicationWorkerAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Expose worker heartbeat and shutdown state for diagnosis."""

    list_display = (
        "worker_id",
        "hostname",
        "process_id",
        "state",
        "started_at",
        "heartbeat_at",
        "stopped_at",
    )
    list_filter = ("state",)
    readonly_fields = (
        "worker_id",
        "hostname",
        "process_id",
        "state",
        "started_at",
        "heartbeat_at",
        "stopped_at",
    )
