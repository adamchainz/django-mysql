from __future__ import annotations

from typing import Any

from django.db import models
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.models import Expression


class Bit1Mixin:
    def db_type(self, connection: BaseDatabaseWrapper) -> str:
        return "bit(1)"

    def from_db_value(
        self, value: Any, expression: Expression, connection: BaseDatabaseWrapper
    ) -> Any:
        return value == b"\x01"

    def get_prep_value(self, value: Any) -> int | None:
        if value is None:
            return value
        else:
            return 1 if value else 0


class Bit1BooleanField(Bit1Mixin, models.BooleanField):
    pass


class NullBit1BooleanField(Bit1Mixin, models.NullBooleanField):
    pass
