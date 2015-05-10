"""
Contains shims that deal with changes to model fields
"""
import functools

import django
from django.utils import six

# Handle the deprecation of SubFieldBase
if django.VERSION < (1, 8):
    from django.db.models import SubfieldBase
    field_class = functools.partial(six.with_metaclass, SubfieldBase)
else:
    field_class = functools.partial(six.with_metaclass, type)
