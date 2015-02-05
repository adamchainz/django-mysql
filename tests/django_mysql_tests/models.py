# -*- coding:utf-8 -*-
from django.db import models


class MyModel(models.Model):
    name = models.CharField(max_length=32)
