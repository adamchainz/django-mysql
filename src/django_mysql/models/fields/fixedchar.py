from __future__ import annotations

from typing import Any, cast

from django.core import checks
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.models import CharField

from django_mysql.typing import DeconstructResult


class FixedCharField(CharField):
    def check(self, **kwargs: Any) -> list[checks.CheckMessage]:
        errors = super().check(**kwargs)

        if isinstance(self.max_length, int) and (
            self.max_length < 0 or self.max_length > 255
        ):
            errors.append(
                checks.Error(
                    "'max_length' must be between 0 and 255.",
                    hint=None,
                    obj=self,
                    id="django_mysql.E015",
                )
            )

        return errors

    def deconstruct(self) -> DeconstructResult:
        name, path, args, kwargs = cast(DeconstructResult, super().deconstruct())

        bad_paths = (
            "django_mysql.models.fields.fixedchar.FixedCharField",
            "django_mysql.models.fields.FixedCharField",
        )
        if path in bad_paths:
            path = "django_mysql.models.FixedCharField"

        return name, path, args, kwargs

    def db_type(self, connection: BaseDatabaseWrapper) -> str:
        return f"CHAR({self.max_length})"
