# -*- coding: utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from django.db import migrations, models

from django_mysql.models import ListCharField


class Migration(migrations.Migration):

    dependencies = [
        ('testapp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='intlistdefaultmodel',
            name='field_2',
            field=ListCharField(models.IntegerField(),
                                default=lambda: [],
                                size=None,
                                max_length=32),
        ),
        migrations.AddField(
            model_name='intlistdefaultmodel',
            name='field_3',
            field=ListCharField(models.IntegerField(),
                                default=lambda: [1, 5],
                                size=None,
                                max_length=32),
        ),
    ]
