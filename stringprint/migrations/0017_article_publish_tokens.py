# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stringprint', '0016_auto_20160830_1419'),
    ]

    operations = [
        migrations.AddField(
            model_name='article',
            name='publish_tokens',
            field=models.IntegerField(default=0),
        ),
    ]
