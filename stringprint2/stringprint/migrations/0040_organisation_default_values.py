# Generated by Django 2.1 on 2020-07-27 09:29

from django.db import migrations
import useful_inkleby.useful_django.fields.serial


class Migration(migrations.Migration):
    dependencies = [
        ("stringprint", "0039_auto_20200727_0838"),
    ]

    operations = [
        migrations.AddField(
            model_name="organisation",
            name="default_values",
            field=useful_inkleby.useful_django.fields.serial.JsonBlockField(default={}),
        ),
    ]
