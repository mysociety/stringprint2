# Generated by Django 2.1 on 2019-10-08 12:21

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("stringprint", "0031_auto_20191007_1529"),
    ]

    operations = [
        migrations.AddField(
            model_name="article",
            name="include_citation",
            field=models.BooleanField(default=False),
        ),
    ]
