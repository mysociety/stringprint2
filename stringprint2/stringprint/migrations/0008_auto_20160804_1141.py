# -*- coding: utf-8 -*-


from django.db import migrations, models
import stringprint2.serialization


class Migration(migrations.Migration):
    dependencies = [
        ("stringprint", "0007_asset_image_chart"),
    ]

    operations = [
        migrations.CreateModel(
            name="MultiSection",
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
                ("order", models.IntegerField(default=0)),
                ("anchor", models.CharField(max_length=255)),
                (
                    "section",
                    stringprint2.serialization.JsonBlockField(
                        null=True, blank=True
                    ),
                ),
                (
                    "grafs",
                    stringprint2.serialization.JsonBlockField(
                        null=True, blank=True
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="article",
            name="sections_over_pages",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="multisection",
            name="version",
            field=models.ForeignKey(
                related_name="multi_section",
                to="stringprint.Article",
                on_delete=models.CASCADE,
            ),
        ),
    ]
