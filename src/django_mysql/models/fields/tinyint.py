from __future__ import annotations

from typing import Any, cast

from django.core import checks
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.models import IntegerField

from django_mysql.typing import DeconstructResult


class TinyIntegerField(IntegerField):
    def check(self, **kwargs: Any) -> list[checks.CheckMessage]:
        errors = super().check(**kwargs)

        if isinstance(self.max_length, int) and (
            self.max_length < -128 or self.max_length > 127
        ):
            errors.append(
                checks.Error(
                    "'max_length' must be between -128 and 127.",
                    hint=None,
                    obj=self,
                    id="django_mysql.E015",
                )
            )

        return errors

    def deconstruct(self) -> DeconstructResult:
        name, path, args, kwargs = cast(DeconstructResult, super().deconstruct())

        bad_paths = (
            "django_mysql.models.fields.tinyint.TinyIntegerField",
            "django_mysql.models.fields.TinyIntegerField",
        )
        if path in bad_paths:
            path = "django_mysql.models.TinyIntegerField"

        return name, path, args, kwargs

    def db_type(self, connection: BaseDatabaseWrapper) -> str:
        return "TINYINT"


class PositiveTinyIntegerField(IntegerField):
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
            "django_mysql.models.fields.tinyint.PositiveTinyIntegerField",
            "django_mysql.models.fields.PositiveTinyIntegerField",
        )
        if path in bad_paths:
            path = "django_mysql.models.PositiveTinyIntegerField"

        return name, path, args, kwargs

    def db_type(self, connection: BaseDatabaseWrapper) -> str:
        return "TINYINT UNSIGNED"
