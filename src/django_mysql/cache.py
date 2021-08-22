import pickle
import re
import sys
import zlib
from random import random
from textwrap import dedent
from time import time
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    Union,
    cast,
)

from django.core.cache.backends.base import DEFAULT_TIMEOUT, BaseCache, default_key_func
from django.db import connections, router
from django.utils.encoding import force_bytes
from django.utils.module_loading import import_string

from django_mysql.utils import collapse_spaces, get_list_sql

if sys.version_info >= (3, 8):
    from typing import Literal

    _BaseDeltaType = Literal["+", "-"]
    _EncodedKeyType = Literal["i", "p", "z"]
else:
    _BaseDeltaType = str
    _EncodedKeyType = str

BIGINT_SIGNED_MIN = -9223372036854775808
BIGINT_SIGNED_MAX = 9223372036854775807
BIGINT_UNSIGNED_MAX = 18446744073709551615


# Slightly modified copies of Options/BaseDatabaseCache from django's
# cache.backends.db - these allow us to act like a separate app for database
# routers (django_mysql), and not appear on django's `createcachetable`
# command


class Options:
    """A class that will quack like a Django model _meta class.

    This allows cache operations to be controlled by the router
    """

    def __init__(self, table: str) -> None:
        self.db_table = table
        self.app_label = "django_mysql"
        self.model_name = "cacheentry"
        self.verbose_name = "cache entry"
        self.verbose_name_plural = "cache entries"
        self.object_name = "CacheEntry"
        self.abstract = False
        self.managed = True
        self.proxy = False
        self.swapped = False


class BaseDatabaseCache(BaseCache):
    def __init__(self, table: str, params: Dict[str, Any]) -> None:
        super().__init__(params)
        self._table = table

        class CacheEntry:
            _meta = Options(table)

        self.cache_model_class = CacheEntry


reverse_key_re = re.compile(r"^([^:]*):(\d+):(.*)")


def default_reverse_key_func(full_key: str) -> Tuple[str, str, int]:
    """
    Reverse of Django's default_key_func, i.e. undoing:

        def default_key_func(key, key_prefix, version):
            return '%s:%s:%s' % (key_prefix, version, key)
    """
    match = reverse_key_re.match(full_key)
    assert match is not None
    return match.group(3), match.group(1), int(match.group(2))


def get_reverse_key_func(
    reverse_key_func: Optional[Union[str, Callable[[str], Tuple[str, str, int]]]]
) -> Optional[Callable[[str], Tuple[str, str, int]]]:
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
            return cast(
                Callable[[str], Tuple[str, str, int]],
                import_string(reverse_key_func),
            )
    return None


