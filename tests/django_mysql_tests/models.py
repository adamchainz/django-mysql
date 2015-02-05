# -*- coding:utf-8 -*-
from django.db import models

from django_mysql.fields import SetCharField


class Settee(models.Model):
    features = SetCharField(max_length=32)
