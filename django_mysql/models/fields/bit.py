# -*- coding:utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals,
)

import django
from django.db.models import BooleanField, NullBooleanField
from django.utils import six


class Bit1Mixin(object):
    def db_type(self, connection):
        return 'bit(1)'

    if django.VERSION >= (2, 0):
        def from_db_value(self, value, expression, connection):
            # Meant to be binary/bytes but can come back as unicode strings
            if isinstance(value, six.binary_type):
                value = (value == b'\x01')
            elif isinstance(value, six.text_type):
                # Only on older versions of mysqlclient and Py 2.7
                value = (value == '\x01')  # pragma: no cover
            return value
    else:
        def from_db_value(self, value, expression, connection, context):
            # Meant to be binary/bytes but can come back as unicode strings
            if isinstance(value, six.binary_type):
                value = (value == b'\x01')
            elif isinstance(value, six.text_type):
                # Only on older versions of mysqlclient and Py 2.7
                value = (value == '\x01')  # pragma: no cover
            return value

    def get_prep_value(self, value):
        if value is None:
            return value
        else:
            return 1 if value else 0


class Bit1BooleanField(Bit1Mixin, BooleanField):
    pass


class NullBit1BooleanField(Bit1Mixin, NullBooleanField):
    pass
