# Generated by Django 2.1 on 2019-12-02 19:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stringprint", "0032_article_include_citation"),
    ]

    operations = [
        migrations.AddField(
            model_name="asset",
            name="size",
            field=models.IntegerField(default=0),
        ),
    ]
