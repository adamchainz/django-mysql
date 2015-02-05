# -*- coding:utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from django.test import TestCase

from django_mysql_tests.models import MyModel


class SimpleTests(TestCase):

    def test_simple(self):
        MyModel.objects.create()
