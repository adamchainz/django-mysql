from typing import Any, cast

from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.models import CharField

from django_mysql.typing import DeconstructResult


class FixedCharField(CharField):
    def __init__(self, *args: Any, length: int, **kwargs: Any) -> None:
        # Ensure we have an actual integer value
        if not isinstance(length, int):
            raise TypeError(
                'Invalid length value "{length}". '
                "Expected integer value.".format(length=length)
            )

        # CHAR fields can only be in the range of 0-255
        if length < 0 or length > 255:
            raise ValueError(
                'Invalid length value "{length}". '
                "Length must be in the range of 0-255.".format(length=length)
            )

        # A max_length doesn't make sense in this context
        if "max_length" in kwargs:
            raise TypeError('"max_length" is not a valid argument')

        # However, a max_length is required by Django CharField,
        # so we'll set it equal to the length of our CHAR field
        self.length = length
        kwargs["max_length"] = length
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
        kwargs["max_length"] = self.length

        return name, path, args, kwargs

    def db_type(self, connection: BaseDatabaseWrapper) -> str:
        return f"char({self.length})"
