# -*- coding:utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals,
)

from django.db.models import Aggregate, CharField


class BitAnd(Aggregate):
    function = 'BIT_AND'
    name = 'bitand'


class BitOr(Aggregate):
    function = 'BIT_OR'
    name = 'bitor'


class BitXor(Aggregate):
    function = 'BIT_XOR'
    name = 'bitxor'


class GroupConcat(Aggregate):
    function = 'GROUP_CONCAT'

    def __init__(self, expression, distinct=False, separator=None,
                 ordering=None, **extra):

        if 'output_field' not in extra:
            # This can/will be improved to SetTextField or ListTextField
            extra['output_field'] = CharField()

        super(GroupConcat, self).__init__(expression, **extra)

        self.distinct = distinct
        self.separator = separator

        if ordering not in ('asc', 'desc', None):
            raise ValueError(
                "'ordering' must be one of 'asc', 'desc', or None")
        self.ordering = ordering

    def as_sql(self, compiler, connection, function=None, template=None):
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

        if self.separator is not None:
            sql.append(" SEPARATOR '{}'".format(self.separator))

        if self.ordering is not None:
            sql.append(" ORDER BY ")
            sql.append(expr_sql)
            params.extend(params[:])
            sql.append(" ")
            sql.append(self.ordering.upper())

        sql.append(")")

        return "".join(sql), params
