# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-07-27 10:33


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stringprint", "0019_article_pdf_location"),
    ]

    operations = [
        migrations.AddField(
            model_name="article",
            name="display_notes",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="organisation",
            name="include_favicon",
            field=models.BooleanField(default=True),
        ),
    ]