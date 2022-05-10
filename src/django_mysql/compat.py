from __future__ import annotations

import sys
from typing import Any, Callable, TypeVar, cast

if sys.version_info >= (3, 9):
    from functools import cache
else:
    from functools import lru_cache

    _F = TypeVar("_F", bound=Callable[..., Any])

    def cache(func: _F) -> _F:
        return cast(_F, lru_cache(maxsize=None)(func))
