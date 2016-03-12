.. _status:

======
Status
======

MySQL gives you metadata on the server status through its ``SHOW GLOBAL
STATUS`` and ``SHOW SESSION STATUS`` commands. These classes make it easy to
get this data, as well as providing utility methods to react to it.

The following can all be imported from ``django_mysql.status``.

.. currentmodule:: django_mysql.status


.. class:: GlobalStatus(name, using=None)

    Provides easy access to the output of ``SHOW GLOBAL STATUS``. These
    statistics are useful for monitoring purposes, or ensuring queries your
    code creates aren't saturating the server.

    Basic usage:

    .. code-block:: python

        from django_mysql.status import global_status

        # Wait until a quiet moment
        while global_status.get('Threads_running') >= 5:
            time.sleep(1)

        # Log all status variables
        logger.log("DB status", extra=global_status.as_dict())

    Note that ``global_status`` is a pre-existing instance for the default
    database connection from ``DATABASES``. If you're using more than database
    connection, you should instantiate the class:

    .. code-block:: pycon

        >>> from django_mysql.status import GlobalStatus
        >>> GlobalStatus(using='replica1').get('Threads_running')
        47

    To see the names of all the available variables, refer to the documentation:
    `MySQL <http://dev.mysql.com/doc/refman/5.6/en/show-status.html>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/show-status/>`_. They vary
    based upon server version, plugins installed, etc.

    .. attribute:: using=None

        The connection alias from ``DATABASES`` to use. Defaults to Django's
        ``DEFAULT_DB_ALIAS`` to use your main database connection.

    .. method:: get(name)

        Returns the current value of the named status variable. The name may
        not include SQL wildcards (``%``). If it does not exist, ``KeyError``
        will be raised.

        The result set for ``SHOW STATUS`` returns values in strings, so
        numbers and booleans will be cast to their respective Python types -
        ``int``, ``float``, or ``bool``. Strings are be left as-is.

    .. method:: get_many(names)

        Returns a dictionary of names to current values, fetching them in a
        single query. The names may not include wildcards (``%``).

        Uses the same type-casting strategy as ``get()``.

    .. method:: as_dict(prefix=None)

        Returns a dictionary of names to current values. If ``prefix`` is
        given, only those variables starting with the prefix will be returned.
        ``prefix`` should not end with a wildcard (``%``) since that will be
        automatically appended.

        Uses the same type-casting strategy as ``get()``.

    .. method:: wait_until_load_low(thresholds={'Threads_running': 5}, \
                                    timeout=60.0, sleep=0.1)

        A helper method similar to the logic in ``pt-online-schema-change`` for
        waiting with `--max-load <http://www.percona.com/doc/percona-toolkit/2.1/pt-online-schema-change.html#cmdoption-pt-online-schema-change--max-load>`_.

        Polls global status every ``sleep`` seconds until every variable named
        in ``thresholds`` is at or below its specified threshold, or raises a
        :class:`django_mysql.exceptions.TimeoutError` if this does not occur
        within ``timeout`` seconds. Set ``timeout`` to 0 to never time out.

        ``thresholds`` defaults to ``{'Threads_running': 5}``, which is the
        default variable used in ``pt-online-schema-change``, but with a lower
        threshold of 5 that is more suitable for small servers. You will very
        probably need to tweak it to your server.

        You can use this method during large background operations which you
        don't want to affect other connections (i.e. your website). By
        processing in small chunks and waiting for low load in between, you
        sharply reduce your risk of outage.


.. class:: SessionStatus(name, connection_name=None)

    This class is the same as GlobalStatus apart from it runs ``SHOW SESSION
    STATUS``, so *some* variables are restricted to the current connection
    only, rather than the whole server. For which, you should refer to the
    documentation:
    `MySQL <http://dev.mysql.com/doc/refman/5.6/en/show-status.html>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/show-status/>`_.

    Also it doesn't have the ``wait_until_load_low`` method, which only makes
    sense in a global setting.

    Example usage:

    .. code-block:: python

        from django_mysql.status import session_status

        read_operations = session_status.get("Handler_read")

    And for a different connection:

    .. code-block:: python

        from django_mysql.status import SessionStatus

        replica1_reads = SessionStatus(using='replica1').get("Handler_read")
