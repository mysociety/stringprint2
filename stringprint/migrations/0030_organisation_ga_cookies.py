# Generated by Django 2.1 on 2019-10-03 20:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stringprint', '0029_version_paragraph_links'),
    ]

    operations = [
        migrations.AddField(
            model_name='organisation',
            name='ga_cookies',
            field=models.BooleanField(default=True),
        ),
    ]
