"""Safe access to bounded publication operation logs."""

from __future__ import annotations

from pathlib import Path

from django.conf import settings

from publication_management.models import PublicationOperation


def read_recent_operation_log(operation: PublicationOperation) -> str:
    """Read bounded output only from the configured operation log root."""
    if not operation.log_path:
        return ""
    log_root = (Path(settings.MEDIA_ROOT) / "operation_logs").resolve()
    log_path = Path(operation.log_path).resolve()
    if not log_path.is_relative_to(log_root):
        return "Log file is unavailable."
    try:
        with log_path.open(encoding="utf-8") as log:
            return "\n".join(log.read().splitlines()[-200:])
    except OSError:
        return "Log file is unavailable."
