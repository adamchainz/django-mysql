from typing import Any, cast
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.models import CharField

from django_mysql.typing import DeconstructResult


class FixedCharField(CharField):
    def __init__(self, length: int, *args: Any, **kwargs: Any) -> None:
        # Ensure we have an actual integer value
        if not isinstance(length, int):
            raise TypeError(
                'Invalid length value "{length}".'
                "Expected integer value.".format(length=length)
            )

        # A max_length doesn't make sense in this context
        if "max_length" in kwargs:
            raise TypeError('"max_length" is not a valid argument')

        self.length = length
        super().__init__(*args, **kwargs)

    def deconstruct(self) -> DeconstructResult:
        name, path, args, kwargs = cast(DeconstructResult, super().deconstruct())

        bad_paths = (
            "django_mysql.models.fields.fixedchar.FixedCharField",
            "django_mysql.models.fields.FixedCharField",
        )
        if path in bad_paths:
            path = "django_mysql.models.FixedCharField"

        kwargs["length"] = self.length

        return name, path, args, kwargs

    def db_type(self, connection: BaseDatabaseWrapper) -> str:
        return "char({length})".format(length=self.length)
