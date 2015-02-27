======
Status
======

These classes can be imported from the ``django_mysql.status`` module.

.. currentmodule:: django_mysql.status

GlobalStatus
------------

.. class:: GlobalStatus(name, connection_name=None)

    Provides easy  access to the output of ``SHOW GLOBAL STATUS``. These
    statistics are useful for monitoring purposes or ensuring operations your
    app creates aren't saturating the database server and bringing your site
    down.

    Basic usage::

        from django_mysql.status import GlobalStatus

        # Wait until a quiet moment
        while GlobalStatus().get('Threads_running') >= 5:
            time.sleep(1)

        # Log all status variables
        logger.log("DB status", extra=GlobalStatus().as_dict())

    To see what variables you can get, refer to the documentation on
    `MySQL <http://dev.mysql.com/doc/refman/5.6/en/show-status.html>`_ or
    `MariaDB <https://mariadb.com/kb/en/mariadb/show-status/>`_.

    .. attribute:: connection_name

        The name of the connection to use from ``DATABASES`` in your Django
        settings. Defaults to Django's ``DEFAULT_DB_ALIAS`` to use your main
        database connection.

    .. method:: get(name)

        Returns the current value of the named status variable. The name may
        not include wildcards (``%``). If it does not exist, ``KeyError`` will
        be raised.

        The result set for ``SHOW STATUS`` returns values in strings, so
        numbers and booleans will be cast to their respective Python types -
        ``int``, ``float``, or ``bool``. Strings are be left as-is.

    .. method:: as_dict(prefix=None)

        Returns a dictionary of names to current values. If ``prefix`` is
        given, only those variables starting with the prefix will be returned.
        ``prefix`` should not end with a wildcard (``%``) since that will be
        automatically appended.

        Uses the same type-casting strategy as ``get()``.

    .. method:: wait_until_load_low(var_name='Threads_running', var_max=5, \
                                    timeout=60.0, sleep=0.1)

        A helper method similar to ``pt-online-schema-change``'s logic for
        waiting with `--max-load <http://www.percona.com/doc/percona-toolkit/2.1/pt-online-schema-change.html#cmdoption-pt-online-schema-change--max-load>`_.

        Continually polls global status every ``sleep`` seconds until
        ``var_name`` is at or below ``var_max``, or raise a
        :class:`django_mysql.exceptions.TimeoutError` if
        it takes more than ``timeout`` seconds. Set ``timeout`` to 0 to never
        time out. Using ``Threads_running`` as the default variable is taken from
        ``pt-online-schema-change``, but with a lower default threshold of 5
        that is more suitable for smaller servers.

        You can use this method during large background operations which you
        don't want to affect other connections, such as your website. By
        processing in small chunks and waiting for low load in between, you
        sharply reduce your risk of outage.


SessionStatus
-------------

.. class:: SessionStatus(name, connection_name=None)

    This class is the same as GlobalStatus apart from it runs
    ``SHOW SESSION STATUS``, so *some* variables are restricted to the current
    connection only, rather than the whole server. For which, you should refer
    to the documentation on
    `MySQL <http://dev.mysql.com/doc/refman/5.6/en/show-status.html>`_ or
    `MariaDB <https://mariadb.com/kb/en/mariadb/show-status/>`_.

    Also it doesn't have the ``wait_until_load_low`` method, which only makes
    sense in a global setting.
