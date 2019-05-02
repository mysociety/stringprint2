# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stringprint', '0005_auto_20160802_1028'),
    ]

    operations = [
        migrations.AddField(
            model_name='asset',
            name='alt_text',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
    ]
