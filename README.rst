============
Django MySQL
============

.. image:: https://badge.fury.io/py/django-mysql.png
    :target: http://badge.fury.io/py/django-mysql

.. image:: https://travis-ci.org/adamchainz/django-mysql.png?branch=master
        :target: https://travis-ci.org/adamchainz/django-mysql

.. image:: https://coveralls.io/repos/adamchainz/django-mysql/badge.svg
        :target: https://coveralls.io/r/adamchainz/django-mysql

.. image:: https://pypip.in/d/django-mysql/badge.png
        :target: https://pypi.python.org/pypi/django-mysql

.. image:: https://readthedocs.org/projects/django-mysql/badge/?version=latest
        :target: http://django-mysql.readthedocs.org/en/latest/

.. image:: https://landscape.io/github/adamchainz/django-mysql/master/landscape.svg?style=flat
   :target: https://landscape.io/github/adamchainz/django-mysql/master
   :alt: Code Health


.. figure:: https://raw.github.com/adamchainz/django-mysql/master/docs/images/dolphin-pony.png
   :alt: The dolphin-pony - taking two cute things and ending up with something
     quite scary

..

    | The dolphin-pony - taking two cute things and ending up with something
    | quite scary.


MySQL and its fork MariaDB have a number of features which are not available in
vanilla Django - this package helps you get at them.


Featuring
---------

Here's a short list of what's inside:

* User locks - easy locking between your distributed servers
* Easy access to server status variables
* ``approx_count`` on ``QuerySet`` for quick estimates of the number of
  objects - and a quicker admin
* 'Smart' iteration methods on ``QuerySet`` for efficient iteration over large
  sets of objects slice-by-slice

All are documented at http://django-mysql.readthedocs.org/en/latest/ .

Requirements
------------

Tested with:

* Python: 2.7, 3.3, 3.4
* Django: 1.7
* MySQL: 5.5, 5.6 / MariaDB: 5.5, 10.0, 10.1
* mysqlclient: 1.3.5 (Python 3 compatible version of ``MySQL-python``)

Any combination of these should be good.
