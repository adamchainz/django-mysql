import uuid
from functools import wraps

from django.db import connections
from django.db.utils import DEFAULT_DB_ALIAS


class override_mysql_variables:
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
        self.prefix = uuid.uuid1().hex.replace("-", "")[:16]

    def __enter__(self):
        self.enable()

    def __exit__(self, exc_type, exc_value, traceback):
        self.disable()

    def __call__(self, test_func):
        from unittest import TestCase

        if isinstance(test_func, type):
            if not issubclass(test_func, TestCase):
                raise Exception(
                    "{} only works with TestCase classes.".format(
                        self.__class__.__name__
                    )
                )

            self.wrap_class(test_func)

            return test_func
        else:

            @wraps(test_func)
            def inner(*args, **kwargs):
                with self:
                    return test_func(*args, **kwargs)

            return inner

    def wrap_class(self, klass):
        kwargs = {"using": self.db}
        kwargs.update(**self.options)

        for name in dir(klass):
            if not name.startswith("test_"):
                continue

            method = getattr(klass, name)
            # Reconstruct self over and over on each method
            wrapped = self.__class__(**kwargs)(method)
            setattr(klass, name, wrapped)

    def enable(self):
        with connections[self.db].cursor() as cursor:

            for key, value in self.options.items():
                cursor.execute(
                    """SET @overridden_{prefix}_{name} = @@{name},
                           @@{name} = %s
                    """.format(
                        prefix=self.prefix, name=key
                    ),
                    (value,),
                )

    def disable(self):
        with connections[self.db].cursor() as cursor:

            for key in self.options:
                cursor.execute(
                    """SET @@{name} = @overridden_{prefix}_{name},
                           @overridden_{prefix}_{name} = NULL
                    """.format(
                        name=key, prefix=self.prefix
                    )
                )
