from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.models import F, Value
from django.db.models.expressions import BaseExpression
from django.db.models.sql.compiler import SQLCompiler

from django_mysql.utils import collapse_spaces


class TwoSidedExpression(BaseExpression):
    def __init__(self, lhs: BaseExpression, rhs: BaseExpression) -> None:
        super().__init__()
        self.lhs = lhs
        self.rhs = rhs

    def get_source_expressions(self) -> list[BaseExpression]:
        return [self.lhs, self.rhs]

    def set_source_expressions(self, exprs: Iterable[BaseExpression]) -> None:
        self.lhs, self.rhs = exprs


class ListF:
    def __init__(self, field_name: str) -> None:
        self.field_name = field_name
        self.field = F(field_name)

    def append(self, value: BaseExpression | Any) -> AppendListF:
        if not hasattr(value, "as_sql"):
            value = Value(value)
        return AppendListF(self.field, value)

    def appendleft(self, value: Any | BaseExpression) -> AppendLeftListF:
        if not hasattr(value, "as_sql"):
            value = Value(value)
        return AppendLeftListF(self.field, value)

    def pop(self) -> PopListF:
        return PopListF(self.field)

    def popleft(self) -> PopLeftListF:
        return PopLeftListF(self.field)


class AppendListF(TwoSidedExpression):
    # A slightly complicated expression.
    # basically if 'value' is not in the set, concat the current set with a
    # comma and 'value'
    # N.B. using MySQL side variables to avoid repeat calculation of
    # expression[s]
    sql_expression = collapse_spaces(
        """
        CONCAT_WS(
            ',',
            IF(
                (@tmp_f:=%s) > '',
                @tmp_f,
                NULL
            ),
            %s
        )
    """
    )

    def as_sql(
        self,
        compiler: SQLCompiler,
        connection: BaseDatabaseWrapper,
    ) -> tuple[str, tuple[Any, ...]]:
        field, field_params = compiler.compile(self.lhs)
        value, value_params = compiler.compile(self.rhs)

        sql = self.sql_expression % (field, value)
        params = tuple(value_params) + tuple(field_params)

        return sql, params


class AppendLeftListF(TwoSidedExpression):
    # A slightly complicated expression.
    # basically if 'value' is not in the set, concat the current set with a
    # comma and 'value'
    # N.B. using MySQL side variables to avoid repeat calculation of
    # expression[s]
    sql_expression = collapse_spaces(
        """
        CONCAT_WS(
            ',',
            %s,
            IF(
                (@tmp_f:=%s) > '',
                @tmp_f,
                NULL
            )
        )
    """
    )

    def as_sql(
        self,
        compiler: SQLCompiler,
        connection: BaseDatabaseWrapper,
    ) -> tuple[str, tuple[Any, ...]]:
        field, field_params = compiler.compile(self.lhs)
        value, value_params = compiler.compile(self.rhs)

        sql = self.sql_expression % (value, field)
        params = tuple(field_params) + tuple(value_params)

        return sql, params


class PopListF(BaseExpression):
    sql_expression = collapse_spaces(
        """
        SUBSTRING(
            @tmp_f:=%s,
            1,
            IF(
                LOCATE(',', @tmp_f),
                (
                    CHAR_LENGTH(@tmp_f) -
                    CHAR_LENGTH(SUBSTRING_INDEX(@tmp_f, ',', -1)) -
                    1
                ),
                0
            )
        )
    """
    )

    def __init__(self, lhs: BaseExpression) -> None:
        super().__init__()
        self.lhs = lhs

    def get_source_expressions(self) -> list[BaseExpression]:
        return [self.lhs]

    def set_source_expressions(self, exprs: Iterable[BaseExpression]) -> None:
        (self.lhs,) = exprs

    def as_sql(
        self,
        compiler: SQLCompiler,
        connection: BaseDatabaseWrapper,
    ) -> tuple[str, tuple[Any, ...]]:
        field, field_params = compiler.compile(self.lhs)

        sql = self.sql_expression % (field)
        return sql, tuple(field_params)


