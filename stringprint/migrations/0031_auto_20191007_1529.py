# Generated by Django 2.1 on 2019-10-07 15:29

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('stringprint', '0030_organisation_ga_cookies'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='multisection',
            name='version',
        ),
        migrations.RenameField(
            model_name='article',
            old_name='sections_over_pages',
            new_name='multipage',
        ),
        migrations.DeleteModel(
            name='MultiSection',
        ),
    ]
