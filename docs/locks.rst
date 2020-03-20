.. _locks:

=====
Locks
=====

.. currentmodule:: django_mysql.locks

The following can be imported from ``django_mysql.locks``.

.. class:: Lock(name, acquire_timeout=10.0, using=None)

    MySQL can act as a locking server for arbitrary named locks (created on the
    fly) via its ``GET_LOCK`` function - sometimes called 'User Locks' since
    they are user-specific, and don't lock tables or rows. They can be useful
    for your code to limit its access to some shared resource.

    This class implements a user lock and acts as either a context manager
    (recommended), or a plain object with ``acquire`` and ``release`` methods
    similar to ``threading.Lock``. These call the MySQL functions ``GET_LOCK``,
    ``RELEASE_LOCK``, and ``IS_USED_LOCK`` to manage it.

    The lock is only re-entrant (acquirable multiple times) on MariaDB 10.0+.

    MySQL before 5.7, and MariaDB before 10.0, only allowed one lock per
    connection. On those versions and later, you can hold multiple locks.

    Basic usage:

    .. code-block:: python

        from django_mysql.exceptions import TimeoutError
        from django_mysql.locks import Lock

        try:
            with Lock('my_unique_name', acquire_timeout=2.0):
                mutually_exclusive_process()
        except TimeoutError:
            print "Could not get the lock"

    For more information on user locks refer to the ``GET_LOCK`` documentation
    on `MySQL
    <https://dev.mysql.com/doc/refman/5.6/en/miscellaneous-functions.html#function_get-lock>`__
    or `MariaDB <https://mariadb.com/kb/en/mariadb/get_lock/>`__.

    .. warning::

        As the documentation warns, user locks are unsafe to use if you have
        replication running and your replication format (``binlog_format``) is
        set to ``STATEMENT``. Most environments have ``binlog_format`` set to
        ``MIXED`` because it can be more performant, but do check.

    .. attribute:: name

        This is a required argument.

        Specifies the name of the lock. Since user locks share a global
        namespace on the MySQL server, it will automatically be prefixed with
        the name of the database you use in your connection from DATABASES and
        a full stop, in case multiple apps are using different databases on the
        same server.

        MySQL 5.7+ enforces a maximum length on the total name (including the
        DB prefix that Django-MySQL adds) of 64 characters. MariaDB doesn't
        enforce any limit. The practical limit on MySQL <5.6 or MariaDB is
        maybe 1 million characters or more, so most sane uses should be fine.

    .. attribute:: acquire_timeout=10.0

        The time in seconds to wait to acquire the lock, as will be passed to
        ``GET_LOCK()``. Defaults to 10 seconds.

    .. attribute:: using=None

        The connection alias from ``DATABASES`` to use. Defaults to Django's
        ``DEFAULT_DB_ALIAS`` to use your main database connection.

    .. method:: is_held()

        Returns True iff a query to ``IS_USED_LOCK()`` reveals that this lock
        is currently held.

    .. method:: holding_connection_id()

        Returns the MySQL ``CONNECTION_ID()`` of the holder of the lock, or
        ``None`` if it is not currently held.

    .. method:: acquire()

        For using the lock as a plain object rather than a context manager,
        similar to ``threading.Lock.acquire``. Note you should normally use
        ``try`` / ``finally`` to ensure unlocking occurs.

        Example usage:

        .. code-block:: python

            from django_mysql.locks import Lock

            lock = Lock('my_unique_name')
            lock.acquire()
            try:
                mutually_exclusive_process()
            finally:
                lock.release()

    .. method:: release()

        Also for using the lock as a plain object rather than a context
        manager, similar to ``threading.Lock.release``. For example, see above.

    .. classmethod:: held_with_prefix(prefix, using=DEFAULT_DB_ALIAS)

        Queries the held locks that match the given prefix, for the given
        database connection. Returns a dict of lock names to the
        ``CONNECTION_ID()`` that holds the given lock.

        Example usage:

        .. code-block:: pycon

            >>> Lock.held_with_prefix('Author')
            {'Author.1': 451, 'Author.2': 457}

        .. note::
            Works with MariaDB 10.0.7+ only, when the ``metadata_lock_info``
            plugin is loaded. You can install this in a migration using the
            :class:`~django_mysql.operations.InstallSOName` operation, like
            so:

            .. code-block:: python

                from django.db import migrations
                from django_mysql.operations import InstallSOName


                class Migration(migrations.Migration):
                    dependencies = []

                    operations = [
                        # Install https://mariadb.com/kb/en/mariadb/metadata_lock_info/
                        InstallSOName('metadata_lock_info')
                    ]

.. class:: TableLock(write=None, read=none, using=None)

    MySQL allows you to gain a table lock to prevent modifications to the data
    during reads or writes. Most applications don't need to do this since
    transaction isolation should provide enough separation between operations,
    but occasionally this can be useful, especially in data migrations or if
    you are using a non-transactional storage such as MyISAM.

    This class implements table locking and acts as either a context manager
    (recommended), or a plain object with ``acquire()`` and ``release()``
    methods similar to ``threading.Lock``. It uses the transactional pattern
    from the MySQL manual to ensure all the necessary steps are taken to lock
    tables properly. Note that locking has no timeout and blocks until held.

    Basic usage:

    .. code-block:: python

        from django_mysql.locks import TableLock

        with TableLock(read=[MyModel1], write=[MyModel2]):
            fix_bad_instances_of_my_model2_using_my_model1_data()

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/en/lock-tables.html>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/lock-tables-and-unlock-tables/>`_.

    .. attribute:: read

        A list of models or raw table names to lock at the ``READ`` level. Any
        models using multi-table inheritance will also lock their parents.

    .. attribute:: write

        A list of models or raw table names to lock at the ``WRITE`` level. Any
        models using multi-table inheritance will also lock their parents.

    .. attribute:: using=None

        The connection alias from ``DATABASES`` to use. Defaults to Django's
        ``DEFAULT_DB_ALIAS`` to use your main database connection.

    .. method:: acquire()

        For using the lock as a plain object rather than a context manager,
        similar to ``threading.Lock.acquire``. Note you should normally use
        ``try`` / ``finally`` to ensure unlocking occurs.

        Example usage:

        .. code-block:: python

            from django_mysql.locks import TableLock

            table_lock = TableLock(read=[MyModel1], write=[MyModel2])
            table_lock.acquire()
            try:
                fix_bad_instances_of_my_model2_using_my_model1_data()
            finally:
                table_lock.release()

    .. method:: release()

        Also for using the lock as a plain object rather than a context
        manager, similar to ``threading.Lock.release``. For example, see above.

    .. note::

        Transactions are not allowed around table locks, and an error will be
        raised if you try and use one inside of a transaction. A transaction is
        created to hold the locks in order to cooperate with InnoDB. There are
        a number of things you can't do whilst holding a table lock, for
        example accessing tables other than those you have locked - see the
        MySQL/MariaDB documentation for more details.

    .. note::

        Table locking works on InnoDB tables only if the ``innodb_table_locks``
        is set to 1. This is the default, but may have been changed for your
        environment.
