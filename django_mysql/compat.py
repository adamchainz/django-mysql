"""
Helpers that deal with the changes in Django over time, by either working
before and after the change, or just failing at usage time rather than import
time.
"""
import functools

import django
from django.utils import six

__all__ = ('BaseExpression', 'Func', 'Value', 'field_class')


# Handle the deprecation of SubfieldBase
# `field_class(base1, base2, ...) should be used in place of
# six.with_metaclass(SubFieldBase, base1, base2, ...)

if django.VERSION[:2] < (1, 8):
    from django.db.models import SubfieldBase
    field_class = functools.partial(six.with_metaclass, SubfieldBase)
else:
    field_class = functools.partial(six.with_metaclass, type)


# Expressions only exist in Django 1.8+
# Handle this by providing a classes that mimic the API but die on
# instantiation

if django.VERSION[:2] < (1, 8):
    class BaseExpression(object):
        def __init__(self, *args, **kwargs):
            raise ValueError("Database Expessions only exist in Django 1.8+")

    class Func(object):
        def __init__(self, *args, **kwargs):
            raise ValueError("Database Functions only exist in Django 1.8+")

    Value = tuple
else:
    from django.db.models.expressions import BaseExpression, Func, Value
