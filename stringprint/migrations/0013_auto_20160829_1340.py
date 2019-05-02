# -*- coding: utf-8 -*-


from django.db import migrations, models
import stringprint.models


class Migration(migrations.Migration):

    dependencies = [
        ('stringprint', '0012_auto_20160822_1553'),
    ]

    operations = [
        migrations.AddField(
            model_name='article',
            name='needs_processing',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='article',
            name='production_url',
            field=models.URLField(default=b''),
        ),
        migrations.AddField(
            model_name='article',
            name='reprocess_source',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='article',
            name='source_file',
            field=models.FileField(null=True, upload_to=stringprint.models.org_source_path, blank=True),
        ),
        migrations.AddField(
            model_name='asset',
            name='regenerate_image_chart',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='headerimage',
            name='queue_responsive',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='headerimage',
            name='queue_tiny',
            field=models.BooleanField(default=False),
        ),
    ]
