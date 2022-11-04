from __future__ import annotations

import datetime as dt
import json
from typing import Any
from typing import Callable
from typing import cast
from typing import Dict
from typing import Iterable
from typing import Type
from typing import Union

from django.core import checks
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.models import DateField
from django.db.models import DateTimeField
from django.db.models import Expression
from django.db.models import Field
from django.db.models import FloatField
from django.db.models import IntegerField
from django.db.models import TextField
from django.db.models import TimeField
from django.db.models import Transform
from django.db.models.sql.compiler import SQLCompiler
from django.forms import Field as FormField
from django.utils.translation import gettext_lazy as _

from django_mysql.checks import mysql_connections
from django_mysql.models.lookups import DynColHasKey
from django_mysql.typing import DeconstructResult

try:
    import mariadb_dyncol
except ImportError:  # pragma: no cover
    mariadb_dyncol = None


# Mypy doesn't support recursive types at time of writing, but we can at least
# define this type to two levels deep.
SpecDict = Dict[
    str,
    Union[
        Type[dt.date],
        Type[dt.datetime],
        Type[float],
        Type[int],
        Type[str],
        Type[dt.time],
        Dict[
            str,
            Union[
                Type[dt.date],
                Type[dt.datetime],
                Type[float],
                Type[int],
                Type[str],
                Type[dt.time],
                Dict[str, Any],
            ],
        ],
    ],
]


class DynamicField(Field):
    empty_strings_allowed = False
    description = _("Mapping")

    def __init__(
        self,
        *args: Any,
        default: Any = dict,
        blank: bool = True,
        spec: SpecDict | None = None,
        **kwargs: Any,
    ) -> None:
        if spec is None:
            self.spec = {}
        else:
            self.spec = spec
        super().__init__(*args, default=default, blank=blank, **kwargs)

    def check(self, **kwargs: Any) -> list[checks.CheckMessage]:
        errors = super().check(**kwargs)
        errors.extend(self._check_mariadb_dyncol())
        errors.extend(self._check_mariadb_version())
        errors.extend(self._check_character_set())
        errors.extend(self._check_spec_recursively(self.spec))
        return errors

    def _check_mariadb_dyncol(self) -> list[checks.CheckMessage]:
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

    def _check_mariadb_version(self) -> list[checks.CheckMessage]:
        errors = []

        any_conn_works = any(
            (conn.vendor == "mysql" and conn.mysql_is_mariadb)
            for _alias, conn in mysql_connections()
        )

        if not any_conn_works:
            errors.append(
                checks.Error(
                    "MariaDB is required to use DynamicField",
                    hint="At least one of your DB connections should be MariaDB.",
                    obj=self,
                    id="django_mysql.E013",
                )
            )
        return errors

    def _check_character_set(self) -> list[checks.CheckMessage]:
        errors = []

        conn = None
        for _alias, check_conn in mysql_connections():
            if check_conn.vendor == "mysql" and check_conn.mysql_is_mariadb:
                conn = check_conn
                break

        if conn is not None:
            with conn.cursor() as cursor:
                cursor.execute("SELECT @@character_set_client")
                charset: str = cursor.fetchone()[0]

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

    def _check_spec_recursively(
        self, spec: Any, path: str = ""
    ) -> list[checks.CheckMessage]:
        errors = []

        if not isinstance(spec, dict):
            errors.append(
                checks.Error(
                    "'spec' must be a dict",
                    hint=f"The value passed is of type {type(spec).__name__}",
                    obj=self,
                    id="django_mysql.E009",
                )
            )
            return errors

        for key, value in spec.items():
            if not isinstance(key, str):
                errors.append(
                    checks.Error(
                        f"The key '{key}' in 'spec{path}' is not a string",
                        hint="'spec' keys must be of type str, "
                        "'{}' is of type {}".format(key, type(key).__name__),
                        obj=self,
                        id="django_mysql.E010",
                    )
                )
                continue

            if isinstance(value, dict):
                subpath = f"{path}.{key}"
                errors.extend(self._check_spec_recursively(value, subpath))
            elif value not in KeyTransform.SPEC_MAP:
                valid_names = ", ".join(
                    sorted(x.__name__ for x in KeyTransform.SPEC_MAP.keys())
                )
                errors.append(
                    checks.Error(
                        "The value for '{}' in 'spec{}' is not an allowed type".format(
                            key, path
                        ),
                        hint=(
                            "'spec' values must be one of the following types: "
                            + valid_names
                        ),
                        obj=self,
                        id="django_mysql.E011",
                    )
                )

        return errors

    def db_type(self, connection: BaseDatabaseWrapper) -> str:
        return "mediumblob"

    def get_transform(
        self, name: str
    ) -> type[Transform] | Callable[..., Transform] | None:
        transform: type[Transform] | None = super().get_transform(name)
        if transform is not None:
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

        return None

    def to_python(self, value: Any) -> Any:
        if isinstance(value, bytes):
            return mariadb_dyncol.unpack(value)
        elif isinstance(value, str):
            return json.loads(value)  # serialization framework
        return value

    def from_db_value(
        self, value: Any, expression: Expression, connection: BaseDatabaseWrapper
    ) -> Any:
        # Used to always convert a value from the database
        return self.to_python(value)

    def get_prep_value(self, value: Any) -> Any:
        value = super().get_prep_value(value)
        if isinstance(value, dict):
            self.validate_spec(self.spec, value)
            return mariadb_dyncol.pack(value)
        return value

    @classmethod
    def validate_spec(
        cls, spec: dict[str, Any], value: dict[str, Any], prefix: str = ""
    ) -> None:
        for key, subspec in spec.items():
            if key in value:

                expected_type = dict if isinstance(subspec, dict) else subspec
                if not isinstance(value[key], expected_type):
                    raise TypeError(
                        "Key '{}{}' should be of type {}".format(
                            prefix, key, expected_type.__name__
                        )
                    )

                if isinstance(subspec, dict):
                    cls.validate_spec(subspec, value[key], prefix + key + ".")

    def get_internal_type(self) -> str:
        return "BinaryField"

    def value_to_string(self, obj: Any) -> str:
        return json.dumps(self.value_from_object(obj))

    def deconstruct(self) -> DeconstructResult:
        name, path, args, kwargs = cast(DeconstructResult, super().deconstruct())

        bad_paths = (
            "django_mysql.models.fields.dynamic.DynamicField",
            "django_mysql.models.fields.DynamicField",
        )
        if path in bad_paths:
            path = "django_mysql.models.DynamicField"

        # Remove defaults
        if "default" in kwargs and kwargs["default"] is dict:
            del kwargs["default"]
        if self.blank:
            kwargs.pop("blank")
        else:
            kwargs["blank"] = False
        return name, path, args, kwargs

    def formfield(self, *args: Any, **kwargs: Any) -> FormField | None:
        """
        Disabled in forms - there is no sensible way of editing this
        """
        return None