class PopLeftListF(BaseExpression):
    sql_expression = collapse_spaces(
        """
        IF(
            (@tmp_c:=LOCATE(',', @tmp_f:=%s)) > 0,
            SUBSTRING(@tmp_f, @tmp_c + 1),
            ''
        )
    """
    )

    def __init__(self, lhs: BaseExpression) -> None:
        super().__init__()
        self.lhs = lhs

    def get_source_expressions(self) -> list[BaseExpression]:
        return [self.lhs]

    def set_source_expressions(self, exprs: Iterable[BaseExpression]) -> None:
        (self.lhs,) = exprs

    def as_sql(
        self,
        compiler: SQLCompiler,
        connection: BaseDatabaseWrapper,
    ) -> tuple[str, tuple[Any, ...]]:
        field, field_params = compiler.compile(self.lhs)

        sql = self.sql_expression % (field)
        return sql, tuple(field_params)


class SetF:
    def __init__(self, field_name: str) -> None:
        self.field = F(field_name)

    def add(self, value: Any | BaseExpression) -> AddSetF:
        if not hasattr(value, "as_sql"):
            value = Value(value)
        return AddSetF(self.field, value)

    def remove(self, value: Any | BaseExpression) -> RemoveSetF:
        if not hasattr(value, "as_sql"):
            value = Value(value)
        return RemoveSetF(self.field, value)


class AddSetF(TwoSidedExpression):
    # A slightly complicated expression.
    # basically if 'value' is not in the set, concat the current set with a
    # comma and 'value'
    # N.B. using MySQL side variables to avoid repeat calculation of
    # expression[s]
    sql_expression = collapse_spaces(
        """
        IF(
            FIND_IN_SET(@tmp_val:=%s, @tmp_f:=%s),
            @tmp_f,
            CONCAT_WS(
                ',',
                IF(CHAR_LENGTH(@tmp_f), @tmp_f, NULL),
                @tmp_val
            )
        )
    """
    )

    def as_sql(
        self,
        compiler: SQLCompiler,
        connection: BaseDatabaseWrapper,
    ) -> tuple[str, tuple[Any, ...]]:
        field, field_params = compiler.compile(self.lhs)
        value, value_params = compiler.compile(self.rhs)

        sql = self.sql_expression % (value, field)
        params = tuple(value_params) + tuple(field_params)

        return sql, params


class RemoveSetF(TwoSidedExpression):
    # Wow, this is a real doozy of an expression.
    # Basically, if it IS in the set, cut the string up to be everything except
    # that element.
    # There are some tricks going on - e.g. LEAST to evaluate a sub expression
    # but not use it in the output of CONCAT_WS
    sql_expression = collapse_spaces(
        """
        IF(
            @tmp_pos:=FIND_IN_SET(%s, @tmp_f:=%s),
            CONCAT_WS(
                ',',
                LEAST(
                    @tmp_len:=(
                        CHAR_LENGTH(@tmp_f) -
                        CHAR_LENGTH(REPLACE(@tmp_f, ',', '')) +
                        IF(CHAR_LENGTH(@tmp_f), 1, 0)
                    ),
                    NULL
                ),
                CASE WHEN
                    (@tmp_before:=SUBSTRING_INDEX(@tmp_f, ',', @tmp_pos - 1))
                    = ''
                    THEN NULL
                    ELSE @tmp_before
                END,
                CASE WHEN
                    (@tmp_after:=
                        SUBSTRING_INDEX(@tmp_f, ',', - (@tmp_len - @tmp_pos)))
                    = ''
                    THEN NULL
                    ELSE @tmp_after
                END
            ),
            @tmp_f
        )
    """
    )

    def as_sql(
        self,
        compiler: SQLCompiler,
        connection: BaseDatabaseWrapper,
    ) -> tuple[str, tuple[Any, ...]]:
        field, field_params = compiler.compile(self.lhs)
        value, value_params = compiler.compile(self.rhs)

        sql = self.sql_expression % (value, field)
        params = tuple(value_params) + tuple(field_params)

        return sql, params
