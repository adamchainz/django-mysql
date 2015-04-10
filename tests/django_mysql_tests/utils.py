from contextlib import contextmanager
from functools import wraps
import sys

from django.db import connections
from django.db.utils import DEFAULT_DB_ALIAS
from django.utils import six


@contextmanager
def captured_output(stream_name):
    """Return a context manager used by captured_stdout/stdin/stderr
    that temporarily replaces the sys stream *stream_name* with a StringIO.

    Note: This function and the following ``captured_std*`` are copied
          from CPython's ``test.support`` module."""
    orig_stdout = getattr(sys, stream_name)
    setattr(sys, stream_name, six.StringIO())
    try:
        yield getattr(sys, stream_name)
    finally:
        setattr(sys, stream_name, orig_stdout)


def captured_stdout():
    """Capture the output of sys.stdout:

       with captured_stdout() as stdout:
           print("hello")
       self.assertEqual(stdout.getvalue(), "hello\n")
    """
    return captured_output("stdout")


class override_mysql_variables(object):
    """
    Based on Django's override_settings, but for connection settings. Give a
    connection alias in using and variable=value pairs to save on that
    connection. Keeps the old values MySQL-side using session variables of the
    form @overridden_X.

    Acts as either a decorator, or a context manager. If it's a decorator it
    takes a function and returns a wrapped function. If it's a contextmanager
    it's used with the ``with`` statement. In either event entering/exiting
    are called before and after, respectively, the function/block is executed.
    """
    def __init__(self, using=DEFAULT_DB_ALIAS, **kwargs):
        self.db = using
        self.options = kwargs

    def __enter__(self):
        self.enable()

    def __exit__(self, exc_type, exc_value, traceback):
        self.disable()

    def __call__(self, test_func):
        if isinstance(test_func, type):
            raise Exception("This doesn't work with classes.")
        else:
            @wraps(test_func)
            def inner(*args, **kwargs):
                with self:
                    return test_func(*args, **kwargs)
            return inner

    def save_options(self, test_func):
        if test_func._overridden_settings is None:
            test_func._overridden_settings = self.options
        else:
            # Duplicate dict to prevent subclasses from altering their parent.
            test_func._overridden_settings = dict(
                test_func._overridden_settings, **self.options)

    def enable(self):
        with connections[self.db].cursor() as cursor:

            for key, value in self.options.iteritems():
                cursor.execute(
                    """SET @overridden_{} = @@{},
                           @@{} = %s""".format(key, key, key),
                    (value,)
                )

    def disable(self):
        with connections[self.db].cursor() as cursor:

            for key in self.options:
                cursor.execute(
                    """SET @@{} = @overridden_{},
                           @overridden_{} = NULL""".format(key, key, key)
                )
