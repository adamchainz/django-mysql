from __future__ import annotations

import datetime as dt
import json
from typing import Any, Union

from django.db import DEFAULT_DB_ALIAS, connections
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.models import (
    CharField,
    Expression,
    Func,
    IntegerField,
    JSONField,
    TextField,
    Value,
)
from django.db.models import Field as DjangoField
from django.db.models.sql.compiler import SQLCompiler

ExpressionArgument = Union[
    Expression,
    str,  # column reference handled by Django
]


class SingleArgFunc(Func):
    output_field_class: type[DjangoField]

    def __init__(self, expression: ExpressionArgument) -> None:
        super().__init__(expression, output_field=self.output_field_class())


# Control Flow Functions


class If(Func):
    function = "IF"

    def __init__(
        self,
        condition: ExpressionArgument,
        true: ExpressionArgument,
        false: ExpressionArgument | None = None,
        output_field: DjangoField | None = None,
    ) -> None:
        if output_field is None:
            # Workaround for some ORM weirdness
            output_field = DjangoField()

        super().__init__(condition, true, false, output_field=output_field)


# Numeric Functions


class CRC32(SingleArgFunc):
    function = "CRC32"
    output_field_class = IntegerField


# String Functions


class ConcatWS(Func):
    """
    Stands for CONCAT_With-Separator
    """

    function = "CONCAT_WS"

    def __init__(
        self, *expressions: ExpressionArgument, separator: str | None = ","
    ) -> None:
        if len(expressions) < 2:
            raise ValueError("ConcatWS must take at least two expressions")

        if not hasattr(separator, "resolve_expression"):
            separator = Value(separator)

        # N.B. if separator is "," we could potentially use list field
        output_field = TextField()
        super().__init__(separator, *expressions, output_field=output_field)


class ELT(Func):
    function = "ELT"

    def __init__(
        self,
        num: ExpressionArgument,
        expressions: list[ExpressionArgument] | tuple[ExpressionArgument],
    ) -> None:
        value_exprs = []
        for v in expressions:
            if not hasattr(v, "resolve_expression"):
                v = Value(v)
            value_exprs.append(v)

        super().__init__(num, *value_exprs, output_field=CharField())


class Field(Func):
    function = "FIELD"

    def __init__(
        self,
        field: ExpressionArgument,
        values: list[ExpressionArgument] | tuple[ExpressionArgument],
        **kwargs: Any,
    ) -> None:
        values_exprs = []
        for v in values:
            if not hasattr(v, "resolve_expression"):
                v = Value(v)
            values_exprs.append(v)

        super().__init__(field, *values_exprs)


# XML Functions


class UpdateXML(Func):
    function = "UPDATEXML"

    def __init__(
        self,
        xml_target: ExpressionArgument,
        xpath_expr: ExpressionArgument,
        new_xml: ExpressionArgument,
    ) -> None:
        if not hasattr(xpath_expr, "resolve_expression"):
            xpath_expr = Value(xpath_expr)
        if not hasattr(new_xml, "resolve_expression"):
            new_xml = Value(new_xml)

        super().__init__(xml_target, xpath_expr, new_xml, output_field=TextField())


class XMLExtractValue(Func):
    function = "EXTRACTVALUE"

    def __init__(
        self, xml_frag: ExpressionArgument, xpath_expr: ExpressionArgument
    ) -> None:
        if not hasattr(xpath_expr, "resolve_expression"):
            xpath_expr = Value(xpath_expr)

        super().__init__(xml_frag, xpath_expr, output_field=TextField())


# Information Functions


class LastInsertId(Func):
    function = "LAST_INSERT_ID"

    def __init__(self, expression: ExpressionArgument | None = None) -> None:
        if expression is not None:
            super().__init__(expression, output_field=IntegerField())
        else:
            super().__init__(output_field=IntegerField())

    @classmethod
    def get(cls, using: str = DEFAULT_DB_ALIAS) -> int:
        # N.B. did try getting it from connection.connection.insert_id() (The
        # MySQLdb query-free method) but it did not work with non-default
        # database connections in Django, and the reason was not clear
        with connections[using].cursor() as cursor:
            cursor.execute("SELECT LAST_INSERT_ID()")
            return cursor.fetchone()[0]


# JSON Functions


class JSONExtract(Func):
    function = "JSON_EXTRACT"

    def __init__(
        self,
        expression: ExpressionArgument,
        *paths: ExpressionArgument,
        output_field: type[DjangoField] | None = None,
    ) -> None:
        exprs = [expression]
        for path in paths:
            if not hasattr(path, "resolve_expression"):
                path = Value(path)
            exprs.append(path)

        if output_field is not None:
            if len(paths) > 1:
                raise TypeError(
                    "output_field won't work with more than one path, as a "
                    "JSON Array will be returned"
                )
        else:
            output_field = JSONField()

        super().__init__(*exprs, output_field=output_field)


class JSONKeys(Func):
    function = "JSON_KEYS"

    def __init__(
        self,
        expression: ExpressionArgument,
        path: ExpressionArgument | None = None,
    ) -> None:
        exprs = [expression]
        if path is not None:
            if not hasattr(path, "resolve_expression"):
                path = Value(path)
            exprs.append(path)

        super().__init__(*exprs, output_field=JSONField())


class JSONLength(Func):
    function = "JSON_LENGTH"

    def __init__(
        self,
        expression: ExpressionArgument,
        path: ExpressionArgument | None = None,
        *,
        output_field: DjangoField | None = None,
        **extra: Any,
    ) -> None:
        if output_field is None:
            output_field = IntegerField()

        exprs = [expression]
        if path is not None:
            if not hasattr(path, "resolve_expression"):
                path = Value(path)
            exprs.append(path)

        super().__init__(*exprs, output_field=output_field)


