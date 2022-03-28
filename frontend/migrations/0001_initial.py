# -*- coding: utf-8 -*-


from django.db import migrations, models
from django.conf import settings
import useful_inkleby.useful_django.models.mixins


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("stringprint", "0012_auto_20160822_1553"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserSettings",
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
                    "org",
                    models.ForeignKey(
                        related_name="user_settings",
                        to="stringprint.Organisation",
                        on_delete=models.CASCADE,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        related_name="settings",
                        to=settings.AUTH_USER_MODEL,
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
