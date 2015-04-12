from datetime import datetime

from django.conf import settings
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.core.cache.backends.db import BaseDatabaseCache
from django.db import connections, router
from django.utils import timezone
from django.utils.encoding import force_bytes

from django_mysql.utils import collapse_spaces

try:
    from django.utils.six.moves import cPickle as pickle
except ImportError:  # pragma: no cover
    import pickle


try:
    from MySQLdb import Warning as MySQLWarning
except ImportError:  # pragma: no cover
    # Uh-oh, we aren't using MySQLdb/mysqlclient, just fake it
    class MySQLWarning(Warning):
        pass


class MySQLCache(BaseDatabaseCache):

    def get(self, key, default=None, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        db = router.db_for_read(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        with connections[db].cursor() as cursor:
            cursor.execute(self._get_query.format(table_name=table), (key,))
            row = cursor.fetchone()
        if row is None:
            return default
        now = timezone.now()
        expires = row[2]

        if expires < now:
            return default

        blob = connections[db].ops.process_clob(row[1])
        return self._decode(blob)

    _get_query = collapse_spaces("""
        SELECT cache_key, value, expires
        FROM {table_name}
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
                self._get_many_query.format(table_name=table),
                (made_keys,)
            )
            rows = cursor.fetchall()

        d = {}
        now = timezone.now()

        for made_key, value, expires in rows:
            if expires < now:
                continue

            value = connections[db].ops.process_clob(value)
            key = made_key_to_key[made_key]
            d[key] = self._decode(value)

        return d

    _get_many_query = collapse_spaces("""
        SELECT cache_key, value, expires
        FROM {table_name}
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
        timeout = self.get_backend_timeout(timeout)
        db = router.db_for_write(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        with connections[db].cursor() as cursor:
            now = timezone.now()
            now = now.replace(microsecond=0)
            if timeout is None:
                exp = datetime.max
            elif settings.USE_TZ:
                exp = datetime.utcfromtimestamp(timeout)
            else:
                exp = datetime.fromtimestamp(timeout)
            exp = exp.replace(microsecond=0)
            blob = self._encode(value)

            exp = connections[db].ops.value_to_db_datetime(exp)

            if mode == 'set':
                query = self._set_query
                params = (key, blob, exp)
            elif mode == 'add':
                query = self._add_query
                now = connections[db].ops.value_to_db_datetime(now)
                params = (key, blob, exp, now)

            cursor.execute(
                query.format(table_name=table),
                params
            )

            if mode == 'set':
                return True
            elif mode == 'add':
                # Unwrap the onion skin around MySQLdb to get the genuine
                # connection
                mysqldb_connection = cursor.cursor.cursor.connection()
                # Use a special code in the add query for "did insert"
                insert_id = mysqldb_connection.insert_id()
                return (insert_id != 444)

    _set_query = collapse_spaces("""
        INSERT INTO {table_name} (cache_key, value, expires)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            value=VALUES(value),
            expires=VALUES(expires)
    """)

    # Uses the IFNULL / LEAST / LAST_INSERT_ID trick to communicate the special
    # value of 444 back to the client (LAST_INSERT_ID is otherwise 0, since
    # there is no AUTO_INCREMENT column)
    _add_query = collapse_spaces("""
        INSERT INTO {table_name} (cache_key, value, expires)
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

    def delete(self, key, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)

        db = router.db_for_write(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        with connections[db].cursor() as cursor:
            cursor.execute(
                """DELETE FROM {table_name}
                   WHERE cache_key = %s""".format(table_name=table),
                (key,)
            )

    def delete_many(self, keys, version=None):
        made_keys = [self.make_key(key, version=version) for key in keys]
        for key in made_keys:
            self.validate_key(key)

        db = router.db_for_write(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        with connections[db].cursor() as cursor:
            cursor.execute(
                """DELETE FROM {table_name}
                   WHERE cache_key IN %s""".format(table_name=table),
                (made_keys,)
            )

    def has_key(self, key, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)

        db = router.db_for_read(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        if settings.USE_TZ:
            now = datetime.utcnow()
        else:
            now = datetime.now()
        now = now.replace(microsecond=0)

        with connections[db].cursor() as cursor:
            cursor.execute(
                """SELECT cache_key FROM %s
                   WHERE cache_key = %%s and expires > %%s""" % table,
                (key, connections[db].ops.value_to_db_datetime(now))
            )
            return cursor.fetchone() is not None

    def clear(self):
        db = router.db_for_write(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)
        with connections[db].cursor() as cursor:
            cursor.execute('DELETE FROM %s' % table)

    def validate_key(self, key):
        """
        Django normally warns about maximum key length, but we error on it.
        """
        if len(key) > 250:
            raise ValueError(
                'Cache key is longer than the maxmimum 250 characters: {}'
                .format(key)
            )
        return super(MySQLCache, self).validate_key(key)

    def _encode(self, value):
        return pickle.dumps(value, pickle.HIGHEST_PROTOCOL)

    def _decode(self, value):
        return pickle.loads(force_bytes(value))
