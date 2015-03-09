# -*- coding:utf-8 -*-
# -*- coding:utf-8 -*-
from __future__ import print_function

from django.core.management import call_command
from django.test import TestCase
from django.utils import six
from django.utils.six.moves import StringIO


class DBParamsTests(TestCase):

    def test_simple(self):
        out = StringIO()
        call_command('dbparams', 'default', stdout=out)
        output = out.getvalue()
        self.assertTrue(isinstance(output, six.string_types))
