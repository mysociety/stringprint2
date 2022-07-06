# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stringprint", "0011_asset_caption"),
    ]

    operations = [
        migrations.AddField(
            model_name="asset",
            name="batch_id",
            field=models.IntegerField(null=True, editable=False, blank=True),
        ),
        migrations.AddField(
            model_name="asset",
            name="batch_time",
            field=models.DateTimeField(null=True, editable=False, blank=True),
        ),
    ]
