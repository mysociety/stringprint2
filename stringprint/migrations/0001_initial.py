# -*- coding: utf-8 -*-


from django.db import migrations, models
from django.conf import settings
import useful_inkleby.useful_django.fields.serial
import useful_inkleby.useful_django.models.mixins


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Access',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('batch_time', models.DateTimeField(null=True, editable=False, blank=True)),
                ('batch_id', models.IntegerField(null=True, editable=False, blank=True)),
                ('email', models.EmailField(max_length=254, null=True, blank=True)),
                ('type', models.CharField(blank=True, max_length=2, null=True, choices=[(b'PA', b'Paid'), (b'FE', b'Free'), (b'CR', b'Crossover'), (b'AD', b'Admin')])),
                ('magic_word', models.CharField(max_length=255, null=True, blank=True)),
                ('views', models.IntegerField(default=0)),
                ('tokens', models.IntegerField(default=-1)),
                ('notes', models.CharField(max_length=255, null=True, blank=True)),
                ('last_access', models.DateTimeField(auto_now=True)),
                ('granted', models.DateTimeField(auto_now_add=True)),
                ('payment_ref', models.IntegerField(default=0)),
                ('disabled', models.BooleanField(default=False)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, useful_inkleby.useful_django.models.mixins.StockModelHelpers),
        ),
        migrations.CreateModel(
            name='Article',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=255, null=True, blank=True)),
                ('paywall', models.BooleanField(default=False)),
                ('short_title', models.CharField(max_length=255, null=True, blank=True)),
                ('description', models.TextField(default=b'')),
                ('byline', models.CharField(max_length=255, null=True, blank=True)),
                ('current_version', models.IntegerField(default=0, null=True)),
                ('copyright', models.TextField(max_length=255, null=True, blank=True)),
                ('authors', models.TextField(null=True)),
                ('file_source', models.CharField(max_length=255, null=True, blank=True)),
                ('slug', models.CharField(max_length=255, null=True, blank=True)),
                ('last_updated', models.DateTimeField(null=True, blank=True)),
                ('publish_date', models.DateTimeField(null=True, blank=True)),
                ('cite_as', models.CharField(max_length=255, null=True, blank=True)),
                ('seed', models.IntegerField(default=13)),
                ('book_cover', models.ImageField(null=True, upload_to=b'', blank=True)),
                ('price', models.FloatField(null=True, blank=True)),
                ('kindle_location', models.CharField(max_length=255, null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Asset',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('slug', models.CharField(max_length=255, null=True)),
                ('type', models.CharField(max_length=2, null=True, choices=[(b'h', b'html'), (b'i', b'image')])),
                ('location', models.CharField(max_length=255, null=True)),
                ('content', models.TextField(null=True)),
                ('active', models.BooleanField(default=False)),
                ('article', models.ForeignKey(related_name='assets', to='stringprint.Article', null=True,on_delete=models.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='HeaderImage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('batch_time', models.DateTimeField(null=True, editable=False, blank=True)),
                ('batch_id', models.IntegerField(null=True, editable=False, blank=True)),
                ('title_image', models.BooleanField(default=False)),
                ('section_name', models.CharField(max_length=255, null=True, blank=True)),
                ('source_loc', models.CharField(max_length=255, null=True, blank=True)),
                ('image', models.ImageField(null=True, upload_to=b'', blank=True)),
                ('image_alt', models.CharField(max_length=255, null=True, blank=True)),
                ('size', models.IntegerField(default=0)),
                ('article', models.ForeignKey(related_name='images', to='stringprint.Article',on_delete=models.CASCADE)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, useful_inkleby.useful_django.models.mixins.StockModelHelpers),
        ),
        migrations.CreateModel(
            name='IPAccess',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('batch_time', models.DateTimeField(null=True, editable=False, blank=True)),
                ('batch_id', models.IntegerField(null=True, editable=False, blank=True)),
                ('ip_address', models.GenericIPAddressField()),
                ('store_time', models.DateTimeField(auto_now=True)),
                ('access', models.ForeignKey(related_name='ips', to='stringprint.Access',on_delete=models.CASCADE)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, useful_inkleby.useful_django.models.mixins.StockModelHelpers),
        ),
        migrations.CreateModel(
            name='Organisation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, null=True, blank=True)),
                ('twitter', models.CharField(max_length=255, null=True, blank=True)),
                ('ga_code', models.CharField(max_length=255, null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='SecretWord',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('batch_time', models.DateTimeField(null=True, editable=False, blank=True)),
                ('batch_id', models.IntegerField(null=True, editable=False, blank=True)),
                ('challenge', models.CharField(max_length=255, null=True, blank=True)),
                ('answer', models.CharField(max_length=255, null=True, blank=True)),
                ('uses', models.IntegerField(default=0)),
                ('article', models.ForeignKey(related_name='secret_words', to='stringprint.Article', null=True,on_delete=models.CASCADE)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, useful_inkleby.useful_django.models.mixins.StockModelHelpers),
        ),
        migrations.CreateModel(
            name='Version',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('number', models.IntegerField()),
                ('label', models.CharField(max_length=255, null=True, blank=True)),
                ('raw', models.TextField(null=True, blank=True)),
                ('sections', useful_inkleby.useful_django.fields.serial.JsonBlockField(null=True, blank=True)),
                ('has_notes', models.BooleanField(default=False)),
                ('article', models.ForeignKey(related_name='versions', to='stringprint.Article',on_delete=models.CASCADE)),
            ],
        ),
        migrations.AddField(
            model_name='article',
            name='org',
            field=models.ForeignKey(blank=True, to='stringprint.Organisation', null=True,on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='access',
            name='article',
            field=models.ForeignKey(related_name='passes', to='stringprint.Article', null=True,on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='access',
            name='secret_word',
            field=models.ForeignKey(blank=True, to='stringprint.SecretWord', null=True,on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='access',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True,on_delete=models.CASCADE),
        ),
    ]
