.. :changelog:

History
=======

0.1.9 (2015-04-20)
------------------

* ``pt_visual_explain`` no longer executes the given query before fetching its
  ``EXPLAIN``
* New ``pt_fingerprint`` function that wraps the ``pt-fingerprint`` tool
  efficiently
* For ``List`` fields, the new ``ListF`` class allows you to do atomic append
  or pop operations from either end of the list in a single query
* For ``Set`` fields, the new ``SetF`` class allows you to do atomic add or
  remove operatiosn from the set in a single query
* The ``@override_mysql_variables`` decorator has been introduced which makes
  testing code with different MySQL configurations easy
* The ``is_mariadb`` property gets added onto Django's MySQL ``connection``
  class automatically
* A race condition in determining the minimum and maximum primary key values
  for smart iteration was fixed.


0.1.8 (2015-03-31)
------------------

* Add ``Set`` and ``List`` fields which can store comma-separated sets and
  lists of a base field with MySQL-specific lookups
* Support MySQL's ``GROUP_CONCAT`` as an aggregate!
* Add a ``functions`` module with many MySQL-specific functions for the new
  Django 1.8 database functions feature
* Allow access of the global and session status for the default connection from
  a lazy singleton, similar to Django's ``connection`` object
* Fix a different recursion error on ``count_tries_approx``


0.1.7 (2015-03-25)
------------------

* Renamed ``connection_name`` argument to ``using`` on ``Lock``,
  ``GlobalStatus``, and ``SessionStatus`` classes, for more consistency with
  Django.
* Fix recursion error on ``QuerySetMixin`` when using ``count_tries_approx``


0.1.6 (2015-03-21)
------------------

* Added support for ``HANDLER`` statements as a ``QuerySet`` extension
* Now tested on Django 1.8
* Add ``pk_range`` argument for 'smart iteration' code


0.1.5 (2015-03-11)
------------------

* Added ``manage.py`` command ``dbparams`` for outputting database paramters
  in formats useful for shell scripts


0.1.4 (2015-03-10)
------------------

* Fix release process


0.1.3 (2015-03-08)
------------------

* Added ``pt_visual_explain`` integration on ``QuerySet``
* Added soundex-based field lookups for the ORM


0.1.2 (2015-03-01)
------------------

* Added ``get_many`` to ``GlobalStatus``
* Added ``wait_until_load_low`` to ``GlobalStatus`` which allows you to wait
  for any high load on your database server to dissipate.
* Added smart iteration classes and methods for ``QuerySet``\s that allow
  efficient iteration over very large sets of objects slice-by-slice.

0.1.1 (2015-02-23)
------------------

* Added ``Model`` and ``QuerySet`` subclasses which add the ``approx_count``
  method

0.1.0 (2015-02-12)
---------------------

* First release on PyPI
* ``Lock``\s
* ``GlobalStatus`` and ``SessionStatus``
