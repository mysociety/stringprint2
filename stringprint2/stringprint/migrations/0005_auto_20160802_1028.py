# -*- coding: utf-8 -*-


from django.db import migrations, models
import charts.fields


class Migration(migrations.Migration):

    dependencies = [
        ("stringprint", "0004_article_public"),
    ]

    operations = [
        migrations.AddField(
            model_name="asset",
            name="chart",
            field=charts.fields.ChartField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="asset",
            name="code_content",
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name="asset",
            name="image",
            field=models.ImageField(null=True, upload_to=b"", blank=True),
        ),
        migrations.AlterField(
            model_name="asset",
            name="type",
            field=models.CharField(
                max_length=2,
                null=True,
                choices=[(b"h", b"html"), (b"i", b"image"), (b"c", b"chart")],
            ),
        ),
    ]
