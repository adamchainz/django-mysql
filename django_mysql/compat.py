# -*- coding:utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals,
)

try:
    # Django 1.11+
    from django.utils.text import format_lazy

    def lazy_string_concat(*strings):
        return format_lazy('{}' * len(strings), *strings)

except ImportError:
    from django.utils.translation import string_concat as lazy_string_concat


__all__ = ['lazy_string_concat']
