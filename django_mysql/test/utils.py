import uuid
from functools import wraps

from django.db import connections
from django.db.utils import DEFAULT_DB_ALIAS
from django.utils import six

from django_mysql.status import GlobalStatus


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
        self.prefix = uuid.uuid1().hex.replace('-', '')

    def __enter__(self):
        self.enable()

    def __exit__(self, exc_type, exc_value, traceback):
        self.disable()

    def __call__(self, test_func):
        from unittest import TestCase
        if isinstance(test_func, six.class_types):
            if not issubclass(test_func, TestCase):
                raise Exception(
                    "{} only works with TestCase classes."
                    .format(self.__class__.__name__)
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
        kwargs = {'using': self.db}
        kwargs.update(**self.options)

        for name in dir(klass):
            if not name.startswith('test_'):
                continue

            method = getattr(klass, name)
            # Reconstruct self over and over on each method
            wrapped = self.__class__(**kwargs)(method)
            setattr(klass, name, wrapped)

    def enable(self):
        with connections[self.db].cursor() as cursor:

            for key, value in six.iteritems(self.options):
                cursor.execute(
                    """SET @overridden_{prefix}_{name} = @@{name},
                           @@{name} = %s
                    """.format(prefix=self.prefix, name=key),
                    (value,)
                )

    def disable(self):
        with connections[self.db].cursor() as cursor:

            for key in self.options:
                cursor.execute(
                    """SET @@{name} = @overridden_{prefix}_{name},
                           @overridden_{prefix}_{name} = NULL
                    """.format(name=key, prefix=self.prefix)
                )


class assert_mysql_queries(object):
    def __init__(self, using=DEFAULT_DB_ALIAS, full_joins=0):
        self.status = GlobalStatus(using)
        self.full_joins = full_joins

    def __enter__(self):
        self._before = self.status.get_many(self.names)

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            return

        before = self._before
        after = self.status.get_many(self.names)

        count = after['Select_full_join'] - before['Select_full_join']
        if self.full_joins is not None and count > self.full_joins:
            raise AssertionError(
                "{count} full {joins_were} executed - expected 0. Check for "
                "any queries that are joining on non-indexed columns."
                .format(
                    count=count,
                    joins_were='joins were' if count > 1 else 'join was'
                )
            )

    @property
    def names(self):
        return {'Select_full_join'}
