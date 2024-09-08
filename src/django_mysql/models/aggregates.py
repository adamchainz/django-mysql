from __future__ import annotations

from typing import Any

from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.models import Aggregate
from django.db.models import CharField
from django.db.models import Expression
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
    function = "GROUP_CONCAT"

    def __init__(
        self,
        expression: Expression,
        distinct: bool = False,
        separator: str | None = None,
        ordering: str | None = None,
        column_order: Union[List[str], str] | None = None,
        **extra: Any,
    ) -> None:
        if "output_field" not in extra:
            # This can/will be improved to SetTextField or ListTextField
            extra["output_field"] = CharField()

        super().__init__(expression, **extra)

        self.distinct = distinct
        self.separator = separator

        if ordering not in ("asc", "desc", None):
            raise ValueError("'ordering' must be one of 'asc', 'desc', or None")
        if ordering is not None:
            if column_order is not None and isinstance(column_order, list):
                raise ValueError(
                    "When having a list in column_order, you can specify the ordering of each column inside the list. Example: ['column_a DESC',...]"
                )
        self.ordering = ordering
        self.column_order = column_order

    def as_sql(
        self,
        compiler: SQLCompiler,
        connection: BaseDatabaseWrapper,
        **extra_context: Any,
    ) -> tuple[str, tuple[Any, ...]]:
        connection.ops.check_expression_support(self)
        sql = ["GROUP_CONCAT("]
        if self.distinct:
            sql.append("DISTINCT ")

        expr_parts = []
        params = []
        for arg in self.source_expressions:
            arg_sql, arg_params = compiler.compile(arg)
            expr_parts.append(arg_sql)
            params.extend(arg_params)
        expr_sql = self.arg_joiner.join(expr_parts)

        sql.append(expr_sql)

        if self.ordering is not None or self.column_order is not None:
            sql.append(" ORDER BY")

            if self.column_order is not None:
                if isinstance(self.column_order, str):
                    sql.append(" ")
                    sql.append(self.column_order)
                if isinstance(self.column_order, list):
                    sql.append(" ")
                    sql.append(", ".join(self.column_order))
            else:
                sql.append(" ")
                sql.append(expr_sql)
                params.extend(params[:])

            if self.ordering is not None and not isinstance(self.column_order, list):
                sql.append(" ")
                sql.append(self.ordering.upper())

        if self.separator is not None:
            sql.append(f" SEPARATOR '{self.separator}'")  # noqa: B028

        sql.append(")")

        return "".join(sql), tuple(params)
