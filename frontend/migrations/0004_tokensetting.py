# -*- coding: utf-8 -*-


from django.db import migrations, models
import useful_inkleby.useful_django.models.mixins


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0003_usersettings_tokens'),
    ]

    operations = [
        migrations.CreateModel(
            name='TokenSetting',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('batch_time', models.DateTimeField(null=True, editable=False, blank=True)),
                ('batch_id', models.IntegerField(null=True, editable=False, blank=True)),
                ('token_amount', models.IntegerField(default=0)),
                ('price', models.FloatField(default=0)),
                ('uses', models.IntegerField(default=0)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, useful_inkleby.useful_django.models.mixins.StockModelHelpers),
        ),
    ]
