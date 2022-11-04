from __future__ import annotations

import sys
from typing import Any
from typing import Callable
from typing import cast
from typing import TypeVar

if sys.version_info >= (3, 9):
    from functools import cache
else:
    from functools import lru_cache

    _F = TypeVar("_F", bound=Callable[..., Any])

    def cache(func: _F) -> _F:
        return cast(_F, lru_cache(maxsize=None)(func))
