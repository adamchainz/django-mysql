.. :changelog:

History
=======

Pending
-------

* New release notes here

1.0.9 (2016-05-12)
------------------

* Fixed some features to work when there are non-MySQL databases configured
* Fixed ``JSONField`` to allow control characters, which MySQL does - but not
  in a top-level string, only inside a JSON object/array.

1.0.8 (2016-04-08)
------------------

* ``SmartChunkedIterator`` now fails properly for models whose primary key is a
  non-integer foreign key.
* ``pty`` is no longer imported at the top-level in ``django_mysql.utils``,
  fixing Windows compatibility.


1.0.7 (2016-03-04)
------------------

* Added new ``JSONField`` class backed by the JSON type added in MySQL 5.7.
* Added database functions ``JSONExtract``, ``JSONKeys``, and ``JSONLength``
  that wrap the JSON functions added in MySQL 5.7, which can be used with the
  JSON type columns as well as JSON data held in text/varchar columns.
* Added ``If`` database function for simple conditionals.


1.0.6 (2016-02-26)
------------------

* Now MySQL 5.7 compatible
* The final message from ``SmartChunkedIterator`` is now rounded to the nearest
  second.
* ``Lock`` and ``TableLock`` classes now have ``acquire`` and ``release()``
  methods for using them as normal objects rather than context managers

1.0.5 (2016-02-10)
------------------

* Added ``manage.py`` command ``fix_datetime_columns`` that outputs the SQL
  necessary to fix any ``datetime`` columns into ``datetime(6)``, as required
  when upgrading a database to MySQL 5.6+, or MariaDB 5.3+.
* ``SmartChunkedIterator`` output now includes the total time taken and number
  of objects iterated over in the final message.


1.0.4 (2016-02-02)
------------------

* Fixed the new system checks to actually work


1.0.3 (2016-02-02)
------------------

* Fixed ``EnumField`` so that it works properly with forms, and does not accept
  the ``max_length`` argument.
* ``SmartChunkedIterator`` output has been fixed for reversed iteration, and
  now includes a time estimate.
* Added three system checks that give warnings if the MySQL configuration can
  (probably) be improved.


1.0.2 (2016-01-24)
------------------

* New function ``add_QuerySetMixin`` allows addding the ``QuerySetMixin`` to
  arbitrary ``QuerySet``\s, for when you can't edit a model class.
* Added field class ``EnumField`` that uses MySQL's ``ENUM`` data type.

1.0.1 (2015-11-18)
------------------

* Added ``chunk_min`` argument to ``SmartChunkedIterator``

1.0.0 (2015-10-29)
------------------

* Changed version number to 1.0.0 to indicate maturity.
* Added ``DynamicField`` for using MariaDB's Named Dynamic Columns, and related
  database functions ``ColumnAdd``, ``ColumnDelete``, and ``ColumnGet``.
* ``SmartChunkedIterator`` with ``report_progress=True`` correctly reports
  'lowest pk so far' when iterating in reverse.
* Fix broken import paths during ``deconstruct()`` for subclasses of all
  fields: ``ListCharField``, ``ListTextField``, ``SetCharField``,
  ``SetTextField``, ``SizedBinaryField`` and ``SizedTextField``
* Added XML database functions - ``UpdateXML`` and ``XMLExtractValue``.

0.2.3 (2015-10-12)
------------------

* Allow ``approx_count`` on QuerySets for which only query hints have been used
* Added index query hints to ``QuerySet`` methods, via query-rewriting layer
* Added ``ordering`` parameter to ``GroupConcat`` to specify the ``ORDER BY``
  clause
* Added index query hints to ``QuerySet`` methods, via query-rewriting layer
* Added ``sql_calc_found_rows()`` query hint that calculates the total rows
  that match when you only take a slice, which becomes available on the
  ``found_rows`` attribute
* Made ``SmartChunkedIterator`` work with ``reverse()``'d ``QuerySet``\s

0.2.2 (2015-09-03)
------------------

* ``SmartChunkedIterator`` now takes an argument ``chunk_size`` as the initial
  chunk size
* ``SmartChunkedIterator`` now allows models whose primary key is a
  ``ForeignKey``
* Added ``iter_smart_pk_ranges`` which is similar to ``iter_smart_chunks`` but
  yields only the start and end primary keys for each chunks, in a tuple.
* Added prefix methods to ``MySQLCache`` - ``delete_with_prefix``,
  ``get_with_prefix``, ``keys_with_prefix``
* Added ``Bit1BooleanField`` and ``NullBit1BooleanField`` model fields that
  work with boolean fields built by other databases that use the ``BIT(1)``
  column type

0.2.1 (2015-06-22)
------------------

* Added Regexp database functions for MariaDB - ``RegexpInstr``,
  ``RegexpReplace``, and ``RegexpSubstr``
* Added the option to not limit the size of a ``MySQLCache`` by setting
  ``MAX_ENTRIES`` = -1.
* ``MySQLCache`` performance improvements in `get`, `get_many`, and `has_key`
* Added query-rewriting layer added which allows the use of MySQL query hints
  such as ``STRAIGHT_JOIN`` via QuerySet methods, as well as adding label
  comments to track where queries are generated.
* Added ``TableLock`` context manager

0.2.0 (2015-05-14)
------------------

* More database functions added - ``Field`` and its complement ``ELT``,
  and ``LastInsertId``
* Case sensitive string lookup added as to the ORM for ``CharField`` and
  ``TextField``
* Migration operations added - ``InstallPlugin``, ``InstallSOName``, and
  ``AlterStorageEngine``
* Extra ORM aggregates added - ``BitAnd``, ``BitOr``, and ``BitXor``
* ``MySQLCache`` is now case-sensitive. If you are already using it, an upgrade
  ``ALTER TABLE`` and migration is provided at `the end of the cache docs
  <http://django-mysql.readthedocs.org/en/latest/cache.html>`_.
* (MariaDB only) The ``Lock`` class gained a class method ``held_with_prefix``
  to query held locks matching a given prefix
* ``SmartIterator`` bugfix for chunks with 0 objects slowing iteration; they
  such chunks most often occur on tables with primary key "holes"
* Now tested against Django master for cutting edge users and forwards
  compatibility

0.1.10 (2015-04-30)
-------------------

* Added the ``MySQLCache`` backend for use with Django's caching framework, a
  more efficient version of ``DatabaseCache``
* Fix a ``ZeroDivision`` error in ``WeightedAverageRate``, which is used in
  smart iteration

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
