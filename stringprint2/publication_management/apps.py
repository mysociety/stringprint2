"""Django application configuration for publication management."""

from django.apps import AppConfig


class PublicationManagementConfig(AppConfig):
    """Configure durable publication operation persistence."""

    default_auto_field = "django.db.models.AutoField"
    name = "publication_management"
