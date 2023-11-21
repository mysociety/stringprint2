# -*- coding: utf-8 -*-


from django.db import migrations, models
import frontend.models
import useful_inkleby.useful_django.models.mixins


class Migration(migrations.Migration):
    dependencies = [
        ("stringprint", "0013_auto_20160829_1340"),
        ("frontend", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Download",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "batch_time",
                    models.DateTimeField(null=True, editable=False, blank=True),
                ),
                (
                    "batch_id",
                    models.IntegerField(null=True, editable=False, blank=True),
                ),
                (
                    "file",
                    models.FileField(
                        null=True,
                        upload_to=frontend.models.org_download_path,
                        blank=True,
                    ),
                ),
                ("time_requested", models.DateTimeField(auto_now_add=True)),
                ("time_completed", models.DateTimeField(null=True, blank=True)),
                ("downloads", models.IntegerField(default=0)),
                (
                    "article",
                    models.ForeignKey(
                        related_name="downloads",
                        to="stringprint.Article",
                        on_delete=models.CASCADE,
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
            bases=(
                models.Model,
                useful_inkleby.useful_django.models.mixins.StockModelHelpers,
            ),
        ),
    ]