class MySQLCache(BaseDatabaseCache):

    # Got an error with the add() query using BIGINT_UNSIGNED_MAX, so use a
    # value slightly 1 bit less (still an incalculable time into the future of
    # 1970)
    FOREVER_TIMEOUT = BIGINT_UNSIGNED_MAX >> 1

    create_table_sql = dedent(
        """\
        CREATE TABLE `{table_name}` (
            cache_key varchar(255) CHARACTER SET utf8 COLLATE utf8_bin
                                   NOT NULL PRIMARY KEY,
            value longblob NOT NULL,
            value_type char(1) CHARACTER SET latin1 COLLATE latin1_bin
                               NOT NULL DEFAULT 'p',
            expires BIGINT UNSIGNED NOT NULL
        );
    """
    )

    @classmethod
    def _now(cls) -> int:
        # Values in the expires column are milliseconds since unix epoch (UTC)
        return int(time() * 1000)

    reverse_key_func: Optional[Callable[[str], Tuple[str, str, int]]]

    def __init__(self, table: str, params: Dict[str, Any]) -> None:
        super().__init__(table, params)
        options = params.get("OPTIONS", {})
        self._compress_min_length = options.get("COMPRESS_MIN_LENGTH", 5000)
        self._compress_level = options.get("COMPRESS_LEVEL", 6)
        self._cull_probability = options.get("CULL_PROBABILITY", 0.01)

        # Figure out our *reverse* key function
        if self.key_func is default_key_func:
            self.reverse_key_func = default_reverse_key_func
            if ":" in self.key_prefix:
                raise ValueError(
                    "Cannot use the default KEY_FUNCTION and "
                    "REVERSE_KEY_FUNCTION if you have a colon in your "
                    "KEY_PREFIX."
                )
        else:
            reverse_key_func = params.get("REVERSE_KEY_FUNCTION", None)
            self.reverse_key_func = get_reverse_key_func(reverse_key_func)

    # Django API + helpers

    def get(
        self, key: str, default: Optional[Any] = None, version: Optional[int] = None
    ) -> Any:
        key = self.make_key(key, version=version)
        self.validate_key(key)
        db = router.db_for_read(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        with connections[db].cursor() as cursor:
            cursor.execute(self._get_query.format(table=table), (key, self._now()))
            row = cursor.fetchone()

        if row is None:
            return default
        else:
            value, value_type = row
            return self.decode(value, value_type)

    _get_query = collapse_spaces(
        """
        SELECT value, value_type
        FROM {table}
        WHERE cache_key = %s AND
              expires >= %s
    """
    )

    def get_many(
        self, keys: Iterable[str], version: Optional[int] = None
    ) -> Dict[str, Any]:
        made_key_to_key = {self.make_key(key, version=version): key for key in keys}
        made_keys = list(made_key_to_key.keys())
        for key in made_keys:
            self.validate_key(key)

        db = router.db_for_read(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        with connections[db].cursor() as cursor:
            cursor.execute(
                self._get_many_query.format(
                    table=table, list_sql=get_list_sql(made_keys)
                ),
                made_keys + [self._now()],
            )
            rows = cursor.fetchall()

        data = {}

        for made_key, value, value_type in rows:
            key = made_key_to_key[made_key]
            data[key] = self.decode(value, value_type)

        return data

    _get_many_query = collapse_spaces(
        """
        SELECT cache_key, value, value_type
        FROM {table}
        WHERE cache_key IN {list_sql} AND
              expires >= %s
    """
    )

    def set(
        self,
        key: str,
        value: Any,
        timeout: Any = DEFAULT_TIMEOUT,
        version: Optional[int] = None,
    ) -> None:
        key = self.make_key(key, version=version)
        self.validate_key(key)
        self._base_set("set", key, value, timeout)

    def add(
        self,
        key: str,
        value: Any,
        timeout: Any = DEFAULT_TIMEOUT,
        version: Optional[int] = None,
    ) -> bool:
        key = self.make_key(key, version=version)
        self.validate_key(key)
        return self._base_set("add", key, value, timeout)

    def _base_set(
        self, mode: str, key: str, value: Any, timeout: Any = DEFAULT_TIMEOUT
    ) -> bool:
        if mode not in ("set", "add"):
            raise ValueError("'mode' should be 'set' or 'add'")

        exp = self.get_backend_timeout(timeout)
        db = router.db_for_write(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        self._maybe_cull()
        with connections[db].cursor() as cursor:

            value, value_type = self.encode(value)

            params: Tuple[Any, ...]
            if mode == "set":
                query = self._set_query
                params = (key, value, value_type, exp)
            else:  # mode = 'add'
                query = self._add_query
                params = (key, value, value_type, exp, self._now())

            cursor.execute(query.format(table=table), params)

            if mode == "set":
                return True
            else:  # mode = 'add'
                # Use a special code in the add query for "did insert"
                insert_id = cursor.lastrowid
                return insert_id != 444

    _set_many_query = collapse_spaces(
        """
        INSERT INTO {table} (cache_key, value, value_type, expires)
        VALUES {{VALUES_CLAUSE}}
        ON DUPLICATE KEY UPDATE
            value=VALUES(value),
            value_type=VALUES(value_type),
            expires=VALUES(expires)
    """
    )

    _set_query = _set_many_query.replace("{{VALUES_CLAUSE}}", "(%s, %s, %s, %s)")

    # Uses the IFNULL / LEAST / LAST_INSERT_ID trick to communicate the special
    # value of 444 back to the client (LAST_INSERT_ID is otherwise 0, since
    # there is no AUTO_INCREMENT column)
    _add_query = collapse_spaces(
        """
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
    """
    )

    def set_many(
        self,
        data: Dict[str, Any],
        timeout: Any = DEFAULT_TIMEOUT,
        version: Optional[int] = None,
    ) -> List[str]:
        exp = self.get_backend_timeout(timeout)
        db = router.db_for_write(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        self._maybe_cull()

        params: List[Any] = []
        for key, value in data.items():
            made_key = self.make_key(key, version=version)
            self.validate_key(made_key)
            value, value_type = self.encode(value)
            params.extend((made_key, value, value_type, exp))

        query = self._set_many_query.replace(
            "{{VALUES_CLAUSE}}", ",".join("(%s, %s, %s, %s)" for key in data)
        ).format(table=table)

        with connections[db].cursor() as cursor:
            cursor.execute(query, params)
        return []

    def delete(self, key: str, version: Optional[int] = None) -> None:
        key = self.make_key(key, version=version)
        self.validate_key(key)

        db = router.db_for_write(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        with connections[db].cursor() as cursor:
            cursor.execute(self._delete_query.format(table=table), (key,))

    _delete_query = collapse_spaces(
        """
        DELETE FROM {table}
        WHERE cache_key = %s
    """
    )

    def delete_many(self, keys: Iterable[str], version: Optional[int] = None) -> None:
        made_keys = [self.make_key(key, version=version) for key in keys]
        for key in made_keys:
            self.validate_key(key)

        db = router.db_for_write(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        with connections[db].cursor() as cursor:
            cursor.execute(
                self._delete_many_query.format(
                    table=table, list_sql=get_list_sql(made_keys)
                ),
                made_keys,
            )

    _delete_many_query = collapse_spaces(
        """
        DELETE FROM {table}
        WHERE cache_key IN {list_sql}
    """
    )

    def has_key(self, key: str, version: Optional[int] = None) -> bool:
        key = self.make_key(key, version=version)
        self.validate_key(key)

        db = router.db_for_read(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        with connections[db].cursor() as cursor:
            cursor.execute(self._has_key_query.format(table=table), (key, self._now()))
            return cursor.fetchone() is not None

    _has_key_query = collapse_spaces(
        """
        SELECT 1 FROM {table}
        WHERE cache_key = %s and expires > %s
    """
    )

    def incr(self, key: str, delta: int = 1, version: Optional[int] = None) -> int:
        return self._base_delta(key, delta, version, "+")

    def decr(self, key: str, delta: int = 1, version: Optional[int] = None) -> int:
        return self._base_delta(key, delta, version, "-")

    def _base_delta(
        self,
        key: str,
        delta: int,
        version: Optional[int],
        operation: _BaseDeltaType,
    ) -> int:
        key = self.make_key(key, version=version)
        self.validate_key(key)

        db = router.db_for_write(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        with connections[db].cursor() as cursor:
            updated = cursor.execute(
                self._delta_query.format(table=table, operation=operation), (delta, key)
            )

            if not updated:
                raise ValueError("Key '%s' not found, or not an integer" % key)

            # New value stored in insert_id
            return cursor.lastrowid

    # Looks a bit tangled to turn the blob back into an int for updating, but
    # it works. Stores the new value for insert_id() with LAST_INSERT_ID
    _delta_query = collapse_spaces(
        """
        UPDATE {table}
        SET value = LAST_INSERT_ID(
            CAST(value AS SIGNED INTEGER)
            {operation}
            %s
        )
        WHERE cache_key = %s AND
              value_type = 'i'
    """
    )

    def clear(self) -> None:
        db = router.db_for_write(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)
        with connections[db].cursor() as cursor:
            cursor.execute(f"DELETE FROM {table}")

    def touch(
        self, key: str, timeout: Any = DEFAULT_TIMEOUT, version: Optional[int] = None
    ) -> None:
        key = self.make_key(key, version=version)
        self.validate_key(key)
        exp = self.get_backend_timeout(timeout)
        db = router.db_for_write(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)
        with connections[db].cursor() as cursor:
            cursor.execute(
                self._touch_query.format(table=table), [exp, key, self._now()]
            )

    _touch_query = collapse_spaces(
        """
        UPDATE {table}
        SET expires = %s
        WHERE cache_key = %s AND
              expires >= %s
    """
    )

    def validate_key(self, key: str) -> None:
        """
        Django normally warns about maximum key length, but we error on it.
        """
        if len(key) > 250:
            raise ValueError(
                f"Cache key is longer than the maxmimum 250 characters: {key}"
            )
        return super().validate_key(key)

    def encode(self, obj: Any) -> Tuple[Union[int, bytes], _EncodedKeyType]:
        """
        Take a Python object and return it as a tuple (value, value_type), a
        blob and a one-char code for what type it is
        """
        if self._is_valid_mysql_bigint(obj):
            return obj, "i"

        value = pickle.dumps(obj, pickle.HIGHEST_PROTOCOL)
        value_type: _EncodedKeyType = "p"
        if self._compress_min_length and len(value) >= self._compress_min_length:
            value = zlib.compress(value, self._compress_level)
            value_type = "z"
        return value, value_type

    def _is_valid_mysql_bigint(self, value: Union[int, bytes]) -> bool:
        return (
            # Can't support int subclasses since they should are expected to
            # decode back to the same object
            type(value) is int
            # Can't go beyond these ranges
            and BIGINT_SIGNED_MIN <= value <= BIGINT_SIGNED_MAX
        )

    def decode(self, value: bytes, value_type: _EncodedKeyType) -> Any:
        """
        Take a value blob and its value_type one-char code and convert it back
        to a python object
        """
        if value_type == "i":
            return int(value)

        raw_value: bytes
        if value_type == "z":
            raw_value = zlib.decompress(value)
            value_type = "p"
        else:
            raw_value = force_bytes(value)

        if value_type == "p":
            return pickle.loads(raw_value)

        raise ValueError(
            f"Unknown value_type '{value_type}' read from the cache table."
        )

    def _maybe_cull(self) -> None:
        # Roll the dice, if it says yes then cull
        if self._cull_probability and random() <= self._cull_probability:
            self.cull()

    def get_backend_timeout(self, timeout: Any = DEFAULT_TIMEOUT) -> int:
        if timeout is None:
            return self.FOREVER_TIMEOUT
        timeout = super().get_backend_timeout(timeout)
        return int(timeout * 1000)

    # Our API extensions

    def keys_with_prefix(self, prefix: str, version: Optional[int] = None) -> Set[str]:
        if self.reverse_key_func is None:
            raise ValueError(
                "To use the _with_prefix commands with a custom KEY_FUNCTION, "
                "you need to specify a custom REVERSE_KEY_FUNCTION too."
            )

        if version is None:
            version = self.version

        db = router.db_for_read(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        prefix = self.make_key(prefix + "%", version=version)

        with connections[db].cursor() as cursor:
            cursor.execute(
                """SELECT cache_key FROM {table}
                   WHERE cache_key LIKE %s AND
                         expires >= %s""".format(
                    table=table
                ),
                (prefix, self._now()),
            )
            rows = cursor.fetchall()
            full_keys = {row[0] for row in rows}

            keys = {}
            for full_key in full_keys:
                key, key_prefix, key_version = self.reverse_key_func(full_key)

                if key_version == version:
                    keys[key] = key_version
            return set(keys.keys())

    def get_with_prefix(
        self, prefix: str, version: Optional[int] = None
    ) -> Dict[str, Any]:
        if self.reverse_key_func is None:
            raise ValueError(
                "To use the _with_prefix commands with a custom KEY_FUNCTION, "
                "you need to specify a custom REVERSE_KEY_FUNCTION too."
            )

        if version is None:
            version = self.version

        db = router.db_for_read(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        prefix = self.make_key(prefix + "%", version=version)

        with connections[db].cursor() as cursor:
            cursor.execute(
                """SELECT cache_key, value, value_type
                   FROM {table}
                   WHERE cache_key LIKE %s AND
                         expires >= %s""".format(
                    table=table
                ),
                (prefix, self._now()),
            )
            rows = cursor.fetchall()

            data = {}
            for made_key, value, value_type in rows:
                key, key_prefix, key_version = self.reverse_key_func(made_key)
                data[key] = self.decode(value, value_type)

            return data

    def delete_with_prefix(self, prefix: str, version: Optional[int] = None) -> int:
        if version is None:
            version = self.version

        db = router.db_for_write(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        prefix = self.make_key(prefix + "%", version=version)

        with connections[db].cursor() as cursor:
            return cursor.execute(
                """DELETE FROM {table}
                   WHERE cache_key LIKE %s""".format(
                    table=table
                ),
                (prefix,),
            )

    def cull(self) -> int:
        db = router.db_for_write(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        with connections[db].cursor() as cursor:
            # First, try just deleting expired keys
            num_deleted = cursor.execute(
                f"DELETE FROM {table} WHERE expires < %s",
                (self._now(),),
            )

            # -1 means "Don't limit size"
            if self._max_entries == -1:
                return 0

            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            num = cursor.fetchone()[0]

            if num < self._max_entries:
                return num_deleted

            # Now do a key-based cull
            if self._cull_frequency == 0:
                num_deleted += cursor.execute(f"DELETE FROM {table}")
            else:
                cull_num = num // self._cull_frequency
                cursor.execute(
                    """SELECT cache_key FROM {table}
                       ORDER BY cache_key
                       LIMIT 1 OFFSET %s""".format(
                        table=table
                    ),
                    (cull_num,),
                )
                max_key = cursor.fetchone()[0]
                num_deleted += cursor.execute(
                    """DELETE FROM {table}
                       WHERE cache_key < %s""".format(
                        table=table
                    ),
                    (max_key,),
                )
            return num_deleted
