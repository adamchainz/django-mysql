# -*- coding: utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from django.db import migrations

from django_mysql.models import EnumField


class Migration(migrations.Migration):

    dependencies = [
        ('testapp', '0002_add_some_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='EnumDefaultModel',
            name='field',
            field=EnumField(choices=[
                ('lion', 'Lion'), ('tiger', 'Tiger'), 'oh my!'
            ])
        ),
    ]
