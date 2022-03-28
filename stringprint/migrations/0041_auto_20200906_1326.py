# Generated by Django 2.1 on 2020-09-06 13:26

from django.db import migrations
import useful_inkleby.useful_django.fields.serial


class Migration(migrations.Migration):

    dependencies = [
        ("stringprint", "0040_organisation_default_values"),
    ]

    operations = [
        migrations.AddField(
            model_name="asset",
            name="extra_values",
            field=useful_inkleby.useful_django.fields.serial.JsonBlockField(default={}),
        ),
        migrations.AddField(
            model_name="headerimage",
            name="extra_values",
            field=useful_inkleby.useful_django.fields.serial.JsonBlockField(default={}),
        ),
    ]
