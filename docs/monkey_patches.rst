.. _monkey_patches:

==============
Monkey Patches
==============

Extra properties monkey-patched on to Django objects. These are automatically
added when ``django_mysql`` is in your ``INSTALLED_APPS``.

---------------------
connection.is_mariadb
---------------------

A boolean property that tells you if the MySQL database connection is to a
MariaDB server. Used internally for activating tests for MariaDB-specific
features. It is patched onto Django's MySQL ``DatabaseWrapper`` class, so you
can do::

    >>> from django.db import connection
    >>> connection.is_mariadb
    True

Or for a secondary connection::

    >>> from django.db import connections
    >>> connections['other'].is_mariadb
    False
