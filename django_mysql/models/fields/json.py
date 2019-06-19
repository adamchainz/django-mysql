import json

import django
from django.core import checks
from django.db.models import Field, IntegerField, Transform

from django_mysql import forms
from django_mysql.checks import mysql_connections
from django_mysql.models.lookups import (
    JSONContainedBy,
    JSONContains,
    JSONExact,
    JSONGreaterThan,
    JSONGreaterThanOrEqual,
    JSONHasAnyKeys,
    JSONHasKey,
    JSONHasKeys,
    JSONLessThan,
    JSONLessThanOrEqual,
)
from django_mysql.utils import collapse_spaces, connection_is_mariadb

__all__ = ("JSONField",)


class JSONField(Field):

    _default_json_encoder = json.JSONEncoder(allow_nan=False)
    _default_json_decoder = json.JSONDecoder(strict=False)

    def __init__(self, *args, **kwargs):
        if "default" not in kwargs:
            kwargs["default"] = dict
        self.json_encoder = kwargs.pop("encoder", self._default_json_encoder)
        self.json_decoder = kwargs.pop("decoder", self._default_json_decoder)
        super(JSONField, self).__init__(*args, **kwargs)

    def check(self, **kwargs):
        errors = super(JSONField, self).check(**kwargs)
        errors.extend(self._check_default())
        errors.extend(self._check_mysql_version())
        errors.extend(self._check_json_encoder_decoder())
        return errors

    def _check_default(self):
        errors = []
        if isinstance(self.default, (list, dict)):
            errors.append(
                checks.Error(
                    "Do not use mutable defaults for JSONField",
                    hint=collapse_spaces(
                        """
                        Mutable defaults get shared between all instances of
                        the field, which probably isn't what you want. You
                        should replace your default with a callable, e.g.
                        replace default={{}} with default=dict.

                        The default you passed was '{}'.
                    """.format(
                            self.default
                        )
                    ),
                    obj=self,
                    id="django_mysql.E017",
                )
            )
        return errors

    def _check_mysql_version(self):
        errors = []

        any_conn_works = False
        for _alias, conn in mysql_connections():
            if (
                hasattr(conn, "mysql_version")
                and not connection_is_mariadb(conn)
                and conn.mysql_version >= (5, 7)
            ):
                any_conn_works = True

        if not any_conn_works:
            errors.append(
                checks.Error(
                    "MySQL 5.7+ is required to use JSONField",
                    hint="At least one of your DB connections should be to "
                    "MySQL 5.7+",
                    obj=self,
                    id="django_mysql.E016",
                )
            )
        return errors

    def _check_json_encoder_decoder(self):
        errors = []

        if self.json_encoder.allow_nan:
            errors.append(
                checks.Error(
                    "Custom JSON encoder should have allow_nan=False as MySQL "
                    "does not support NaN/Infinity in JSON.",
                    obj=self,
                    id="django_mysql.E018",
                )
            )

        if self.json_decoder.strict:
            errors.append(
                checks.Error(
                    "Custom JSON decoder should have strict=False to support "
                    "all the characters that MySQL does.",
                    obj=self,
                    id="django_mysql.E019",
                )
            )

        return errors

    def deconstruct(self):
        name, path, args, kwargs = super(JSONField, self).deconstruct()

        bad_paths = (
            "django_mysql.models.fields.json.JSONField",
            "django_mysql.models.fields.JSONField",
        )
        if path in bad_paths:
            path = "django_mysql.models.JSONField"

        return name, path, args, kwargs

    def db_type(self, connection):
        return "json"

    def get_transform(self, name):
        transform = super(JSONField, self).get_transform(name)
        if transform:
            return transform  # pragma: no cover
        return KeyTransformFactory(name)

    if django.VERSION >= (2, 0):

        def from_db_value(self, value, expression, connection):
            if isinstance(value, str):
                return self.json_decoder.decode(value)
            return value

    else:

        def from_db_value(self, value, expression, connection, context):
            if isinstance(value, str):
                return self.json_decoder.decode(value)
            return value

    def get_prep_value(self, value):
        if value is not None and not isinstance(value, str):
            # For some reason this value gets string quoted in Django's SQL
            # compiler...
            return self.json_encoder.encode(value)

        return value

    def get_db_prep_value(self, value, connection, prepared=False):
        if not prepared and value is not None:
            return self.json_encoder.encode(value)
        return value

    def get_lookup(self, lookup_name):
        # Have to 'unregister' some incompatible lookups
        if lookup_name in {
            "range",
            "in",
            "iexact",
            "icontains",
            "startswith",
            "istartswith",
            "endswith",
            "iendswith",
            "search",
            "regex",
            "iregex",
        }:
            raise NotImplementedError(
                "Lookup '{}' doesn't work with JSONField".format(lookup_name)
            )
        return super(JSONField, self).get_lookup(lookup_name)

    def value_to_string(self, obj):
        return self.value_from_object(obj)

    def formfield(self, **kwargs):
        defaults = {"form_class": forms.JSONField}
        defaults.update(kwargs)
        return super(JSONField, self).formfield(**defaults)


class JSONLength(Transform):
    lookup_name = "length"

    output_field = IntegerField()

    function = "JSON_LENGTH"


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

        return "JSON_EXTRACT({}, %s)".format(lhs), tuple(params) + (json_path,)

    def compile_json_path(self, key_transforms):
        path = ["$"]
        for key_transform in key_transforms:
            try:
                num = int(key_transform)
                path.append("[{}]".format(num))
            except ValueError:  # non-integer
                path.append(".")
                path.append(key_transform)
        return "".join(path)


class KeyTransformFactory(object):
    def __init__(self, key_name):
        self.key_name = key_name

    def __call__(self, *args, **kwargs):
        return KeyTransform(self.key_name, *args, **kwargs)
