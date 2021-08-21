import sys

import django

if sys.version_info >= (3, 7):
    from contextlib import nullcontext
else:

    class nullcontext:
        def __enter__(self):
            pass

        def __exit__(self, *exc_info):
            pass


if django.VERSION >= (3, 1):
    from django.db.models import JSONField

    HAVE_JSONFIELD = True
else:
    try:
        from django_jsonfield_backport.models import JSONField  # noqa: F401

        HAVE_JSONFIELD = True
    except ImportError:
        HAVE_JSONFIELD = False
