# Generated by Django 2.1 on 2019-10-03 16:26

from django.db import migrations
import useful_inkleby.useful_django.fields.serial


class Migration(migrations.Migration):

    dependencies = [
        ('stringprint', '0028_auto_20191001_1856'),
    ]

    operations = [
        migrations.AddField(
            model_name='version',
            name='paragraph_links',
            field=useful_inkleby.useful_django.fields.serial.JsonBlockField(blank=True, null=True),
        ),
    ]
