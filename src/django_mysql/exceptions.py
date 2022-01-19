from __future__ import annotations


class TimeoutError(Exception):
    """
    Indicates a database operation timed out in some way.
    """
