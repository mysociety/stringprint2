# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stringprint', '0008_auto_20160804_1141'),
    ]

    operations = [
        migrations.AlterField(
            model_name='multisection',
            name='version',
            field=models.ForeignKey(related_name='multi_section', to='stringprint.Version',on_delete=models.CASCADE),
        ),
    ]
