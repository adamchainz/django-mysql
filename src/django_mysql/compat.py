import sys
from types import TracebackType
from typing import Any, Callable, Optional, Type, TypeVar, cast

import django

if sys.version_info >= (3, 7):
    from contextlib import nullcontext
else:

    class nullcontext:
        def __enter__(self) -> None:
            pass

        def __exit__(
            self,
            exc_type: Optional[Type[BaseException]],
            exc_value: Optional[BaseException],
            exc_traceback: Optional[TracebackType],
        ) -> None:
            pass


if sys.version_info >= (3, 9):
    from functools import cache
else:
    from functools import lru_cache

    _F = TypeVar("_F", bound=Callable[..., Any])

    def cache(func: _F) -> _F:
        return cast(_F, lru_cache(maxsize=None)(func))


if django.VERSION >= (3, 1):
    from django.db.models import JSONField

    HAVE_JSONFIELD = True
else:
    try:
        from django_jsonfield_backport.models import JSONField  # noqa: F401

        HAVE_JSONFIELD = True
    except ImportError:  # pragma: no cover
        HAVE_JSONFIELD = False
