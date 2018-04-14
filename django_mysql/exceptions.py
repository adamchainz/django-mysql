# -*- coding:utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals,
)


class TimeoutError(Exception):
    """
    Indicates a database operation timed out in some way.
    """
    pass
