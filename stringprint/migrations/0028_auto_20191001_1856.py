# Generated by Django 2.1 on 2019-10-01 18:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stringprint", "0027_auto_20190502_1009"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="organisation",
            name="custom_css",
        ),
        migrations.AddField(
            model_name="organisation",
            name="screenshot_stylesheet",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
