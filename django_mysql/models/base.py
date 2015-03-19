# -*- coding:utf-8 -*-
from django.db import models

from django_mysql.models.handler import Handler
from django_mysql.models.query import QuerySet


_BaseManager = models.Manager.from_queryset(QuerySet)


class Manager(_BaseManager):
    def handler(self):
        return Handler(self)


class Model(models.Model):
    class Meta(object):
        abstract = True

    objects = Manager()
