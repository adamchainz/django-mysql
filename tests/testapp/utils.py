from __future__ import annotations

import sys
from contextlib import contextmanager
from types import TracebackType
from typing import Any
from typing import Generator

import pytest
from django.db import connection
from django.db import connections
from django.db import DEFAULT_DB_ALIAS
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.mysql.base import DatabaseWrapper as MySQLDatabaseWrapper
from django.db.backends.utils import CursorWrapper
from django.test.utils import CaptureQueriesContext

if sys.version_info >= (3, 10):
    from typing import TypeGuard
else:
    from typing_extensions import TypeGuard


def conn_is_mysql(connection: BaseDatabaseWrapper) -> TypeGuard[MySQLDatabaseWrapper]:
    return connection.vendor == "mysql"


@contextmanager
def skip_if_mysql_8_plus() -> Generator[None, None, None]:
    if not conn_is_mysql(connection) or (
        not connection.mysql_is_mariadb and connection.mysql_version >= (8,)
    ):
        pytest.skip("Requires MySQL<8 or MariaDB")
    yield


def column_type(table_name: str, column_name: str) -> str:
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
               WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND
                     COLUMN_NAME = %s""",
            (table_name, column_name),
        )
        type_: str = cursor.fetchone()[0]
        return type_


class CaptureLastQuery:
    def __init__(self, conn: BaseDatabaseWrapper | None = None) -> None:
        if conn is None:  # pragma: no branch
            conn = connection
        self.conn: BaseDatabaseWrapper = conn

    def __enter__(self) -> CaptureLastQuery:
        self.capturer = CaptureQueriesContext(self.conn)
        self.capturer.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.capturer.__exit__(exc_type, exc_val, exc_tb)

    @property
    def query(self) -> str:
        return self.capturer.captured_queries[-1]["sql"]


class print_all_queries:
    def __init__(self, conn: BaseDatabaseWrapper | None = None) -> None:
        if conn is None:  # pragma: no branch
            conn = connection
        self.conn: BaseDatabaseWrapper = conn

    def __enter__(self) -> print_all_queries:
        self.capturer = CaptureQueriesContext(self.conn)
        self.capturer.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.capturer.__exit__(exc_type, exc_val, exc_tb)
        for q in self.capturer.captured_queries:
            print(q["sql"])


def used_indexes(query: str, using: str = DEFAULT_DB_ALIAS) -> set[str]:
    """
    Given SQL 'query', run EXPLAIN and return the names of the indexes used
    """
    connection = connections[using]
    with connection.cursor() as cursor:
        cursor.execute("EXPLAIN " + query)

        return {row["key"] for row in fetchall_dicts(cursor) if row["key"] is not None}


def fetchall_dicts(cursor: CursorWrapper) -> list[dict[str, Any]]:
    columns = [x[0] for x in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
