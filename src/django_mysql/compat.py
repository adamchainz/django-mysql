from __future__ import annotations

import sys
from typing import Any, Callable, TypeVar, cast

import django

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
