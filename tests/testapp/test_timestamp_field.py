# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from django.test import TestCase

from django_mysql.models import TimestampField


class TimestampFieldTests(TestCase):

    def test_to_python(self):
        field = TimestampField()
        assert field.to_python(0) == datetime(1970, 1, 1, 0, 0, 0)
        assert field.to_python(10) == datetime(1970, 1, 1, 0, 0, 10)
        assert field.to_python(1433785089) == datetime(2015, 6, 8, 17, 38, 9)
