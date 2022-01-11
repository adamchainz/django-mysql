.. _utilities:

=========
Utilities
=========

.. currentmodule:: django_mysql.utils

The following can be imported from ``django_mysql.utils``.


.. function:: connection_is_mariadb(connection)

    Given a Django database connection (from ``django.db.connections``) return
    ``True`` if it is a connection to a MariaDB database else ``False``. The
    result is cached to avoid unnecessary connections.
