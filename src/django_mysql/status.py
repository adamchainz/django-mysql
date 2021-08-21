import time
from typing import Dict, Iterable, Optional, Union

from django.db import connections
from django.db.backends.utils import CursorWrapper
from django.db.utils import DEFAULT_DB_ALIAS
from django.utils.functional import SimpleLazyObject

from django_mysql.exceptions import TimeoutError


class BaseStatus:
    """
    Base class for the status classes
    """

    query = ""

    def __init__(self, using: Optional[str] = None) -> None:
        if using is None:
            self.db = DEFAULT_DB_ALIAS
        else:
            self.db = using

    def get_cursor(self) -> CursorWrapper:
        return connections[self.db].cursor()

    def get(self, name: str) -> Union[int, float, bool, str]:
        if "%" in name:
            raise ValueError(
                "get() is for fetching single variables, " "no % wildcards"
            )
        with self.get_cursor() as cursor:
            num_rows = cursor.execute(self.query + " LIKE %s", (name,))
            if num_rows == 0:
                raise KeyError(f"No such status variable '{name}'")
            return self._cast(cursor.fetchone()[1])

    def get_many(self, names: Iterable[str]) -> Dict[str, Union[int, float, bool, str]]:
        if not names:
            return {}

        if any(("%" in name) for name in names):
            raise ValueError(
                "get_many() is for fetching named " "variables, no % wildcards"
            )

        with self.get_cursor() as cursor:
            query = " ".join(
                [
                    self.query,
                    "WHERE Variable_name IN (",
                    ", ".join("%s" for n in names),
                    ")",
                ]
            )

            cursor.execute(query, names)

            return {name: self._cast(value) for name, value in cursor.fetchall()}

    def as_dict(
        self, prefix: Optional[str] = None
    ) -> Dict[str, Union[int, float, bool, str]]:
        with self.get_cursor() as cursor:
            if prefix is None:
                cursor.execute(self.query)
            else:
                cursor.execute(self.query + " LIKE %s", (prefix + "%",))
            rows = cursor.fetchall()
            return {name: self._cast(value) for name, value in rows}

    def _cast(self, value: str) -> Union[int, float, bool, str]:
        # Many status variables are integers or floats but SHOW GLOBAL STATUS
        # returns them as strings
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                pass

        if value == "ON":
            return True
        elif value == "OFF":
            return False

        return value


class GlobalStatus(BaseStatus):
    query = "SHOW GLOBAL STATUS"

    def wait_until_load_low(
        self,
        thresholds: Optional[Dict[str, Union[int, float]]] = None,
        timeout: float = 60.0,
        sleep: float = 0.1,
    ) -> None:
        if thresholds is None:
            thresholds = {"Threads_running": 10}

        start = time.time()
        names = thresholds.keys()

        while True:
            current = self.get_many(names)
            higher = []
            for name, value in current.items():
                assert isinstance(value, (int, float))
                if value > thresholds[name]:
                    higher.append(name)

            if not higher:
                return

            if timeout and time.time() > start + timeout:
                raise TimeoutError(
                    "Span too long waiting for load to drop: "
                    + ",".join(f"{name} > {thresholds[name]}" for name in higher)
                )
            time.sleep(sleep)


class SessionStatus(BaseStatus):
    query = "SHOW SESSION STATUS"


global_status = SimpleLazyObject(GlobalStatus)
session_status = SimpleLazyObject(SessionStatus)
