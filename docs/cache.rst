.. _cache:

=====
Cache
=====


An efficient implementation of django's cache API for MySQL.

.. currentmodule:: django_mysql.cache

Benefits
--------

* Every operation is done in one query - get, set, add, delete, incr, decr, and
  all the _many methods. By contrast, the django default uses multiple queries
  for nearly every operation, including the overhead of setting up a
  transaction
* Automatic client-side zlib compression for objects over a given size, which
  can be tuned
* Ability to turn down or off the very slow cull-on-every-set behaviour (this
  is on by default to reduce surprise when moving from Django's DatabaseCache,
  but it is recommended you look at it).

Usage
-----

To use, add an entry to your CACHES setting, for example::

    CACHES = {
        'default': {
            'BACKEND': 'django_mysql.cache.MySQLCache',
            'LOCATION': 'some_table_name'
        }
    }

You then need to make sure the table exists. The table schema is NOT
backwards compatible with that of django's
:ref:`~django.core.cache.backends.db.DatabaseCache`, so you should make sure
you are creating a fresh table.

You can create a Django migration to do this with
``manage.py mysql_cache_migration`` which will output the python for a
migration that adds the table[s] for all your MySQLCache instances. You can
give one or more aliases from CACHES to generate statements for just those
caches.

You'll need to copy that output into a migration in your project to get
`migrate` to run it. This also allows you to customize the SQL, e.g. changing
the storage engine to ``MEMORY`` if appropriate.


.. warning:: max_allowed_packet

    Maximum size of a query!!


Separate Database connection
----------------------------
