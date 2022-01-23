from __future__ import annotations

from typing import Any, cast

from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.models import CharField

from django_mysql.typing import DeconstructResult


class FixedCharField(CharField):
    def __init__(self, *args: Any, length: int, **kwargs: Any) -> None:
        if length < 0 or length > 255:
            raise ValueError(
                'Invalid length value "{length}". '
                "Length must be in the range of 0-255.".format(length=length)
            )

        if "max_length" in kwargs:
            raise TypeError('"max_length" is not a valid argument')

        super().__init__(*args, max_length=length, **kwargs)

    def deconstruct(self) -> DeconstructResult:
        name, path, args, kwargs = cast(DeconstructResult, super().deconstruct())

        bad_paths = (
            "django_mysql.models.fields.fixedchar.FixedCharField",
            "django_mysql.models.fields.FixedCharField",
        )
        if path in bad_paths:
            path = "django_mysql.models.FixedCharField"

        kwargs["length"] = kwargs.pop("max_length")

        return name, path, args, kwargs

    def db_type(self, connection: BaseDatabaseWrapper) -> str:
        return f"CHAR({self.max_length})"
