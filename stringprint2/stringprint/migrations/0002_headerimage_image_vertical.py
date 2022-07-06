# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stringprint", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="headerimage",
            name="image_vertical",
            field=models.ImageField(null=True, upload_to=b"", blank=True),
        ),
    ]
