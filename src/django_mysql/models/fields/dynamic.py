import json
from datetime import date, datetime, time

import django
from django.core import checks
from django.db.models import (
    DateField,
    DateTimeField,
    Field,
    FloatField,
    IntegerField,
    TextField,
    TimeField,
    Transform,
)
from django.utils.translation import ugettext_lazy as _

from django_mysql.checks import mysql_connections
from django_mysql.models.lookups import DynColHasKey
from django_mysql.utils import connection_is_mariadb

try:
    import mariadb_dyncol
except ImportError:  # pragma: no cover
    mariadb_dyncol = None


class DynamicField(Field):
    empty_strings_allowed = False
    description = _("Mapping")

    def __init__(self, *args, **kwargs):
        if "default" not in kwargs:
            kwargs["default"] = dict
        if "blank" not in kwargs:
            kwargs["blank"] = True
        self.spec = kwargs.pop("spec", {})
        super(DynamicField, self).__init__(*args, **kwargs)

    def check(self, **kwargs):
        errors = super(DynamicField, self).check(**kwargs)
        errors.extend(self._check_mariadb_dyncol())
        errors.extend(self._check_mariadb_version())
        errors.extend(self._check_character_set())
        errors.extend(self._check_spec_recursively(self.spec))
        return errors

    def _check_mariadb_dyncol(self):
        errors = []
        if mariadb_dyncol is None:
            errors.append(
                checks.Error(
                    "'mariadb_dyncol' is required to use DynamicField",
                    hint="Install the 'mariadb_dyncol' library from 'pip'",
                    obj=self,
                    id="django_mysql.E012",
                )
            )
        return errors

    def _check_mariadb_version(self):
        errors = []

        any_conn_works = False
        for _alias, conn in mysql_connections():
            if (
                hasattr(conn, "mysql_version")
                and connection_is_mariadb(conn)
                and conn.mysql_version >= (10, 0, 1)
            ):
                any_conn_works = True

        if not any_conn_works:
            errors.append(
                checks.Error(
                    "MariaDB 10.0.1+ is required to use DynamicField",
                    hint="At least one of your DB connections should be to "
                    "MariaDB 10.0.1+",
                    obj=self,
                    id="django_mysql.E013",
                )
            )
        return errors

    def _check_character_set(self):
        errors = []

        conn = None
        for _alias, check_conn in mysql_connections():
            if (
                hasattr(check_conn, "mysql_version")
                and connection_is_mariadb(check_conn)
                and check_conn.mysql_version >= (10, 0, 1)
            ):
                conn = check_conn
                break

        if conn is not None:
            with conn.cursor() as cursor:
                cursor.execute("SELECT @@character_set_client")
                charset = cursor.fetchone()[0]

            if charset not in ("utf8", "utf8mb4"):
                errors.append(
                    checks.Error(
                        "The MySQL charset must be 'utf8' or 'utf8mb4' to "
                        "use DynamicField",
                        hint="You are currently connecting with the '{}' "
                        "character set. Add "
                        "'OPTIONS': {{'charset': 'utf8mb4'}}, to your "
                        "DATABASES setting to fix this".format(charset),
                        obj=self,
                        id="django_mysql.E014",
                    )
                )

        return errors

    def _check_spec_recursively(self, spec, path=""):
        errors = []

        if not isinstance(spec, dict):
            errors.append(
                checks.Error(
                    "'spec' must be a dict",
                    hint="The value passed is of type {}".format(type(spec).__name__),
                    obj=self,
                    id="django_mysql.E009",
                )
            )
            return errors

        for key, value in spec.items():
            if not isinstance(key, str):
                errors.append(
                    checks.Error(
                        "The key '{}' in 'spec{}' is not a string".format(key, path),
                        hint="'spec' keys must be of type str, "
                        "'{}' is of type {}".format(key, type(key).__name__),
                        obj=self,
                        id="django_mysql.E010",
                    )
                )
                continue

            if isinstance(value, dict):
                subpath = "{}.{}".format(path, key)
                errors.extend(self._check_spec_recursively(value, subpath))
            elif value not in KeyTransform.SPEC_MAP:
                errors.append(
                    checks.Error(
                        "The value for '{}' in 'spec{}' is not an allowed type".format(
                            key, path
                        ),
                        hint="'spec' values must be one of the following "
                        "types: {}".format(KeyTransform.SPEC_MAP_NAMES),
                        obj=self,
                        id="django_mysql.E011",
                    )
                )

        return errors

    def db_type(self, connection):
        return "mediumblob"

    def get_transform(self, name):
        transform = super(DynamicField, self).get_transform(name)
        if transform:
            return transform
        if name in self.spec:
            type_ = self.spec[name]
            if isinstance(type_, dict):
                # Nested dict
                data_type = KeyTransform.SPEC_MAP[dict]
                return KeyTransformFactory(name, data_type, subspec=type_)
            else:
                # Scalar type
                return KeyTransformFactory(name, KeyTransform.SPEC_MAP[type_])

        end = name.split("_")[-1]
        if end in KeyTransform.TYPE_MAP and len(name) > len(end):
            return KeyTransformFactory(
                key_name=name[: -len(end) - 1], data_type=end  # '_' + data_type
            )

    def to_python(self, value):
        if isinstance(value, bytes):
            return mariadb_dyncol.unpack(value)
        elif isinstance(value, str):
            return json.loads(value)  # serialization framework
        return value

    if django.VERSION >= (2, 0):

        def from_db_value(self, value, expression, connection):
            # Used to always convert a value from the database
            return self.to_python(value)

    else:

        def from_db_value(self, value, expression, connection, context):
            # Used to always convert a value from the database
            return self.to_python(value)

    def get_prep_value(self, value):
        value = super(DynamicField, self).get_prep_value(value)
        if isinstance(value, dict):
            self.validate_spec(self.spec, value)
            return mariadb_dyncol.pack(value)
        return value

    @classmethod
    def validate_spec(cls, spec, value, prefix=""):
        for key, subspec in spec.items():
            if key in value:

                if isinstance(subspec, dict):
                    expected_type = dict
                else:
                    expected_type = subspec

                if not isinstance(value[key], expected_type):
                    raise TypeError(
                        "Key '{}{}' should be of type {}".format(
                            prefix, key, expected_type.__name__
                        )
                    )

                if isinstance(subspec, dict):
                    cls.validate_spec(subspec, value[key], prefix + key + ".")

    def get_internal_type(self):
        return "BinaryField"

    def value_to_string(self, obj):
        return json.dumps(self.value_from_object(obj))

    def deconstruct(self):
        name, path, args, kwargs = super(DynamicField, self).deconstruct()

        bad_paths = (
            "django_mysql.models.fields.dynamic.DynamicField",
            "django_mysql.models.fields.DynamicField",
        )
        if path in bad_paths:
            path = "django_mysql.models.DynamicField"

        # Remove defaults
        if "default" in kwargs and kwargs["default"] is dict:
            del kwargs["default"]
        if "blank" in kwargs and kwargs["blank"]:
            del kwargs["blank"]
        return name, path, args, kwargs

    def formfield(self, *args, **kwargs):
        """
        Disabled in forms - there is no sensible way of editing this
        """
        return None


