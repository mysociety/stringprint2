# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("frontend", "0002_download"),
    ]

    operations = [
        migrations.AddField(
            model_name="usersettings",
            name="tokens",
            field=models.IntegerField(default=0),
        ),
    ]
