.. _cache:

=====
Cache
=====

Extensions for ``django.core.cache``.

.. currentmodule:: django_mysql.cache


MySQLCache
==========

An efficient cache backend for MySQL, to replace the Django's
database-agnostic ``DatabaseCache``.

Benefits
--------

* Each operation uses only one query - including the ``*_many`` methods. By
  contrast, ``DatabaseCache`` uses multiple queries for nearly every operation,
  and opens transactions for some.
* Automatic client-side ``zlib`` compression for objects over a threshold size,
  which can be tuned. Also it is easy to subclass and add your own compression
  schemes.
* Ability to turn down or off the slow cull-on-every-set behaviour from Django.
  This is left on by default to reduce surprise when moving from Django's
  DatabaseCache, but it is recommended you look at the settings when
  installing.

Usage
-----

To use, add an entry to your ``CACHES`` setting with the path to the backend,
for example::

    CACHES = {
        'default': {
            'BACKEND': 'django_mysql.cache.MySQLCache',
            'LOCATION': 'some_table_name'
        }
    }

You then need to make sure the table exists. The table schema is *not*
backwards compatible with that of ``DatabaseCache``, so if you are migrating,
you will need to create a fresh table (and copy data between the two via
``get`` and ``set`` calls if appropriate).

Generate a migration to add the table using the manage command
``mysql_cache_migration``. Save this to the `migrations` folder for one of your
project's apps. You might want to customize the SQL at this time, for example
switching the table to use the ``MEMORY`` storage engine.

Once you've run the migration, the cache is good to work.


Multiple Databases
------------------

If you use this with multiple databases, you'll also need to set up routing
instructions for your database cache table. This can be done the same way as
described for ``DatabaseCache`` in the
`Django manual
<https://docs.djangoproject.com/en/1.8/topics/cache/#database-caching>`_, apart
from the application name is ``django_mysql``.

.. note::

    Even if you aren't using multiple MySQL servers, it may be worth doing
    database routing anyway to put all your cache operations on a second
    connection - this way they won't be affected by transactions your main code
    runs.


Caveats
-----

``MySQLCache`` is fully compatible with Django's cache API, but there are of
course a few details to worry about.


incr/decr
~~~~~~~~~

Like ``MemcachedCache`` (and unlike ``DatabaseCache``), ``incr`` and ``decr``
are atomic, and can only be used with ``int`` values. They have the range of
MySQL's ``SIGNED BIGINT`` (-9223372036854775808 to 9223372036854775807).


max_allowed_packet
~~~~~~~~~~~~~~~~~~

MySQL has a setting called ``max_allowed_packet``, which is the maximum size of
a query, including data. This therefore constrains the size of a cached value,
but you're more likely to run up against it first with the
``get_many``/``set_many`` operations.

`The MySQL 5.5 default <https://dev.mysql.com/doc/refman/5.5/en/server-system-
variables.html#sysvar_max_allowed_packet>`_ is 1 MB, and `the MySQL 5.6 default
<https://dev.mysql.com/doc/refman/5.6/en/server-system-
variables.html#sysvar_max_allowed_packet>`_ is 4MB, with which most
applications will be fine. You can tweak it as high as 1GB (if this isn't
enough, you should probably be considering another solution!).