DynamicField.register_lookup(DynColHasKey)


class KeyTransform(Transform):

    SPEC_MAP = {
        date: "DATE",
        datetime: "DATETIME",
        float: "DOUBLE",
        int: "INTEGER",
        str: "CHAR",
        time: "TIME",
        dict: "BINARY",
    }

    SPEC_MAP_NAMES = ", ".join(sorted(x.__name__ for x in SPEC_MAP.keys()))

    TYPE_MAP = {
        "BINARY": DynamicField,
        "CHAR": TextField(),
        "DATE": DateField(),
        "DATETIME": DateTimeField(),
        "DOUBLE": FloatField(),
        "INTEGER": IntegerField(),
        "TIME": TimeField(),
    }

    def __init__(self, key_name, data_type, *args, **kwargs):
        subspec = kwargs.pop("subspec", None)
        super(KeyTransform, self).__init__(*args, **kwargs)
        self.key_name = key_name
        self.data_type = data_type

        try:
            output_field = self.TYPE_MAP[data_type]
        except KeyError:  # pragma: no cover
            raise ValueError("Invalid data_type '{}'".format(data_type))

        if data_type == "BINARY":
            self.output_field = output_field(spec=subspec)
        else:
            self.output_field = output_field

    def as_sql(self, compiler, connection):
        lhs, params = compiler.compile(self.lhs)
        return (
            "COLUMN_GET({}, %s AS {})".format(lhs, self.data_type),
            tuple(params) + (self.key_name,),
        )


class KeyTransformFactory(object):
    def __init__(self, key_name, data_type, subspec=None):
        self.key_name = key_name
        self.data_type = data_type
        self.subspec = subspec

    def __call__(self, *args, **kwargs):
        if self.subspec is not None:
            kwargs["subspec"] = self.subspec
        return KeyTransform(self.key_name, self.data_type, *args, **kwargs)
