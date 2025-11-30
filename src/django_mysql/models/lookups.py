from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.models import CharField, Lookup, Transform
from django.db.models.lookups import BuiltinLookup
from django.db.models.sql.compiler import SQLCompiler


class CaseSensitiveExact(BuiltinLookup):
    lookup_name = "case_exact"

    def get_rhs_op(self, connection: BaseDatabaseWrapper, rhs: str) -> str:
        return f"= BINARY {rhs}"


class SoundsLike(Lookup):
    lookup_name = "sounds_like"

    def as_sql(
        self,
        qn: Callable[[str], str],
        connection: BaseDatabaseWrapper,
    ) -> tuple[str, tuple[Any, ...]]:
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        return (
            f"{lhs} SOUNDS LIKE {rhs}",
            (*lhs_params, *rhs_params),
        )


class Soundex(Transform):
    lookup_name = "soundex"
    output_field = CharField()

    def as_sql(
        self, compiler: SQLCompiler, connection: BaseDatabaseWrapper
    ) -> tuple[str, tuple[Any, ...]]:
        lhs, params = compiler.compile(self.lhs)
        return f"SOUNDEX({lhs})", params


# Custom field class lookups


# Set{Char,Text}Field


class SetContains(Lookup):
    lookup_name = "contains"

    def get_prep_lookup(self) -> Any:
        if isinstance(self.rhs, (list, set, tuple)):
            # Can't do multiple contains without massive ORM hackery
            # (ANDing all the FIND_IN_SET calls), so just reject them
            raise ValueError(
                f"Can't do contains with a set and {self.lhs.__class__.__name__}, you should "
                "pass them as separate filters."
            )
        return super().get_prep_lookup()

    def as_sql(
        self, qn: Callable[[str], str], connection: BaseDatabaseWrapper
    ) -> tuple[str, tuple[Any, ...]]:
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        # Put rhs (and params) on the left since that's the order FIND_IN_SET uses
        return (
            f"FIND_IN_SET({rhs}, {lhs})",
            (*rhs_params, *lhs_params),
        )


class SetIContains(SetContains):
    lookup_name = "icontains"


# DynamicField


class DynColHasKey(Lookup):
    lookup_name = "has_key"

    def as_sql(
        self, qn: Callable[[str], str], connection: BaseDatabaseWrapper
    ) -> tuple[str, tuple[Any, ...]]:
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        return (
            f"COLUMN_EXISTS({lhs}, {rhs})",
            (*lhs_params, *rhs_params),
        )
