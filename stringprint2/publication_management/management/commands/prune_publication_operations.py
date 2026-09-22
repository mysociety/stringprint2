"""Prune old terminal publication operations and their owned logs."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser
from django.utils import timezone

from ...retention import prune_publication_operations


class Command(BaseCommand):
    """Apply the bounded publication operation retention policy."""

    help = "Prune old terminal publication operations and their logs"

    def add_arguments(self, parser: CommandParser) -> None:
        """Configure age and dry-run behaviour."""
        parser.add_argument("--older-than-days", type=int, default=90)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: object, **options: Any) -> None:
        """Select and optionally delete expired operation history."""
        days = options["older_than_days"]
        if days < 1:
            raise ValueError("older-than-days must be at least 1")
        result = prune_publication_operations(
            timezone.now() - timedelta(days=days),
            Path(settings.MEDIA_ROOT) / "operation_logs",
            dry_run=options["dry_run"],
        )
        action = "Would prune" if result.dry_run else "Pruned"
        self.stdout.write(
            f"{action} {len(result.operation_ids)} operation(s) and "
            f"{len(result.log_paths)} log(s)"
        )
