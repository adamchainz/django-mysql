from __future__ import annotations

from typing import Any

from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.models import Aggregate, CharField, Expression
from django.db.models.sql.compiler import SQLCompiler


class BitAnd(Aggregate):
    function = "BIT_AND"
    name = "bitand"


class BitOr(Aggregate):
    function = "BIT_OR"
    name = "bitor"


class BitXor(Aggregate):
    function = "BIT_XOR"
    name = "bitxor"


class GroupConcat(Aggregate):
    template = "%(function)s(%(distinct)s%(expressions)s%(order_by)s%(separator)s)"
    function = "GROUP_CONCAT"
    name = "GroupConcat"
    output_field = CharField()
    allow_distinct = True

    def __init__(
        self,
        expression: Expression,
        filter: Any | None = None,
        distinct: bool = False,
        separator: str | None = None,
        ordering: str | None = None,
        **extra: Any,
    ) -> None:

        if "output_field" not in extra:
            # This can/will be improved to SetTextField or ListTextField
            extra["output_field"] = CharField()

        super().__init__(expression, filter=filter, **extra)

        self.distinct = distinct
        self.separator = separator

        if ordering not in ("asc", "desc", None):
            raise ValueError("'ordering' must be one of 'asc', 'desc', or None")
        self.ordering = ordering

    def as_sql(
        self,
        compiler: SQLCompiler,
        connection: BaseDatabaseWrapper,
        **extra_context: Any,
    ) -> tuple[str, tuple[Any, ...]]:
        def expr_sql():
            expr_parts = []
            params = []
            for arg in self.source_expressions:
                arg_sql, arg_params = compiler.compile(arg)
                expr_parts.append(arg_sql)
                params.extend(arg_params)
            return self.arg_joiner.join(expr_parts), params

        if self.filter:
            extra_context["distinct"] = "DISTINCT " if self.distinct else ""
            copy = self.copy()
            copy.filter = None
            source_expressions = copy.get_source_expressions()
            condition = When(self.filter, then=source_expressions[0])
            copy.set_source_expressions([Case(condition)] + source_expressions[1:])

            expr_sql, _ = expr_sql()

            extra_context["order_by"] = (
                f" ORDER BY {expr_sql} {self.ordering}" if self.ordering else ""
            )

            extra_context["separator"] = (
                f" SEPARATOR '{self.separator}' " if self.separator else ""
            )

            return super(Aggregate, copy).as_sql(compiler, connection, **extra_context)

        connection.ops.check_expression_support(self)
        sql = ["GROUP_CONCAT("]
        if self.distinct:
            sql.append("DISTINCT ")

        expr_sql, params = expr_sql()

        sql.append(expr_sql)

        if self.ordering is not None:
            sql.append(" ORDER BY ")
            sql.append(expr_sql)
            params.extend(params[:])
            sql.append(" ")
            sql.append(self.ordering.upper())

        if self.separator is not None:
            sql.append(f" SEPARATOR '{self.separator}'")

        sql.append(")")

        return "".join(sql), tuple(params)
