"""
Contains shims that die on instantiation for classes from
django.db.models.expressions if the version of django is too old.
"""
import django

if django.VERSION >= (1, 8):
    from django.db.models.expressions import BaseExpression, Func, Value
else:
    class BaseExpression(object):
        def __init__(self, *args, **kwargs):
            raise ValueError("Database Expessions only exist in Django 1.8+")

    class Func(object):
        def __init__(self, *args, **kwargs):
            raise ValueError("Database Functions only exist in Django 1.8+")

    Value = tuple


__all__ = ('BaseExpression', 'Value', 'Func')
