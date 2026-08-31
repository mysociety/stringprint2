"""Persistence models for durable publication operations."""

from __future__ import annotations

from django.conf import settings
from django.db import models


class PublicationOperationState(models.TextChoices):
    """Represent the durable lifecycle of a publication operation."""

    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    CANCEL_REQUESTED = "cancel_requested", "Cancellation requested"
    CANCELLED = "cancelled", "Cancelled"
    INTERRUPTED = "interrupted", "Interrupted"


class PublicationWorkerState(models.TextChoices):
    """Represent whether a registered worker expects to consume operations."""

    ACTIVE = "active", "Active"
    STOPPED = "stopped", "Stopped"


class PublicationWorker(models.Model):
    """Record worker liveness independently of queued operation state."""

    worker_id = models.CharField(max_length=255, primary_key=True)
    hostname = models.CharField(max_length=255)
    process_id = models.PositiveIntegerField()
    state = models.CharField(
        max_length=16,
        choices=PublicationWorkerState.choices,
        default=PublicationWorkerState.ACTIVE,
        db_index=True,
    )
    started_at = models.DateTimeField()
    heartbeat_at = models.DateTimeField(db_index=True)
    stopped_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        """Show worker identity and liveness state in diagnostics."""
        return f"{self.worker_id} ({self.state})"


class PublicationOperation(models.Model):
    """Record a typed publication operation independently of its worker."""

    organisation = models.ForeignKey(
        "stringprint.Organisation",
        related_name="publication_operations",
        on_delete=models.CASCADE,
    )
    article = models.ForeignKey(
        "stringprint.Article",
        related_name="publication_operations",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    publication_slug = models.CharField(max_length=255)
    operation_name = models.CharField(max_length=64)
    schema_version = models.PositiveSmallIntegerField(default=1)
    parameters = models.JSONField(default=dict)
    state = models.CharField(
        max_length=32,
        choices=PublicationOperationState.choices,
        default=PublicationOperationState.PENDING,
        db_index=True,
    )
    stage = models.CharField(max_length=64, blank=True)
    progress_detail = models.TextField(blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="publication_operations",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    request_source = models.CharField(max_length=32, default="web")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    heartbeat_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    worker_id = models.CharField(max_length=255, blank=True)
    process_id = models.PositiveIntegerField(null=True, blank=True)
    error_summary = models.TextField(blank=True)
    log_path = models.CharField(max_length=1024, blank=True)
    result = models.JSONField(null=True, blank=True)
    retry_of = models.ForeignKey(
        "self",
        related_name="retries",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        """Order recent operations first and accelerate worker claims."""

        ordering = ("-created_at", "-pk")
        indexes = [
            models.Index(
                fields=("state", "created_at"),
                name="publication_state_created_idx",
            )
        ]

    def __str__(self) -> str:
        """Show the operation and publication in diagnostics."""
        return f"{self.operation_name}: {self.publication_slug} ({self.state})"
