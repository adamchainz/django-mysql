from __future__ import annotations

from typing import Any, cast

import django
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.models import CharField
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from django_mysql.typing import DeconstructResult


class EnumField(CharField):
    description = _("Enumeration")

    if django.VERSION >= (4, 1):
        non_db_attrs = tuple(f for f in CharField.non_db_attrs if f != "choices")

    def __init__(
        self,
        *args: Any,
        choices: list[str | tuple[str, str]],
        **kwargs: Any,
    ) -> None:
        if len(choices) == 0:
            raise ValueError('"choices" argument must be be a non-empty list')

        reformatted_choices: list[tuple[str, str]] = []
        for choice in choices:
            if isinstance(choice, tuple):
                reformatted_choices.append(choice)
            elif isinstance(choice, str):
                reformatted_choices.append((choice, choice))
            else:
                raise TypeError(
                    'Invalid choice "{choice}". '
                    "Expected string or tuple as elements in choices".format(
                        choice=choice
                    )
                )

        if "max_length" in kwargs:
            raise TypeError('"max_length" is not a valid argument')
        # Massive to avoid problems with validation - let MySQL handle the
        # maximum string length
        kwargs["max_length"] = int(2**32)

        super().__init__(*args, choices=reformatted_choices, **kwargs)

    def deconstruct(self) -> DeconstructResult:
        name, path, args, kwargs = cast(DeconstructResult, super().deconstruct())

        bad_paths = (
            "django_mysql.models.fields.enum.EnumField",
            "django_mysql.models.fields.EnumField",
        )
        if path in bad_paths:
            path = "django_mysql.models.EnumField"

        kwargs["choices"] = self.choices
        del kwargs["max_length"]

        return name, path, args, kwargs

    def db_type(self, connection: BaseDatabaseWrapper) -> str:
        connection.ensure_connection()
        values = [connection.connection.escape_string(c) for c, _ in self.flatchoices]
        # Use force_str because MySQLdb escape_string() returns bytes, but
        # pymysql returns str
        return "enum(%s)" % ",".join("'%s'" % force_str(v) for v in values)
