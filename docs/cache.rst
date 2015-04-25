.. _cache:

=====
Cache
=====

A new cache backend for ``django.core.cache``.

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
* Automatic client-side ``zlib`` compression for objects larger than a given
  threshold. It is also easy to subclass and add your own compression schemes.
* Faster probabilistic culling behaviour, which you can also turn off and
  execute in a background task. This can be a bottleneck with Django's
  ``DatabaseCache`` since it does a ``SELECT COUNT(*)`` on every ``set()``


Usage
-----

To use, add an entry to your ``CACHES`` setting with:

* ``BACKEND`` set to ``django_mysql.cache.MySQLCache``

* ``LOCATION`` set to ``tablename``, the name of the table to use. This name
  can be whatever you want, as long as it's a valid table name that's not
  already being used in your database.

For example::

    CACHES = {
        'default': {
            'BACKEND': 'django_mysql.cache.MySQLCache',
            'LOCATION': 'my_super_cache'
        }
    }

You then need to make the table. The table schema is *not* compatible with that
of ``DatabaseCache``, so if you are switching, you will need to create a fresh
table (and copy data between the two via ``get`` and ``set`` calls if
appropriate).

Use the management command ``mysql_cache_migration`` to print out a migration
to create tables for all the ``MySQLCache`` instances you have configured. For
example::

    $ python manage.py mysql_cache_migration
    from django.db import migrations


    class Migration(migrations.Migration):

        operations = [
            migrations.RunSQL(
                """
                CREATE TABLE `my_super_cache` (
                    cache_key varchar(255) CHARACTER SET utf8 NOT NULL PRIMARY KEY,
                    value longblob NOT NULL,
                    value_type char(1) CHARACTER SET latin1 NOT NULL DEFAULT 'p',
                    expires BIGINT UNSIGNED NOT NULL
                );
                """,
                "DROP TABLE `my_super_cache`;"
            ),
        ]

Save this to a file in the ``migrations`` directory of one of your project's
apps. You might want to customize the SQL at this time, for example switching
the table to use the ``MEMORY`` storage engine.

Once the migration has run, the cache will work!


Multiple Databases
------------------

If you use this with multiple databases, you'll also need to set up routing
instructions for the cache table. This can be done the same way as described
for ``DatabaseCache`` in the `Django manual
<https://docs.djangoproject.com/en/1.8/topics/cache/#database-caching>`_, apart
from the application name is ``django_mysql``.

.. note::

    Even if you aren't using multiple MySQL servers, it may be worth using
    database routing anyway to put all your cache operations on a second
    connection - this way they won't be affected by transactions your main code
    runs.


Extra Details
-------------

``MySQLCache`` is fully compatible with Django's cache API, but it also extends
it and there are, of course, a few details to consider.


incr/decr
~~~~~~~~~

Like ``MemcachedCache`` (and unlike ``DatabaseCache``), ``incr`` and ``decr``
are atomic operations, and can only be used with ``int`` values. They have the
range of MySQL's ``SIGNED BIGINT`` (-9223372036854775808 to
9223372036854775807).


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


culling
~~~~~~~

Databases are designed to store data forever, and thus don't have a way of
setting rows to disappear - thus the expiration of old keys and the limiting of
rows to ``MAX_ENTRIES`` is performed in the cache code by performing a cull
operation when appropriate. This deletes expired keys first, then if there are
still more than ``MAX_ENTRIES`` keys, deletes 1 / ``CULL_FREQUENCY`` of them.

The ``MAX_ENTRIES`` and ``CULL_FREQUENCY`` options are set in ``OPTIONS``, as
noted in the `Django manual
<https://docs.djangoproject.com/en/1.8/topics/cache/#cache-arguments>`_.

Django's ``DatabaseCache`` performs a cull check on *every* write operation,
which means performing a ``SELECT COUNT(*)`` on the table, which means a
slow full-table scan. This easily becomes a bottleneck for even modest amounts
of caching. ``MySQLCache`` helps you solve this in two ways:

1. The cull-on-set behaviour is probabilistic. An extra setting in ``OPTIONS``
   is available called ``CULL_PROBABILITY``, which should be a number between 0
   and 1, defaulting to ``0.01``. This is the probability of performing a cull
   operation to fit under ``MAX_ENTRIES`` on a write operation. Thus by default
   only 1% of write operations will try to get rid of old data, making the
   remaining 99% faster.

   If you want to use the same cull-on-*every*-write behaviour as
   ``DatabaseCache``, set ``CULL_PROBABILITY`` to 1.0::

       CACHES = {
           'default': {
               'BACKEND': 'django_mysql.cache.MySQLCache',
               'LOCATION': 'some_table_name',
               'OPTIONS': {
                   'CULL_PROBABILITY': 1.0
               }
           }
       }


2. The ``cull()`` method is available as a public API so you can set up your
   own culling schedule in background tasks, never affecting any user-facing
   web requests. For example, you could create a periodic **celery** task to
   do this::

       @shared_task
       def clear_caches():
           cache.cull()
           caches['my_cache'].cull()

   This functionality is also available as the management command
   ``cull_mysql_caches``, which you might run as a cron job. It performs
   ``cull()`` on all of your ``MySQLCache`` instances, or you can give it names
   to just cull those. For example, this::

       $ python manage.py cull_mysql_caches default supercache

   ...will call ``caches['default'].cull()`` and
   ``caches['supercache'].cull()``.

   If you're using this, you should set ``CULL_PROBABILITY`` to 0 so that no
   culling occurs on write operations such as ``set()``.


compression
~~~~~~~~~~~

Stored objects are serialized via ``pickle`` (except from integers). If an
object's pickled representation is above the threshold defined by the option
``COMPRESS_MIN_LENGTH``, it will be compressed with ``zlib`` in Python before
being stored, reducing the on-disk size in MySQL and the network cost for the
query. The zlib level is set by the option ``COMPRESS_LEVEL``. You can tune
these options, for example to compress all objects > 100 bytes at the maximum
level 9::

    CACHES = {
        'default': {
            'BACKEND': 'django_mysql.cache.MySQLCache',
            'LOCATION': 'some_table_name',
            'OPTIONS': {
                'COMPRESS_MIN_LENGTH': 100,
                'COMPRESS_LEVEL': 9
            }
        }
    }

To turn compression off, set ``COMPRESS_MIN_LENGTH`` to 0. This only affects
writes - any compressed values already in the table will remain readable.


custom serialization schemes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can implement your own encoding schemes by subclassing ``MySQLCache``. It
uses two methods to serialize and deserialize objects that you can wrap.

Values are stored in the table with two columns - ``value``, which is a blob of
binary data, and ``value_type``, a single latin1 character that specifies the
type of data in ``value``. MySQLCache by default uses three codes for
``value_type``:

* ``i`` - The blob is a string of an integer value. This is used so that integer
  counters can be deserialized by MySQL during ``incr()``/``decr()``
  operations.
* ``p`` - The blob is a pickled Python object.
* ``z`` - The blob is a zlib-compressed pickled Python object.

For future compatibility, ``MySQLCache`` reserves all ``value_type`` codes that
are lowercase letters. For custom types you should use uppercase letters.

The methods you need to override (and probably call ``super()`` from) are:

.. method:: encode(obj)

    Takes an object and returns a tuple ``(value, value_type)``, ready to be
    inserted as parameters into the SQL query.

.. method:: decode(value, value_type)

    Takes the pair of ``(value, value_type)`` as stored in the table and
    returns the deserialized object.
