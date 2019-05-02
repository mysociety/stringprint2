# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stringprint', '0009_auto_20160804_1154'),
    ]

    operations = [
        migrations.AddField(
            model_name='article',
            name='first_section_name',
            field=models.CharField(default=b'start', max_length=255, blank=True),
        ),
    ]
