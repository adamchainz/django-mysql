from django.db import models

from django_mysql.models.query import QuerySet


class Model(models.Model):
    class Meta(object):
        abstract = True

    objects = QuerySet.as_manager()
