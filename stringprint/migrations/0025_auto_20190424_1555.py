# Generated by Django 2.1 on 2019-04-24 14:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stringprint', '0024_auto_20190322_1324'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='article',
            name='price',
        ),
        migrations.RemoveField(
            model_name='article',
            name='publish_tokens',
        ),
        migrations.AddField(
            model_name='organisation',
            name='publish_dir',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='organisation',
            name='slug',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='organisation',
            name='storage_dir',
            field=models.TextField(blank=True, default=''),
        ),
    ]
