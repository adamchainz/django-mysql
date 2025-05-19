from __future__ import annotations

import uuid
from functools import wraps
from types import TracebackType
from typing import Any

from django.db import connections
from django.db.utils import DEFAULT_DB_ALIAS


class override_mysql_variables:
    """
    Based on Django's override_settings, but for connection settings. Give a
    connection alias in using and variable=value pairs to save on that
    connection. Keeps the old values MySQL-side using session variables of the
    form @overridden_X.

    Acts as either a decorator, or a context manager. If it's a decorator it
    takes a function and returns a wrapped function. If it's a contextmanager
    it's used with the ``with`` statement. In either event entering/exiting
    are called before and after, respectively, the function/block is executed.
    """

    def __init__(self, using: str = DEFAULT_DB_ALIAS, **options: str | int) -> None:
        self.db = using
        self.options = options
        self.prefix: str = uuid.uuid1().hex.replace("-", "")[:16]

    def __enter__(self) -> None:
        self.enable()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: TracebackType | None,
    ) -> None:
        self.disable()

    def __call__(self, test_func: Any) -> Any:
        from unittest import TestCase

        if isinstance(test_func, type):
            if not issubclass(test_func, TestCase):
                raise TypeError(
                    f"{self.__class__.__name__} only works with TestCase classes."
                )

            self.wrap_class(test_func)

            return test_func
        else:

            @wraps(test_func)
            def inner(*args: Any, **kwargs: Any) -> Any:
                with self:
                    return test_func(*args, **kwargs)

            return inner

    def wrap_class(self, klass: type[Any]) -> None:
        kwargs: dict[str, Any] = {"using": self.db, **self.options}

        for name in dir(klass):
            if not name.startswith("test_"):
                continue

            method = getattr(klass, name)
            # Reconstruct self over and over on each method
            wrapped = self.__class__(**kwargs)(method)
            setattr(klass, name, wrapped)

    def enable(self) -> None:
        with connections[self.db].cursor() as cursor:
            for key, value in self.options.items():
                cursor.execute(
                    f"""SET @overridden_{self.prefix}_{key} = @@{key},
                           @@{key} = %s
                    """,
                    (value,),
                )

    def disable(self) -> None:
        with connections[self.db].cursor() as cursor:
            for key in self.options:
                cursor.execute(
                    f"""SET @@{key} = @overridden_{self.prefix}_{key},
                           @overridden_{self.prefix}_{key} = NULL
                    """
                )
