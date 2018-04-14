# -*- coding:utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals,
)

import re
import zlib
from random import random
from textwrap import dedent
from time import time

from django.core.cache.backends.base import (
    DEFAULT_TIMEOUT, BaseCache, default_key_func,
)
from django.db import connections, router
from django.utils import six
from django.utils.encoding import force_bytes
from django.utils.module_loading import import_string

from django_mysql.utils import collapse_spaces, get_list_sql

try:
    from django.utils.six.moves import cPickle as pickle
except ImportError:  # pragma: no cover
    import pickle


BIGINT_SIGNED_MIN = -9223372036854775808
BIGINT_SIGNED_MAX = 9223372036854775807
BIGINT_UNSIGNED_MAX = 18446744073709551615


# Slightly modified copies of Options/BaseDatabaseCache from django's
# cache.backends.db - these allow us to act like a separate app for database
# routers (django_mysql), and not appear on django's `createcachetable`
# command

class Options(object):
    """A class that will quack like a Django model _meta class.

    This allows cache operations to be controlled by the router
    """
    def __init__(self, table):
        self.db_table = table
        self.app_label = 'django_mysql'
        self.model_name = 'cacheentry'
        self.verbose_name = 'cache entry'
        self.verbose_name_plural = 'cache entries'
        self.object_name = 'CacheEntry'
        self.abstract = False
        self.managed = True
        self.proxy = False
        self.swapped = False


class BaseDatabaseCache(BaseCache):
    def __init__(self, table, params):
        super(BaseDatabaseCache, self).__init__(params)
        self._table = table

        class CacheEntry(object):
            _meta = Options(table)
        self.cache_model_class = CacheEntry


reverse_key_re = re.compile(r'^([^:]*):(\d+):(.*)')


def default_reverse_key_func(full_key):
    """
    Reverse of Django's default_key_func, i.e. undoing:

        def default_key_func(key, key_prefix, version):
            return '%s:%s:%s' % (key_prefix, version, key)
    """
    match = reverse_key_re.match(full_key)
    return match.group(3), match.group(1), int(match.group(2))


def get_reverse_key_func(reverse_key_func):
    """
    Function to decide which reverse key function to use

    Defaults to ``None``, as any other value might not apply to the given
    KEY_FUNCTION. Also the user may not use any of the operations that require
    reversing the key_func.
    """
    if reverse_key_func is not None:
        if callable(reverse_key_func):
            return reverse_key_func
        else:
            return import_string(reverse_key_func)
    return None


