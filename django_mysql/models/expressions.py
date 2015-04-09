# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from django.db.models import F

from django_mysql.shims.expressions import BaseExpression, Value
from django_mysql.utils import collapse_spaces


class SetF(object):

    def __init__(self, field_name):
        self.field = F(field_name)

    def add(self, value):
        if not hasattr(value, 'as_sql'):
            value = Value(value)
        return AddSetF(self.field, value)

    def remove(self, value):
        if not hasattr(value, 'as_sql'):
            value = Value(value)
        return RemoveSetF(self.field, value)


class BaseSetF(BaseExpression):

    def __init__(self, lhs, rhs):
        super(BaseSetF, self).__init__()
        self.lhs = lhs
        self.rhs = rhs

    def get_source_expressions(self):
        return [self.lhs, self.rhs]

    def set_source_expressions(self, exprs):
        self.lhs, self.rhs = exprs


class AddSetF(BaseSetF):

    # A slightly complicated expression.
    # basically if 'value' is not in the set, concat the current set with a
    # comma and 'value'
    # N.B. using MySQL side variables to avoid repeat calculation of
    # expression[s]
    sql_expression = collapse_spaces("""
        IF(
            FIND_IN_SET(@tmp_val:=%s, @tmp_f:=%s),
            @tmp_f,
            CONCAT_WS(
                ',',
                IF(CHAR_LENGTH(@tmp_f), @tmp_f, NULL),
                @tmp_val
            )
        )
    """)

    def as_sql(self, compiler, connection):
        field, field_params = compiler.compile(self.lhs)
        value, value_params = compiler.compile(self.rhs)

        sql = self.sql_expression % (value, field)

        params = []
        params.extend(value_params)
        params.extend(field_params)

        return sql, params


class RemoveSetF(BaseSetF):

    # Wow, this is a real doozy of an expression.
    # Basically, if it IS in the set, cut the string up to be everything except
    # that element.
    # There are some tricks going on - e.g. LEAST to evaluate a sub expression
    # but not use it in the output of CONCAT_WS
    sql_expression = collapse_spaces("""
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
    """)

    def as_sql(self, compiler, connection):
        field, field_params = compiler.compile(self.lhs)
        value, value_params = compiler.compile(self.rhs)

        sql = self.sql_expression % (value, field)

        params = []
        params.extend(value_params)
        params.extend(field_params)

        return sql, params
