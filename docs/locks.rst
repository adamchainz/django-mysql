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

    This class implements a user lock as a context manager, which calls the
    underlying MySQL functions ``GET_LOCK``, ``RELEASE_LOCK``, and
    ``IS_USED_LOCK`` to manage it. It is not re-entrant so don't write
    code that gains/releases the same lock more than once.

    Basic usage::

        from django_mysql.exceptions import TimeoutError
        from django_mysql.locks import Lock

        try:
            with Lock('my_unique_name', acquire_timeout=2.0):
                mutually_exclusive_process()
        except TimeoutError:
            print "Could not get the lock"

    For more information on user locks refer to the ``GET_LOCK`` documentation
    on `MySQL
    <http://dev.mysql.com/doc/refman/5.6/en/miscellaneous-functions.html#function_get-lock>`_
    or `MariaDB <https://mariadb.com/kb/en/mariadb/get_lock/>`_.

    .. warning::

        As the documentation warns, user locks are unsafe to use if you have
        replication running and your replication format (``binlog_format``) is
        set to ``STATEMENT``. Most environments have ``binlog_format`` set to
        ``MIXED`` because it can be more performant, but do check.

    .. warning::

        It's not very well documented, but you can only hold one lock per
        database connection at a time. Acquiring a lock releases any other lock
        you were holding.

        Since there is no MySQL function to tell you if you are currently
        holding a lock, this class does not check that you only acquire one
        lock. It has been a `more than 10 year feature request
        <http://bugs.mysql.com/bug.php?id=1118>`_ to hold more than one lock
        per connection, and has been finally announced in MySQL 5.7.5.

    .. attribute:: name

        This is a required argument.

        Specifies the name of the lock. Since user locks share a global
        namespace on the MySQL server, it will automatically be prefixed with
        the name of the database you use in your connection from DATABASES and
        a full stop, in case multiple apps are using different databases on the
        same server.

        Whilst not documented, the length limit is somewhere between 1 and 10
        million characters, so most sane uses should be fine.

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