class MySQLCache(BaseDatabaseCache):

    # Got an error with the add() query using BIGINT_UNSIGNED_MAX, so use a
    # value slightly 1 bit less (still an incalculable time into the future of
    # 1970)
    FOREVER_TIMEOUT = BIGINT_UNSIGNED_MAX >> 1

    create_table_sql = dedent('''\
        CREATE TABLE `{table_name}` (
            cache_key varchar(255) CHARACTER SET utf8 COLLATE utf8_bin
                                   NOT NULL PRIMARY KEY,
            value longblob NOT NULL,
            value_type char(1) CHARACTER SET latin1 COLLATE latin1_bin
                               NOT NULL DEFAULT 'p',
            expires BIGINT UNSIGNED NOT NULL
        );
    ''')

    @classmethod
    def _now(cls):
        # Values in the expires column are milliseconds since unix epoch (UTC)
        return int(time() * 1000)

    def __init__(self, table, params):
        super(MySQLCache, self).__init__(table, params)
        options = params.get('OPTIONS', {})
        self._compress_min_length = options.get('COMPRESS_MIN_LENGTH', 5000)
        self._compress_level = options.get('COMPRESS_LEVEL', 6)
        self._cull_probability = options.get('CULL_PROBABILITY', 0.01)

        # Figure out our *reverse* key function
        if self.key_func is default_key_func:
            self.reverse_key_func = default_reverse_key_func
            if ':' in self.key_prefix:
                raise ValueError(
                    "Cannot use the default KEY_FUNCTION and "
                    "REVERSE_KEY_FUNCTION if you have a colon in your "
                    "KEY_PREFIX.",
                )
        else:
            reverse_key_func = params.get('REVERSE_KEY_FUNCTION', None)
            self.reverse_key_func = get_reverse_key_func(reverse_key_func)

    # Django API + helpers

    def get(self, key, default=None, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        db = router.db_for_read(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        with connections[db].cursor() as cursor:
            cursor.execute(
                self._get_query.format(table=table),
                (key, self._now()),
            )
            row = cursor.fetchone()

        if row is None:
            return default
        else:
            value, value_type = row
            return self.decode(value, value_type)

    _get_query = collapse_spaces("""
        SELECT value, value_type
        FROM {table}
        WHERE cache_key = %s AND
              expires >= %s
    """)

    def get_many(self, keys, version=None):
        made_key_to_key = {
            self.make_key(key, version=version): key
            for key in keys
        }
        made_keys = list(made_key_to_key.keys())
        for key in made_keys:
            self.validate_key(key)

        db = router.db_for_read(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        with connections[db].cursor() as cursor:
            cursor.execute(
                self._get_many_query.format(
                    table=table,
                    list_sql=get_list_sql(made_keys),
                ),
                made_keys + [self._now()],
            )
            rows = cursor.fetchall()

        data = {}

        for made_key, value, value_type in rows:
            key = made_key_to_key[made_key]
            data[key] = self.decode(value, value_type)

        return data

    _get_many_query = collapse_spaces("""
        SELECT cache_key, value, value_type
        FROM {table}
        WHERE cache_key IN {list_sql} AND
              expires >= %s
    """)

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        self._base_set('set', key, value, timeout)

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        return self._base_set('add', key, value, timeout)

    def _base_set(self, mode, key, value, timeout=DEFAULT_TIMEOUT):
        if mode not in ('set', 'add'):
            raise ValueError("'mode' should be 'set' or 'add'")

        exp = self.get_backend_timeout(timeout)
        db = router.db_for_write(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        self._maybe_cull()
        with connections[db].cursor() as cursor:

            value, value_type = self.encode(value)

            if mode == 'set':
                query = self._set_query
                params = (key, value, value_type, exp)
            else:  # mode = 'add'
                query = self._add_query
                params = (key, value, value_type, exp, self._now())

            cursor.execute(query.format(table=table), params)

            if mode == 'set':
                return True
            else:  # mode = 'add'
                # Use a special code in the add query for "did insert"
                insert_id = cursor.lastrowid
                return (insert_id != 444)

    _set_many_query = collapse_spaces("""
        INSERT INTO {table} (cache_key, value, value_type, expires)
        VALUES {{VALUES_CLAUSE}}
        ON DUPLICATE KEY UPDATE
            value=VALUES(value),
            value_type=VALUES(value_type),
            expires=VALUES(expires)
    """)

    _set_query = _set_many_query.replace('{{VALUES_CLAUSE}}',
                                         '(%s, %s, %s, %s)')

    # Uses the IFNULL / LEAST / LAST_INSERT_ID trick to communicate the special
    # value of 444 back to the client (LAST_INSERT_ID is otherwise 0, since
    # there is no AUTO_INCREMENT column)
    _add_query = collapse_spaces("""
        INSERT INTO {table} (cache_key, value, value_type, expires)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            value=IF(expires > @tmp_now:=%s, value, VALUES(value)),
            value_type=IF(expires > @tmp_now, value_type, VALUES(value_type)),
            expires=IF(
                expires > @tmp_now,
                IFNULL(
                    LEAST(LAST_INSERT_ID(444), NULL),
                    expires
                ),
                VALUES(expires)
            )
    """)

    def set_many(self, data, timeout=DEFAULT_TIMEOUT, version=None):
        exp = self.get_backend_timeout(timeout)
        db = router.db_for_write(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        self._maybe_cull()

        params = []
        for key, value in six.iteritems(data):
            made_key = self.make_key(key, version=version)
            self.validate_key(made_key)
            value, value_type = self.encode(value)
            params.extend((made_key, value, value_type, exp))

        query = self._set_many_query.replace(
            '{{VALUES_CLAUSE}}',
            ','.join('(%s, %s, %s, %s)' for key in data),
        ).format(table=table)

        with connections[db].cursor() as cursor:
            cursor.execute(query, params)
        return []

    def delete(self, key, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)

        db = router.db_for_write(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        with connections[db].cursor() as cursor:
            cursor.execute(self._delete_query.format(table=table), (key,))

    _delete_query = collapse_spaces("""
        DELETE FROM {table}
        WHERE cache_key = %s
    """)

    def delete_many(self, keys, version=None):
        made_keys = [self.make_key(key, version=version) for key in keys]
        for key in made_keys:
            self.validate_key(key)

        db = router.db_for_write(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        with connections[db].cursor() as cursor:
            cursor.execute(
                self._delete_many_query.format(
                    table=table,
                    list_sql=get_list_sql(made_keys),
                ),
                made_keys,
            )

    _delete_many_query = collapse_spaces("""
        DELETE FROM {table}
        WHERE cache_key IN {list_sql}
    """)

    def has_key(self, key, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)

        db = router.db_for_read(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        with connections[db].cursor() as cursor:
            cursor.execute(
                self._has_key_query.format(table=table),
                (key, self._now()),
            )
            return cursor.fetchone() is not None

    _has_key_query = collapse_spaces("""
        SELECT 1 FROM {table}
        WHERE cache_key = %s and expires > %s
    """)

    def incr(self, key, delta=1, version=None):
        return self._base_delta(key, delta, version, '+')

    def decr(self, key, delta=1, version=None):
        return self._base_delta(key, delta, version, '-')

    def _base_delta(self, key, delta, version, operation):
        key = self.make_key(key, version=version)
        self.validate_key(key)

        db = router.db_for_write(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        with connections[db].cursor() as cursor:
            updated = cursor.execute(
                self._delta_query.format(table=table, operation=operation),
                (delta, key),
            )

            if not updated:
                raise ValueError("Key '%s' not found, or not an integer" % key)

            # New value stored in insert_id
            return cursor.lastrowid

    # Looks a bit tangled to turn the blob back into an int for updating, but
    # it works. Stores the new value for insert_id() with LAST_INSERT_ID
    _delta_query = collapse_spaces("""
        UPDATE {table}
        SET value = LAST_INSERT_ID(
            CAST(value AS SIGNED INTEGER)
            {operation}
            %s
        )
        WHERE cache_key = %s AND
              value_type = 'i'
    """)

    def clear(self):
        db = router.db_for_write(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)
        with connections[db].cursor() as cursor:
            cursor.execute("DELETE FROM {table}".format(table=table))

    def validate_key(self, key):
        """
        Django normally warns about maximum key length, but we error on it.
        """
        if len(key) > 250:
            raise ValueError(
                "Cache key is longer than the maxmimum 250 characters: {}"
                .format(key),
            )
        return super(MySQLCache, self).validate_key(key)

    def encode(self, obj):
        """
        Take a Python object and return it as a tuple (value, value_type), a
        blob and a one-char code for what type it is
        """
        if self._is_valid_mysql_bigint(obj):
            return obj, 'i'

        value = pickle.dumps(obj, pickle.HIGHEST_PROTOCOL)
        value_type = 'p'
        if (
            self._compress_min_length and
            len(value) >= self._compress_min_length
        ):
            value = zlib.compress(value, self._compress_level)
            value_type = 'z'
        return value, value_type

    def _is_valid_mysql_bigint(self, value):
        return(
            # Can't support int/long subclasses since they should are expected
            # to decode back to the same object
            (type(value) in six.integer_types) and
            # Can't go beyond these ranges
            BIGINT_SIGNED_MIN <= value <= BIGINT_SIGNED_MAX
        )

    def decode(self, value, value_type):
        """
        Take a value blob and its value_type one-char code and convert it back
        to a python object
        """
        if value_type == 'i':
            return int(value)

        if value_type == 'z':
            value = zlib.decompress(value)
            value_type = 'p'

        if value_type == 'p':
            return pickle.loads(force_bytes(value))

        raise ValueError(
            "Unknown value_type '{}' read from the cache table."
            .format(value_type),
        )

    def _maybe_cull(self):
        # Roll the dice, if it says yes then cull
        if self._cull_probability and random() <= self._cull_probability:
            self.cull()

    def get_backend_timeout(self, timeout=DEFAULT_TIMEOUT):
        if timeout is None:
            return self.FOREVER_TIMEOUT
        timeout = super(MySQLCache, self).get_backend_timeout(timeout)
        return int(timeout * 1000)

    # Our API extensions

    def keys_with_prefix(self, prefix, version=None):
        if self.reverse_key_func is None:
            raise ValueError(
                "To use the _with_prefix commands with a custom KEY_FUNCTION, "
                "you need to specify a custom REVERSE_KEY_FUNCTION too.",
            )

        if version is None:
            version = self.version

        db = router.db_for_read(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        prefix = self.make_key(prefix + '%', version=version)

        with connections[db].cursor() as cursor:
            cursor.execute(
                """SELECT cache_key FROM {table}
                   WHERE cache_key LIKE %s AND
                         expires >= %s""".format(table=table),
                (prefix, self._now()),
            )
            rows = cursor.fetchall()
            full_keys = {row[0] for row in rows}

            keys = {}
            for full_key in full_keys:
                key, key_prefix, key_version = self.reverse_key_func(full_key)

                if key_version == version:
                    keys[key] = key_version
            return set(six.iterkeys(keys))

    def get_with_prefix(self, prefix, version=None):
        if self.reverse_key_func is None:
            raise ValueError(
                "To use the _with_prefix commands with a custom KEY_FUNCTION, "
                "you need to specify a custom REVERSE_KEY_FUNCTION too.",
            )

        if version is None:
            version = self.version

        db = router.db_for_read(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        prefix = self.make_key(prefix + '%', version=version)
        version = six.text_type(version)

        with connections[db].cursor() as cursor:
            cursor.execute(
                """SELECT cache_key, value, value_type
                   FROM {table}
                   WHERE cache_key LIKE %s AND
                         expires >= %s""".format(table=table),
                (prefix, self._now()),
            )
            rows = cursor.fetchall()

            data = {}
            for made_key, value, value_type in rows:
                key, key_prefix, key_version = self.reverse_key_func(made_key)
                data[key] = self.decode(value, value_type)

            return data

    def delete_with_prefix(self, prefix, version=None):
        if version is None:
            version = self.version

        db = router.db_for_write(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        prefix = self.make_key(prefix + '%', version=version)

        with connections[db].cursor() as cursor:
            return cursor.execute(
                """DELETE FROM {table}
                   WHERE cache_key LIKE %s""".format(table=table),
                (prefix,),
            )

    def cull(self):
        db = router.db_for_write(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        with connections[db].cursor() as cursor:
            # First, try just deleting expired keys
            num_deleted = cursor.execute(
                "DELETE FROM {table} WHERE expires < %s".format(table=table),
                (self._now(),),
            )

            # -1 means "Don't limit size"
            if self._max_entries == -1:
                return

            cursor.execute("SELECT COUNT(*) FROM {table}".format(table=table))
            num = cursor.fetchone()[0]

            if num < self._max_entries:
                return num_deleted

            # Now do a key-based cull
            if self._cull_frequency == 0:
                num_deleted += cursor.execute(
                    "DELETE FROM {table}".format(table=table),
                )
            else:
                cull_num = num // self._cull_frequency
                cursor.execute(
                    """SELECT cache_key FROM {table}
                       ORDER BY cache_key
                       LIMIT 1 OFFSET %s""".format(table=table),
                    (cull_num,),
                )
                max_key = cursor.fetchone()[0]
                num_deleted += cursor.execute(
                    """DELETE FROM {table}
                       WHERE cache_key < %s""".format(table=table),
                    (max_key,),
                )
            return num_deleted
