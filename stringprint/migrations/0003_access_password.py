# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stringprint', '0002_headerimage_image_vertical'),
    ]

    operations = [
        migrations.AddField(
            model_name='access',
            name='password',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
    ]
