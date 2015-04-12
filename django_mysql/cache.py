import time
import zlib

from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.core.cache.backends.db import BaseDatabaseCache
from django.db import connections, router
from django.utils import six
from django.utils.encoding import force_bytes

from django_mysql.utils import collapse_spaces

try:
    from django.utils.six.moves import cPickle as pickle
except ImportError:  # pragma: no cover
    import pickle


BIGINT_UNSIGNED_MAX = 18446744073709551615


class MySQLCache(BaseDatabaseCache):

    FOREVER_TIMEOUT = BIGINT_UNSIGNED_MAX >> 1

    def __init__(self, table, params):
        super(MySQLCache, self).__init__(table, params)
        options = params.get('OPTIONS', {})
        self._compress_min_length = options.get('COMPRESS_MIN_LENGTH', 5000)
        self._compress_level = options.get('COMPRESS_LEVEL', 6)

    def get(self, key, default=None, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        db = router.db_for_read(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        with connections[db].cursor() as cursor:
            cursor.execute(self._get_query.format(table=table), (key,))
            row = cursor.fetchone()

        if row is None:
            return default

        now = int(time.time() * 1000)
        value, expires = row

        if expires < now:
            return default

        return self._decode(value)

    _get_query = collapse_spaces("""
        SELECT value, expires
        FROM {table}
        WHERE cache_key = %s
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
                self._get_many_query.format(table=table),
                (made_keys,)
            )
            rows = cursor.fetchall()

        d = {}
        now = int(time.time() * 1000)

        for made_key, value, expires in rows:
            if expires < now:
                continue

            key = made_key_to_key[made_key]
            d[key] = self._decode(value)

        return d

    _get_many_query = collapse_spaces("""
        SELECT cache_key, value, expires
        FROM {table}
        WHERE cache_key IN %s
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
        exp = self.get_backend_timeout(timeout)
        db = router.db_for_write(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        with connections[db].cursor() as cursor:
            now = int(time.time() * 1000)

            value = self._encode(value)

            if mode == 'set':
                query = self._set_query
                params = (key, value, exp)
            elif mode == 'add':
                query = self._add_query
                params = (key, value, exp, now)

            cursor.execute(query.format(table=table), params)

            if mode == 'set':
                return True
            elif mode == 'add':
                # Unwrap the onion skin around MySQLdb to get the genuine
                # connection
                mysqldb_connection = cursor.cursor.cursor.connection()
                # Use a special code in the add query for "did insert"
                insert_id = mysqldb_connection.insert_id()
                return (insert_id != 444)

    _set_many_query = collapse_spaces("""
        INSERT INTO {table} (cache_key, value, expires)
        VALUES {{VALUES_CLAUSE}}
        ON DUPLICATE KEY UPDATE
            value=VALUES(value),
            expires=VALUES(expires)
    """)

    _set_query = _set_many_query.replace('{{VALUES_CLAUSE}}', '(%s, %s, %s)')

    # Uses the IFNULL / LEAST / LAST_INSERT_ID trick to communicate the special
    # value of 444 back to the client (LAST_INSERT_ID is otherwise 0, since
    # there is no AUTO_INCREMENT column)
    _add_query = collapse_spaces("""
        INSERT INTO {table} (cache_key, value, expires)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            value=IF(expires > @tmp_now:=%s, value, VALUES(value)),
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

        params = []
        for key, value in six.iteritems(data):
            made_key = self.make_key(key, version=version)
            self.validate_key(made_key)
            value = self._encode(value)
            params.extend((made_key, value, exp))

        query = self._set_many_query.replace(
            '{{VALUES_CLAUSE}}',
            ','.join('(%s, %s, %s)' for key in data)
        ).format(table=table)

        with connections[db].cursor() as cursor:
            cursor.execute(query, params)

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
                self._delete_many_query.format(table=table),
                (made_keys,)
            )

    _delete_many_query = collapse_spaces("""
        DELETE FROM {table}
        WHERE cache_key IN %s
    """)

    def has_key(self, key, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)

        db = router.db_for_read(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        now = int(time.time() * 1000)

        with connections[db].cursor() as cursor:
            cursor.execute(
                """SELECT cache_key FROM %s
                   WHERE cache_key = %%s and expires > %%s""" % table,
                (key, now)
            )
            return cursor.fetchone() is not None

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
                .format(key)
            )
        return super(MySQLCache, self).validate_key(key)

    def _encode(self, value):
        value = pickle.dumps(value, pickle.HIGHEST_PROTOCOL)
        if (
            self._compress_min_length and
            len(value) >= self._compress_min_length
        ):
            value = zlib.compress(value, self._compress_level)
        return value

    def _decode(self, value):
        try:
            value = zlib.decompress(value)
        except zlib.error as e:
            # Not zlib data
            if not str(e).endswith('incorrect header check'):
                raise

        return pickle.loads(force_bytes(value))

    def get_backend_timeout(self, timeout=DEFAULT_TIMEOUT):
        if timeout is None:
            return self.FOREVER_TIMEOUT
        timeout = super(MySQLCache, self).get_backend_timeout(timeout)
        return int(timeout * 1000)
