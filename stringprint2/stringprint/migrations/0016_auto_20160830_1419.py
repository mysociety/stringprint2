# -*- coding: utf-8 -*-


from django.db import migrations, models
import stringprint.models


class Migration(migrations.Migration):
    dependencies = [
        ("stringprint", "0015_organisation_publish_root"),
    ]

    operations = [
        migrations.AlterField(
            model_name="article",
            name="book_cover",
            field=models.ImageField(
                null=True,
                upload_to=stringprint.models.kindle_source_storage,
                blank=True,
            ),
        ),
    ]