DynamicField.register_lookup(DynColHasKey)


class KeyTransform(Transform):

    SPEC_MAP = {
        dt.date: "DATE",
        dt.datetime: "DATETIME",
        float: "DOUBLE",
        int: "INTEGER",
        str: "CHAR",
        dt.time: "TIME",
        dict: "BINARY",
    }

    TYPE_MAP: dict[str, Field[Any, Any]] = {
        # Excludes BINARY -> DynamicField as that’s requires spec
        "CHAR": TextField(),
        "DATE": DateField(),
        "DATETIME": DateTimeField(),
        "DOUBLE": FloatField(),
        "INTEGER": IntegerField(),
        "TIME": TimeField(),
    }

    def __init__(
        self,
        key_name: str,
        data_type: str,
        *expressions: Any,
        subspec: SpecDict | None = None,
    ) -> None:
        output_field: Field[Any, Any]
        if data_type == "BINARY":
            output_field = DynamicField(spec=subspec)
        else:
            try:
                output_field = self.TYPE_MAP[data_type]
            except KeyError:
                raise ValueError(f"Invalid data_type {data_type!r}")

        super().__init__(*expressions, output_field=output_field)

        self.key_name = key_name
        self.data_type = data_type

    def as_sql(
        self, compiler: SQLCompiler, connection: BaseDatabaseWrapper
    ) -> tuple[str, Iterable[Any]]:
        lhs, params = compiler.compile(self.lhs)
        return (
            f"COLUMN_GET({lhs}, %s AS {self.data_type})",
            tuple(params) + (self.key_name,),
        )


class KeyTransformFactory:
    def __init__(
        self, key_name: str, data_type: str, subspec: SpecDict | None = None
    ) -> None:
        self.key_name = key_name
        self.data_type = data_type
        self.subspec = subspec

    def __call__(self, *args: Any, **kwargs: Any) -> Transform:
        if self.subspec is not None:
            kwargs["subspec"] = self.subspec
        return KeyTransform(self.key_name, self.data_type, *args, **kwargs)
