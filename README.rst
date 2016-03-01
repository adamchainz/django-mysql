============
Django-MySQL
============

.. image:: https://img.shields.io/pypi/v/django-mysql.svg
    :target: https://pypi.python.org/pypi/django-mysql

.. image:: https://travis-ci.org/adamchainz/django-mysql.svg?branch=master
        :target: https://travis-ci.org/adamchainz/django-mysql

.. image:: https://coveralls.io/repos/adamchainz/django-mysql/badge.svg
        :target: https://coveralls.io/r/adamchainz/django-mysql

.. image:: https://img.shields.io/pypi/dm/django-mysql.svg
        :target: https://pypi.python.org/pypi/django-mysql

.. image:: https://readthedocs.org/projects/django-mysql/badge/?version=latest
        :target: http://django-mysql.readthedocs.org/en/latest/


.. figure:: https://raw.github.com/adamchainz/django-mysql/master/docs/images/dolphin-pony.png
   :alt: The dolphin-pony - proof that cute + cute = double cute.

..

    | The dolphin-pony - proof that cute + cute = double cute.


Django-MySQL is a non-inventively named package that helps you use some
MySQL/MariaDB-specific features in the world of Django.


What kind of features?
----------------------

Includes:

* ``QuerySet`` extensions:

  * 'Smart' iteration - chunked pagination across a large queryset
  * ``approx_count`` for quick estimates of ``count()``
  * Query hints
  * Quick ``pt-visual-explain`` of the underlying query

* Model fields:

  * MySQL 5.7+ JSON Field
  * MariaDB Dynamic Columns for storing dictionaries
  * Comma-separated fields for storing lists and sets
  * 'Missing' fields: differently sized ``BinaryField``/``TextField`` classes,
    ``BooleanField``\s represented by BIT(1)

* ORM expressions for over 20 MySQL-specific functions
* A new cache backend that makes use of MySQL's upsert statement and does
  compression
* Handler API for quicker-than-SQL reads using the 'NoSQL' HANDLER commands
* Status variable inspection and utility methods
* Named locks for easy locking of e.g. external resources
* Table lock manager for hard to pull off data migrations

To see them all, check out the exposition at
http://django-mysql.readthedocs.org/en/latest/exposition.html .


Requirements
------------

Tested with all combinations of:

* Python: 2.7, 3.4, 3.5
* Django: 1.7, 1.8, 1.9, master
* MySQL: 5.5, 5.6, 5.7 / MariaDB: 5.5, 10.0, 10.1
* mysqlclient: 1.3.7 (Python 3 compatible version of ``MySQL-python``)

Any combination of these should be good, and also ``MySQL-python`` should work
since it's just an older version of ``mysqlclient`` - however you should
probably just upgrade.

Please note that some features are restricted to particular databases, database
versions or Django versions - all such restrictions can be found in the
documentation for each feature.


Documentation
-------------

Every detail documented on
`Read The Docs <https://django-mysql.readthedocs.org/en/latest/>`_.
