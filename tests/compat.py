import django

if django.VERSION >= (3, 2):

    def wrap_testdata(func):
        return func

else:
    from testdata import wrap_testdata  # type: ignore [no-redef]  # noqa: F401
