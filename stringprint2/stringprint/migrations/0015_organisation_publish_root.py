# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("stringprint", "0014_auto_20160829_1424"),
    ]

    operations = [
        migrations.AddField(
            model_name="organisation",
            name="publish_root",
            field=models.URLField(max_length=255, null=True, blank=True),
        ),
    ]
