# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

import django_mysql.fields


class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='IntSetDefaultModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False,
                 auto_created=True, primary_key=True)),
                ('field', django_mysql.fields.SetCharField(
                    models.IntegerField(), size=None, max_length=32)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
