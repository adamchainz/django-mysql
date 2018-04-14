# -*- coding: utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals,
)

from django.db import migrations, models

from django_mysql.models import ListCharField


class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='IntListDefaultModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False,
                 auto_created=True, primary_key=True)),
                ('field', ListCharField(
                    models.IntegerField(), size=None, max_length=32)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
