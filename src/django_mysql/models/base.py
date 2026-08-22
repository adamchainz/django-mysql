from __future__ import annotations

from django.db import models

from django_mysql.models.query import QuerySet

Manager = models.Manager.from_queryset(QuerySet)


class Model(models.Model):
    class Meta:
        abstract = True

    objects = Manager()
