# -*- coding:utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import json

import django
from django.core import checks
from django.db import connections
from django.db.models import Field, IntegerField, Transform
from django.utils import six

from django_mysql import forms
from django_mysql.models.lookups import (
    JSONContainedBy, JSONContains, JSONExact, JSONGreaterThan,
    JSONGreaterThanOrEqual, JSONHasAnyKeys, JSONHasKey, JSONHasKeys,
    JSONLessThan, JSONLessThanOrEqual
)
from django_mysql.utils import collapse_spaces, connection_is_mariadb

__all__ = ('JSONField',)


class JSONField(Field):
    def __init__(self, *args, **kwargs):
        if 'default' not in kwargs:
            kwargs['default'] = dict
        super(JSONField, self).__init__(*args, **kwargs)

    def check(self, **kwargs):
        errors = super(JSONField, self).check(**kwargs)
        errors.extend(self._check_default())
        errors.extend(self._check_mysql_version())

        return errors

    def _check_default(self):
        errors = []
        if isinstance(self.default, (list, dict)):
            errors.append(
                checks.Error(
                    'Do not use mutable defaults for JSONField',
                    hint=collapse_spaces('''
                        Mutable defaults get shared between all instances of
                        the field, which probably isn't what you want. You
                        should replace your default with a callable, e.g.
                        replace default={{}} with default=dict.

                        The default you passed was '{}'.
                    '''.format(self.default)),
                    obj=self,
                    id='django_mysql.E017',
                )
            )
        return errors

    def _check_mysql_version(self):
        errors = []

        any_conn_works = True
        conn_names = ['default'] + list(set(connections) - {'default'})
        for db in conn_names:
            conn = connections[db]
            if (
                hasattr(conn, 'mysql_version') and
                (connection_is_mariadb(conn) or conn.mysql_version < (5, 7))
            ):
                any_conn_works = False

        if not any_conn_works:
            errors.append(
                checks.Error(
                    "MySQL 5.7+ is required to use JSONField",
                    hint=None,
                    obj=self,
                    id='django_mysql.E016'
                )
            )
        return errors

    def deconstruct(self):
        name, path, args, kwargs = super(JSONField, self).deconstruct()
        path = 'django_mysql.models.%s' % self.__class__.__name__
        return name, path, args, kwargs

    def db_type(self, connection):
        return 'json'

    def get_transform(self, name):
        transform = super(JSONField, self).get_transform(name)
        if transform:
            return transform  # pragma: no cover
        return KeyTransformFactory(name)

    def from_db_value(self, value, expression, connection, context):
        # Similar to to_python, for Django 1.8+
        if isinstance(value, six.string_types):
            return json.loads(value, strict=False)
        return value

    def get_prep_value(self, value):
        if value is not None and not isinstance(value, six.string_types):
            # For some reason this value gets string quoted in Django's SQL
            # compiler...

            # Although json.dumps could serialize NaN, MySQL doesn't.
            return json.dumps(value, allow_nan=False)

        return value

    def get_db_prep_value(self, value, connection, prepared=False):
        if not prepared and value is not None:
            return json.dumps(value, allow_nan=False)
        return value

    def get_lookup(self, lookup_name):
        # Have to 'unregister' some incompatible lookups
        if lookup_name in {
            'range', 'in', 'iexact', 'icontains', 'startswith',
            'istartswith', 'endswith', 'iendswith', 'search', 'regex', 'iregex'
        }:
            raise NotImplementedError(
                "Lookup '{}' doesn't work with JSONField".format(lookup_name)
            )
        return super(JSONField, self).get_lookup(lookup_name)

    def value_to_string(self, obj):
        return self.value_from_object(obj)

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.JSONField}
        defaults.update(kwargs)
        return super(JSONField, self).formfield(**defaults)


class JSONLength(Transform):
    lookup_name = 'length'

    output_field = IntegerField()

    if django.VERSION[:2] < (1, 9):
        def as_sql(self, compiler, connection):
            lhs, params = compiler.compile(self.lhs)
            return 'JSON_LENGTH({})'.format(lhs), params
    else:
        function = 'JSON_LENGTH'


JSONField.register_lookup(JSONContainedBy)
JSONField.register_lookup(JSONContains)
JSONField.register_lookup(JSONExact)
JSONField.register_lookup(JSONGreaterThan)
JSONField.register_lookup(JSONGreaterThanOrEqual)
JSONField.register_lookup(JSONHasAnyKeys)
JSONField.register_lookup(JSONHasKey)
JSONField.register_lookup(JSONHasKeys)
JSONField.register_lookup(JSONLength)
JSONField.register_lookup(JSONLessThan)
JSONField.register_lookup(JSONLessThanOrEqual)


class KeyTransform(Transform):

    def __init__(self, key_name, *args, **kwargs):
        super(KeyTransform, self).__init__(*args, **kwargs)
        self.key_name = key_name

    def as_sql(self, compiler, connection):
        key_transforms = [self.key_name]
        previous = self.lhs
        while isinstance(previous, KeyTransform):
            key_transforms.insert(0, previous.key_name)
            previous = previous.lhs

        lhs, params = compiler.compile(previous)

        json_path = self.compile_json_path(key_transforms)

        return 'JSON_EXTRACT({}, %s)'.format(lhs), params + [json_path]

    def compile_json_path(self, key_transforms):
        path = ['$']
        for key_transform in key_transforms:
            try:
                num = int(key_transform)
                path.append('[{}]'.format(num))
            except ValueError:  # non-integer
                path.append('.')
                path.append(key_transform)
        return ''.join(path)


class KeyTransformFactory(object):

    def __init__(self, key_name):
        self.key_name = key_name

    def __call__(self, *args, **kwargs):
        return KeyTransform(self.key_name, *args, **kwargs)
