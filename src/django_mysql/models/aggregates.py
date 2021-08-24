from typing import Any, Optional, Tuple

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
    function = "GROUP_CONCAT"

    def __init__(
        self,
        expression: Expression,
        distinct: bool = False,
        separator: Optional[str] = None,
        ordering: Optional[str] = None,
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
        self.ordering = ordering

    def as_sql(
        self,
        compiler: SQLCompiler,
        connection: BaseDatabaseWrapper,
        **extra_context: Any,
    ) -> Tuple[str, Tuple[Any, ...]]:
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
