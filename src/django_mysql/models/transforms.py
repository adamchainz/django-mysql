from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.models import IntegerField
from django.db.models import Transform
from django.db.models.sql.compiler import SQLCompiler

from django_mysql.utils import collapse_spaces


class SetLength(Transform):
    lookup_name = "len"
    output_field = IntegerField()

    # No str.count equivalent in MySQL :(
    expr = collapse_spaces(
        """
        (
            CHAR_LENGTH(%s) -
            CHAR_LENGTH(REPLACE(%s, ',', '')) +
            IF(CHAR_LENGTH(%s), 1, 0)
        )
    """
    )

    def as_sql(
        self, compiler: SQLCompiler, connection: BaseDatabaseWrapper
    ) -> tuple[str, Iterable[Any]]:
        lhs, params = compiler.compile(self.lhs)
        return self.expr % (lhs, lhs, lhs), params
