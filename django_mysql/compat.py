"""
Helpers that deal with the changes in Django over time, by either working
before and after the change, or just failing at usage time rather than import
time.
"""
import functools

import django
from django.utils import six

__all__ = ('BaseExpression', 'Func', 'Value', 'field_class',
           'add_raw_condition')


# Handle the deprecation of SubfieldBase
# `field_class(base1, base2, ...) should be used in place of
# six.with_metaclass(SubFieldBase, base1, base2, ...)

if django.VERSION < (1, 8):
    from django.db.models import SubfieldBase
    field_class = functools.partial(six.with_metaclass, SubfieldBase)
else:
    field_class = functools.partial(six.with_metaclass, type)


# Expressions only exist in Django 1.8+
# Handle this by providing a classes that mimic the API but die on
# instantiation

if django.VERSION < (1, 8):
    class BaseExpression(object):
        def __init__(self, *args, **kwargs):
            raise ValueError("Database Expessions only exist in Django 1.8+")

    class Func(object):
        def __init__(self, *args, **kwargs):
            raise ValueError("Database Functions only exist in Django 1.8+")

    Value = tuple
else:
    from django.db.models.expressions import BaseExpression, Func, Value


# QuerySet.extra is ugly and deprecated, maybe there is a way of replacing it
# with an Expression in Django 1.8+.. experimenting but not finding anything...

if django.VERSION < (1, 8):

    def add_raw_condition(queryset, condition):
        return queryset.extra(where=[condition])

else:

    from django.db.models.expressions import RawSQL

    def add_raw_condition(queryset, condition):
        return queryset.filter(RawSQL(condition, ()))
