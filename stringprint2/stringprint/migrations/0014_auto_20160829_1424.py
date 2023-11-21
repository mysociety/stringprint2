# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("stringprint", "0013_auto_20160829_1340"),
    ]

    operations = [
        migrations.AlterField(
            model_name="article",
            name="publish_date",
            field=models.DateField(null=True, blank=True),
        ),
    ]
