"""Create durable publication operations."""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """Create the initial publication-management schema."""

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("stringprint", "0044_alter_article_commands_alter_article_extra_values_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="PublicationOperation",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("publication_slug", models.CharField(max_length=255)),
                ("operation_name", models.CharField(max_length=64)),
                ("schema_version", models.PositiveSmallIntegerField(default=1)),
                ("parameters", models.JSONField(default=dict)),
                ("state", models.CharField(choices=[("pending", "Pending"), ("running", "Running"), ("succeeded", "Succeeded"), ("failed", "Failed"), ("cancel_requested", "Cancellation requested"), ("cancelled", "Cancelled"), ("interrupted", "Interrupted")], db_index=True, default="pending", max_length=32)),
                ("stage", models.CharField(blank=True, max_length=64)),
                ("progress_detail", models.TextField(blank=True)),
                ("request_source", models.CharField(default="web", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("heartbeat_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("worker_id", models.CharField(blank=True, max_length=255)),
                ("process_id", models.PositiveIntegerField(blank=True, null=True)),
                ("error_summary", models.TextField(blank=True)),
                ("log_path", models.CharField(blank=True, max_length=1024)),
                ("result", models.JSONField(blank=True, null=True)),
                ("article", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="publication_operations", to="stringprint.article")),
                ("organisation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="publication_operations", to="stringprint.organisation")),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="publication_operations", to=settings.AUTH_USER_MODEL)),
                ("retry_of", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="retries", to="publication_management.publicationoperation")),
            ],
            options={
                "ordering": ("-created_at", "-pk"),
                "indexes": [models.Index(fields=["state", "created_at"], name="publication_state_created_idx")],
            },
        ),
    ]
