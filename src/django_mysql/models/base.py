from django.db import models

from django_mysql.models.query import QuerySet


class Model(models.Model):
    class Meta:
        abstract = True

    objects = QuerySet.as_manager()
