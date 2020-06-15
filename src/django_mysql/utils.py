import os
import subprocess
import time
from collections import defaultdict
from queue import Empty, Queue
from threading import Lock, Thread
from weakref import WeakKeyDictionary

import django
from django.db import DEFAULT_DB_ALIAS
from django.db import connection as default_connection
from django.db import connections


class WeightedAverageRate:
    """
    Adapted from percona-toolkit - provides a weighted average counter to keep
    at a certain rate of activity (row iterations etc.).
    """

    def __init__(self, target_t, weight=0.75):
        """
        target_t - Target time for t in update()
        weight - Weight of previous n/t values
        """
        self.target_t = target_t
        self.avg_n = 0.0
        self.avg_t = 0.0
        self.weight = weight

    def update(self, n, t):
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

        new_n = int(self.avg_rate * self.target_t)
        return new_n

    @property
    def avg_rate(self):
        try:
            return self.avg_n / self.avg_t
        except ZeroDivisionError:
            # Assume a small amount of time, not 0
            return self.avg_n / 0.001


class StopWatch:
    """
    Context manager for timing a block
    """

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args, **kwargs):
        self.end_time = time.time()
        self.total_time = self.end_time - self.start_time


def format_duration(total_seconds):
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


if django.VERSION >= (3, 0):

    def connection_is_mariadb(connection):
        return connection.vendor == "mysql" and connection.mysql_is_mariadb


else:

    _is_mariadb_cache = WeakKeyDictionary()

    def connection_is_mariadb(connection):
        if connection.vendor != "mysql":
            return False

        if connection is default_connection:
            connection = connections[DEFAULT_DB_ALIAS]

        try:
            return _is_mariadb_cache[connection]
        except KeyError:
            with connection.temporary_connection():
                server_info = connection.connection.get_server_info()
            is_mariadb = "MariaDB" in server_info
            _is_mariadb_cache[connection] = is_mariadb
            return is_mariadb


def settings_to_cmd_args(settings_dict):
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
    if host:
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


programs_memo = {}


def have_program(program_name):
    global programs_memo
    if program_name not in programs_memo:
        status = subprocess.call(["which", program_name], stdout=subprocess.PIPE)
        programs_memo[program_name] = status == 0

    return programs_memo[program_name]


def pt_fingerprint(query):
    """
    Takes a query (in a string) and returns its 'fingerprint'
    """
    if not have_program("pt-fingerprint"):  # pragma: no cover
        raise OSError("pt-fingerprint doesn't appear to be installed")

    thread = PTFingerprintThread.get_thread()
    thread.in_queue.put(query)
    return thread.out_queue.get()


class PTFingerprintThread(Thread):
    """
    Class for a singleton background thread to pass queries to pt-fingerprint
    and get their fingerprints back. This is done because the process launch
    time is relatively expensive and it's useful to be able to fingerprinting
    queries quickly.

    The get_thread() class method returns the singleton thread - either
    instantiating it or returning the existing one.

    The thread launches pt-fingerprint with subprocess and then takes queries
    from an input queue, passes them the subprocess and returns the fingerprint
    to an output queue. If it receives no queries in PROCESS_LIFETIME seconds,
    it closes the subprocess and itself - so you don't have processes hanging
    around.
    """

    the_thread = None
    life_lock = Lock()

    PROCESS_LIFETIME = 60.0  # seconds

    @classmethod
    def get_thread(cls):
        with cls.life_lock:
            if cls.the_thread is None:
                in_queue = Queue()
                out_queue = Queue()
                thread = cls(in_queue, out_queue)
                thread.daemon = True
                thread.in_queue = in_queue
                thread.out_queue = out_queue
                thread.start()
                cls.the_thread = thread

        return cls.the_thread

    def __init__(self, in_queue, out_queue, **kwargs):
        self.in_queue = in_queue
        self.out_queue = out_queue
        super().__init__(**kwargs)

    def run(self):
        # pty is unix/linux only
        import pty  # noqa

        global fingerprint_thread
        master, slave = pty.openpty()
        proc = subprocess.Popen(
            ["pt-fingerprint"], stdin=subprocess.PIPE, stdout=slave, close_fds=True
        )
        stdin = proc.stdin
        stdout = os.fdopen(master)

        while True:
            try:
                query = self.in_queue.get(timeout=self.PROCESS_LIFETIME)
            except Empty:
                self.life_lock.acquire()
                # We timed out, but there was something put into the queue
                # since
                if (
                    self.__class__.the_thread is self and self.in_queue.qsize()
                ):  # pragma: no cover
                    self.life_lock.release()
                    break
                # Die
                break

            stdin.write(query.encode("utf-8"))
            if not query.endswith(";"):
                stdin.write(b";")
            stdin.write(b"\n")
            stdin.flush()
            fingerprint = stdout.readline()
            self.out_queue.put(fingerprint.strip())

        stdin.close()
        self.__class__.the_thread = None
        self.life_lock.release()


def collapse_spaces(string):
    bits = string.replace("\n", " ").split(" ")
    return " ".join(filter(None, bits))


def index_name(model, *field_names, **kwargs):
    """
    Returns the name of the index existing on field_names, or raises KeyError
    if no such index exists.
    """
    if not len(field_names):
        raise ValueError("At least one field name required")
    using = kwargs.pop("using", DEFAULT_DB_ALIAS)
    if len(kwargs):
        raise ValueError("The only supported keyword argument is 'using'")

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


def get_list_sql(sequence):
    return "({})".format(",".join("%s" for x in sequence))


def mysql_connections():
    conn_names = [DEFAULT_DB_ALIAS] + list(set(connections) - {DEFAULT_DB_ALIAS})
    for alias in conn_names:
        connection = connections[alias]
        if connection.vendor != "mysql":
            continue

        yield alias, connection
