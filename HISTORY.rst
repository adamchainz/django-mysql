.. :changelog:

History
=======

0.1.7 (pending)
---------------

* Renamed ``connection_name`` argument to ``using`` on ``Lock``,
  ``GlobalStatus``, and ``SessionStatus`` classes, for more consistency with
  Django.


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
