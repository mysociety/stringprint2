# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stringprint", "0010_article_first_section_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="asset",
            name="caption",
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
    ]
