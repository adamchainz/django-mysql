.. _utilities:

=========
Utilities
=========

.. currentmodule:: django_mysql.utils

The following can be imported from ``django_mysql.utils``.


.. function:: pt_fingerprint(query)

    Given a string ``query`` containing a MySQL query, returns a 'fingerprint'
    of the query from the Percona ``pt-fingerprint`` tool
    (`docs <http://www.percona.com/doc/percona-toolkit/2.2/pt-fingerprint.html>`_).
    You must therefore have ``pt-fingerprint`` installed.

    Example usage:

        >>> pt_fingerprint("SELECT a, b FROM myapp_author WHERE id = 55")
        'select a, b from myapp_author where id = ?'
        >>> pt_fingerprint("SELECT SLEEP(123)")
        'select sleep(?)'
        >>> pt_fingerprint("release savepoint `ax123`")
        'release savepoint `a?`'

    This is a complex subprocess wrapper that is suitable for processing many
    queries serially - it opens ``pt-fingerprint`` in a background thread,
    which accepts input line-by-line, and shuts it down after 60 seconds of
    not being used. It is therefore suitable for use one-query-at-a-time, even
    when batch processing hundreds of queries.

    .. note::

        Because this uses Python's ``pty`` library, it only works on Unix.
