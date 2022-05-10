from __future__ import annotations

import time
from collections import defaultdict
from types import TracebackType
from typing import Any, Generator

from django.db import DEFAULT_DB_ALIAS, connections
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.models import Model


class WeightedAverageRate:
    """
    Adapted from percona-toolkit - provides a weighted average counter to keep
    at a certain rate of activity (row iterations etc.).
    """

    def __init__(self, target_t: float, weight: float = 0.75) -> None:
        """
        target_t - Target time for t in update()
        weight - Weight of previous n/t values
        """
        self.target_t = target_t
        self.avg_n = 0.0
        self.avg_t = 0.0
        self.weight = weight

    def update(self, n: int, t: float) -> int:
        """
        Update weighted average rate.  Param n is generic; it's how many of
        whatever the caller is doing (rows, checksums, etc.).  Param s is how
        long this n took, in seconds (hi-res or not).

        Parameters:
            n - Number of operations (rows, etc.)
            t - Amount of time in seconds that n took

        Returns:
            n adjusted to meet target_t based on weighted decaying avg rate
        """
        if self.avg_n and self.avg_t:
            self.avg_n = (self.avg_n * self.weight) + n
            self.avg_t = (self.avg_t * self.weight) + t
        else:
            self.avg_n = n
            self.avg_t = t

        return int(self.avg_rate * self.target_t)

    @property
    def avg_rate(self) -> float:
        try:
            return self.avg_n / self.avg_t
        except ZeroDivisionError:
            # Assume a small amount of time, not 0
            return self.avg_n / 0.001


class StopWatch:
    """
    Context manager for timing a block
    """

    def __enter__(self) -> StopWatch:
        self.start_time = time.time()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: TracebackType | None,
    ) -> None:
        self.end_time = time.time()
        self.total_time = self.end_time - self.start_time


def format_duration(total_seconds: int) -> str:
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    out = []
    if hours > 0:
        out.extend([str(hours), "h"])
    if hours or minutes:
        out.extend([str(minutes), "m"])
    out.extend([str(seconds), "s"])
    return "".join(out)


def settings_to_cmd_args(settings_dict: dict[str, Any]) -> list[str]:
    """
    Copied from django 1.8 MySQL backend DatabaseClient - where the runshell
    commandline creation has been extracted and made callable like so.
    """
    args = ["mysql"]
    db = settings_dict["OPTIONS"].get("db", settings_dict["NAME"])
    user = settings_dict["OPTIONS"].get("user", settings_dict["USER"])
    passwd = settings_dict["OPTIONS"].get("passwd", settings_dict["PASSWORD"])
    host = settings_dict["OPTIONS"].get("host", settings_dict["HOST"])
    port = settings_dict["OPTIONS"].get("port", settings_dict["PORT"])
    cert = settings_dict["OPTIONS"].get("ssl", {}).get("ca")
    defaults_file = settings_dict["OPTIONS"].get("read_default_file")
    # Seems to be no good way to set sql_mode with CLI.

    if defaults_file:
        args += ["--defaults-file=%s" % defaults_file]
    if user:
        args += ["--user=%s" % user]
    if passwd:
        args += ["--password=%s" % passwd]
    if host:  # pragma: no branch
        if "/" in host:
            args += ["--socket=%s" % host]
        else:
            args += ["--host=%s" % host]
    if port:
        args += ["--port=%s" % port]
    if cert:
        args += ["--ssl-ca=%s" % cert]
    if db:
        args += [db]
    return args


def collapse_spaces(string: str) -> str:
    bits = string.replace("\n", " ").split(" ")
    return " ".join(filter(None, bits))


def index_name(model: Model, *field_names: str, using: str = DEFAULT_DB_ALIAS) -> str:
    """
    Returns the name of the index existing on field_names, or raises KeyError
    if no such index exists.
    """
    if not len(field_names):
        raise ValueError("At least one field name required")

    existing_fields = {field.name: field for field in model._meta.fields}
    fields = [existing_fields[name] for name in field_names if name in existing_fields]

    if len(fields) != len(field_names):
        unfound_names = set(field_names) - {field.name for field in fields}
        raise ValueError("Fields do not exist: " + ",".join(unfound_names))
    column_names = tuple(field.column for field in fields)
    list_sql = get_list_sql(column_names)

    with connections[using].cursor() as cursor:
        cursor.execute(
            """SELECT `INDEX_NAME`, `SEQ_IN_INDEX`, `COLUMN_NAME`
               FROM INFORMATION_SCHEMA.STATISTICS
               WHERE TABLE_SCHEMA = DATABASE() AND
                     TABLE_NAME = %s AND
                     COLUMN_NAME IN {list_sql}
               ORDER BY `INDEX_NAME`, `SEQ_IN_INDEX` ASC
            """.format(
                list_sql=list_sql
            ),
            (model._meta.db_table,) + column_names,
        )
        indexes = defaultdict(list)
        for index_name, _, column_name in cursor.fetchall():
            indexes[index_name].append(column_name)

    indexes_by_columns = {tuple(v): k for k, v in indexes.items()}
    try:
        return indexes_by_columns[column_names]
    except KeyError:
        raise KeyError("There is no index on (" + ",".join(field_names) + ")")


def get_list_sql(sequence: list[str] | tuple[str, ...]) -> str:
    return "({})".format(",".join("%s" for x in sequence))


def mysql_connections() -> Generator[BaseDatabaseWrapper, None, None]:
    conn_names = [DEFAULT_DB_ALIAS] + list(set(connections) - {DEFAULT_DB_ALIAS})
    for alias in conn_names:
        connection = connections[alias]
        if connection.vendor == "mysql":
            yield alias, connection
