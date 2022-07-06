# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stringprint", "0017_article_publish_tokens"),
    ]

    operations = [
        migrations.AddField(
            model_name="organisation",
            name="custom_css",
            field=models.TextField(default=b""),
        ),
        migrations.AddField(
            model_name="organisation",
            name="fonts",
            field=models.TextField(default=b""),
        ),
    ]
