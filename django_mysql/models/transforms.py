# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from django.db.models import IntegerField, Transform


class SetLength(Transform):
    lookup_name = 'len'
    output_field = IntegerField()

    expr = (
        # No str.count equivalent in MySQL :(
        "("
        "CHAR_LENGTH(%s) -"
        "CHAR_LENGTH(REPLACE(%s, ',', '')) +"
        "IF(CHAR_LENGTH(%s), 1, 0)"
        ")"
    )

    def as_sql(self, compiler, connection):
        lhs, params = compiler.compile(self.lhs)
        return self.expr % (lhs, lhs, lhs), params
