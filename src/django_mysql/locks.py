from __future__ import annotations

from collections import OrderedDict
from types import TracebackType

from django.db import connections
from django.db.backends.utils import CursorWrapper
from django.db.models import Model
from django.db.transaction import TransactionManagementError
from django.db.transaction import atomic
from django.db.utils import DEFAULT_DB_ALIAS

from django_mysql.exceptions import TimeoutError


class Lock:
    def __init__(
        self, name: str, acquire_timeout: float = 10.0, using: str | None = None
    ) -> None:
        self.acquire_timeout = acquire_timeout

        if using is None:
            self.db: str = DEFAULT_DB_ALIAS
        else:
            self.db = using

        # For multi-database servers, we prefix the name of the lock wth
        # the database, to protect against concurrent apps with the same locks
        self.name = self.make_name(self.db, name)

    @classmethod
    def make_name(cls, db: str, name: str) -> str:
        return ".".join((connections[db].settings_dict["NAME"], name))

    @classmethod
    def unmake_name(cls, db: str, name: str) -> str:
        # Cut off the 'dbname.' prefix
        db_name = connections[db].settings_dict["NAME"]
        return name[len(db_name) + 1 :]

    def get_cursor(self) -> CursorWrapper:
        return connections[self.db].cursor()

    def __enter__(self) -> Lock:
        return self.acquire()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: TracebackType | None,
    ) -> None:
        self.release()

    def acquire(self) -> Lock:
        with self.get_cursor() as cursor:
            cursor.execute("SELECT GET_LOCK(%s, %s)", (self.name, self.acquire_timeout))
            result = cursor.fetchone()[0]
            if result == 1:
                return self
            else:
                raise TimeoutError(
                    f"Waited >{self.acquire_timeout} seconds to gain lock"
                )

    def release(self) -> None:
        with self.get_cursor() as cursor:
            cursor.execute("SELECT RELEASE_LOCK(%s)", (self.name,))
            result = cursor.fetchone()[0]

            if result is None or result == 0:
                raise ValueError("Tried to release an unheld lock.")

    def is_held(self) -> bool:
        return self.holding_connection_id() is not None

    def holding_connection_id(self) -> int | None:
        with self.get_cursor() as cursor:
            cursor.execute("SELECT IS_USED_LOCK(%s)", (self.name,))
            return cursor.fetchone()[0]

    @classmethod
    def held_with_prefix(
        cls, prefix: str, using: str = DEFAULT_DB_ALIAS
    ) -> dict[str, int]:
        # Use the METADATA_LOCK_INFO table from the MariaDB plugin to show
        # which locks of a given prefix are held
        prefix = cls.make_name(using, prefix)

        with connections[using].cursor() as cursor:
            cursor.execute(
                """SELECT TABLE_SCHEMA, THREAD_ID
                   FROM INFORMATION_SCHEMA.METADATA_LOCK_INFO
                   WHERE TABLE_SCHEMA LIKE %s AND
                         LOCK_TYPE = 'User Lock'""",
                (prefix + "%",),
            )
            return {cls.unmake_name(using, row[0]): row[1] for row in cursor.fetchall()}


class TableLock:
    def __init__(
        self,
        read: list[str | type[Model]] | None = None,
        write: list[str | type[Model]] | None = None,
        using: str | None = None,
    ) -> None:
        self.read: list[str] = self._process_names(read)
        self.write: list[str] = self._process_names(write)
        self.db = DEFAULT_DB_ALIAS if using is None else using

    def _process_names(self, names: list[str | type[Model]] | None) -> list[str]:
        """
        Convert a list of models/table names into a list of table names. Deals
        with cases of model inheritance, etc.
        """
        if names is None:
            return []

        table_names = OrderedDict()  # Preserve order and ignore duplicates
        while len(names):
            name = names.pop(0)
            if isinstance(name, type):
                if name._meta.abstract:
                    raise ValueError(f"Can't lock abstract model {name.__name__}")

                table_names[name._meta.db_table] = True
                # Include all parent models - the keys are the model classes
                if name._meta.parents:
                    names.extend(name._meta.parents.keys())
            else:
                table_names[name] = True
        return list(table_names.keys())

    def __enter__(self) -> None:
        self.acquire()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: TracebackType | None,
    ) -> None:
        self.release(exc_type, exc_value, exc_traceback)

    def acquire(self) -> None:
        connection = connections[self.db]
        qn = connection.ops.quote_name
        with connection.cursor() as cursor:
            if not connection.get_autocommit():
                raise TransactionManagementError(
                    "InnoDB requires that we not be in a transaction when "
                    "gaining a table lock."
                )

            # Begin transaction - does 'SET autocommit = 0'
            self._atomic = atomic(using=self.db)
            self._atomic.__enter__()

            locks = [f"{qn(name)} READ" for name in self.read]
            for name in self.write:
                locks.append(f"{qn(name)} WRITE")
            cursor.execute("LOCK TABLES {}".format(", ".join(locks)))

    def release(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        exc_traceback: TracebackType | None = None,
    ) -> None:
        connection = connections[self.db]
        with connection.cursor() as cursor:
            self._atomic.__exit__(exc_type, exc_value, exc_traceback)
            self._atomic = None
            cursor.execute("UNLOCK TABLES")
