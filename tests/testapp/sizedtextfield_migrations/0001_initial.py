# -*- coding: utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals,
)

from django.db import migrations, models

from django_mysql.models import SizedTextField


class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='SizedTextAlterModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False,
                 auto_created=True, primary_key=True)),
                ('field', SizedTextField(size_class=3)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