# When only Django 3.1+ is supported, JSONValue can be replaced with
# Cast(..., output_field=JSONField())
class JSONValue(Expression):
    def __init__(
        self, data: None | int | float | str | list[Any] | dict[str, Any]
    ) -> None:
        self._data = data

    def as_sql(
        self,
        compiler: SQLCompiler,
        connection: BaseDatabaseWrapper,
    ) -> tuple[str, tuple[Any, ...]]:
        if connection.vendor != "mysql":  # pragma: no cover
            raise AssertionError("JSONValue only supports MySQL/MariaDB")
        json_string = json.dumps(self._data, allow_nan=False)
        if connection.vendor == "mysql" and connection.mysql_is_mariadb:
            # MariaDB doesn't support explicit cast to JSON.
            return "JSON_EXTRACT(%s, '$')", (json_string,)
        else:
            return "CAST(%s AS JSON)", (json_string,)


class BaseJSONModifyFunc(Func):
    def __init__(
        self,
        expression: ExpressionArgument,
        data: dict[
            str,
            (
                ExpressionArgument
                | None
                | int
                | float
                | str
                | list[Any]
                | dict[str, Any]
            ),
        ],
    ) -> None:
        if not data:
            raise ValueError('"data" cannot be empty')

        exprs = [expression]

        for path, value in data.items():
            if not hasattr(path, "resolve_expression"):
                path = Value(path)

            exprs.append(path)

            if not hasattr(value, "resolve_expression"):
                value = JSONValue(value)

            exprs.append(value)

        super().__init__(*exprs, output_field=JSONField())


class JSONInsert(BaseJSONModifyFunc):
    function = "JSON_INSERT"


class JSONReplace(BaseJSONModifyFunc):
    function = "JSON_REPLACE"


class JSONSet(BaseJSONModifyFunc):
    function = "JSON_SET"


class JSONArrayAppend(BaseJSONModifyFunc):
    function = "JSON_ARRAY_APPEND"


# MariaDB Regexp Functions


class RegexpInstr(Func):
    function = "REGEXP_INSTR"

    def __init__(
        self, expression: ExpressionArgument, regex: ExpressionArgument
    ) -> None:
        if not hasattr(regex, "resolve_expression"):
            regex = Value(regex)

        super().__init__(expression, regex, output_field=IntegerField())


class RegexpReplace(Func):
    function = "REGEXP_REPLACE"

    def __init__(
        self,
        expression: ExpressionArgument,
        regex: ExpressionArgument,
        replace: ExpressionArgument,
    ) -> None:
        if not hasattr(regex, "resolve_expression"):
            regex = Value(regex)

        if not hasattr(replace, "resolve_expression"):
            replace = Value(replace)

        super().__init__(expression, regex, replace, output_field=CharField())


class RegexpSubstr(Func):
    function = "REGEXP_SUBSTR"

    def __init__(
        self, expression: ExpressionArgument, regex: ExpressionArgument
    ) -> None:
        if not hasattr(regex, "resolve_expression"):
            regex = Value(regex)

        super().__init__(expression, regex, output_field=CharField())


# MariaDB Dynamic Columns Functions


class AsType(Func):
    """
    Helper for ColumnAdd when you want to add a column with a given type
    """

    function = ""
    template = "%(expressions)s AS %(data_type)s"

    def __init__(self, expression: ExpressionArgument, data_type: str) -> None:
        from django_mysql.models.fields.dynamic import KeyTransform

        if not hasattr(expression, "resolve_expression"):
            expression = Value(expression)

        if data_type not in KeyTransform.TYPE_MAP and data_type != "BINARY":
            raise ValueError(f"Invalid data_type {data_type!r}")

        super().__init__(expression, data_type=data_type)


class ColumnAdd(Func):
    function = "COLUMN_ADD"

    def __init__(
        self,
        expression: ExpressionArgument,
        to_add: dict[
            str,
            ExpressionArgument | float | int | dt.date | dt.time | dt.datetime,
        ],
    ) -> None:
        from django_mysql.models.fields import DynamicField

        expressions = [expression]
        for name, value in to_add.items():
            if not hasattr(name, "resolve_expression"):
                name = Value(name)

            if isinstance(value, dict):
                raise ValueError("ColumnAdd with nested values is not supported")
            if not hasattr(value, "resolve_expression"):
                value = Value(value)

            expressions.extend((name, value))

        super().__init__(*expressions, output_field=DynamicField())


class ColumnDelete(Func):
    function = "COLUMN_DELETE"

    def __init__(
        self, expression: ExpressionArgument, *to_delete: ExpressionArgument
    ) -> None:
        from django_mysql.models.fields import DynamicField

        expressions = [expression]
        for name in to_delete:
            if not hasattr(name, "resolve_expression"):
                name = Value(name)
            expressions.append(name)

        super().__init__(*expressions, output_field=DynamicField())


class ColumnGet(Func):
    function = "COLUMN_GET"
    template = "COLUMN_GET(%(expressions)s AS %(data_type)s)"

    def __init__(
        self,
        expression: ExpressionArgument,
        column_name: ExpressionArgument,
        data_type: str,
    ):
        from django_mysql.models.fields.dynamic import DynamicField, KeyTransform

        if not hasattr(column_name, "resolve_expression"):
            column_name = Value(column_name)

        output_field: DjangoField[Any, Any]
        if data_type == "BINARY":
            output_field = DynamicField()
        else:
            try:
                output_field = KeyTransform.TYPE_MAP[data_type]
            except KeyError:
                raise ValueError(f"Invalid data_type {data_type!r}")

        super().__init__(
            expression,
            column_name,
            output_field=output_field,
            data_type=data_type,
        )
