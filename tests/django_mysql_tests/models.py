# -*- coding:utf-8 -*-
from django.db.models import CharField, Model

from django_mysql.fields import SetCharField


class Settee(Model):
    features = SetCharField(max_length=32)


class Author(Model):
    name = CharField(max_length=32)
