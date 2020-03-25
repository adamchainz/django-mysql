import sys

if sys.version_info >= (3, 7):
    from contextlib import nullcontext
else:

    class nullcontext:
        def __enter__(self):
            pass

        def __exit__(self, *exc_info):
            pass
