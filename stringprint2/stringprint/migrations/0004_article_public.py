# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("stringprint", "0003_access_password"),
    ]

    operations = [
        migrations.AddField(
            model_name="article",
            name="public",
            field=models.BooleanField(default=False),
        ),
    ]
