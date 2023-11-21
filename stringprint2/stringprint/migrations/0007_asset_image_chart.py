# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("stringprint", "0006_asset_alt_text"),
    ]

    operations = [
        migrations.AddField(
            model_name="asset",
            name="image_chart",
            field=models.ImageField(null=True, upload_to=b"", blank=True),
        ),
    ]
