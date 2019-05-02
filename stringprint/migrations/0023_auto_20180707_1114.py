# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-07-07 10:14


from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stringprint', '0022_auto_20180615_1527'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrgLinks',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('link', models.URLField(max_length=255)),
                ('order', models.IntegerField(default=0)),
            ],
        ),
        migrations.AddField(
            model_name='organisation',
            name='icon',
            field=models.ImageField(blank=True, null=True, upload_to=b''),
        ),
        migrations.AddField(
            model_name='organisation',
            name='stylesheet',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='orglinks',
            name='org',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='org_links', to='stringprint.Organisation'),
        ),
    ]
