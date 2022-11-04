from __future__ import annotations

from django.core.validators import MaxLengthValidator
from django.core.validators import MinLengthValidator
from django.utils.translation import ngettext_lazy


class ListMaxLengthValidator(MaxLengthValidator):
    message = ngettext_lazy(
        "List contains %(show_value)d item, "
        "it should contain no more than %(limit_value)d.",
        "List contains %(show_value)d items, "
        "it should contain no more than %(limit_value)d.",
        "limit_value",
    )


class ListMinLengthValidator(MinLengthValidator):
    message = ngettext_lazy(
        "List contains %(show_value)d item, "
        "it should contain no fewer than %(limit_value)d.",
        "List contains %(show_value)d items, "
        "it should contain no fewer than %(limit_value)d.",
        "limit_value",
    )


class SetMaxLengthValidator(MaxLengthValidator):
    message = ngettext_lazy(
        "Set contains %(show_value)d item, "
        "it should contain no more than %(limit_value)d.",
        "Set contains %(show_value)d items, "
        "it should contain no more than %(limit_value)d.",
        "limit_value",
    )


class SetMinLengthValidator(MinLengthValidator):
    message = ngettext_lazy(
        "Set contains %(show_value)d item, "
        "it should contain no fewer than %(limit_value)d.",
        "Set contains %(show_value)d items, "
        "it should contain no fewer than %(limit_value)d.",
        "limit_value",
    )
