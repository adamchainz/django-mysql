Checks
======

Django-MySQL runs some extra checks as part of Django's check framework to
ensure your configuration for Django + MySQL is optimal. If triggered, the
checks give a brief message, and a link here for documentation on how to fix
it.

.. note::

    A reminder: as per
    `the Django docs <https://docs.djangoproject.com/en/1.9/ref/settings/#std:setting-SILENCED_SYSTEM_CHECKS>`_,
    you can silence individual checks in your settings. For example, if you
    determine ``django_mysql.W002`` doesn't require your attention, add the
    following to ``settings.py``:

    .. code-block:: python

        SILENCED_SYSTEM_CHECKS = [
            'django_mysql.W002',
        ]


django_mysql.W001: Strict Mode
------------------------------

MySQL's Strict Mode fixes many data integrity problems in MySQL, such as data
truncation upon insertion, by escalating warnings into errors. It is strongly
recommended you activate it.

Docs:
`MySQL <https://dev.mysql.com/doc/refman/5.5/en/sql-mode.html#sql-mode-strict>`_ /
`MariaDB <https://mariadb.com/kb/en/mariadb/sql_mode/#strict-mode>`_.

It is configured as part of ``sql_mode``, a system variable contains a list of
comma-separated modes to activate. Please check the value of your install and
update it as necessary to add ``STRICT_TRANS_TABLES`` (the default in MySQL 5.7
onwards) - the following instructions assume it is set to the empty string
initially, which is the MySQL 5.5 default.

The easiest way to change ``sql_mode`` for your app is to set it from the
``init_command`` that is run on each new connection by ``MySQLdb``:

.. code-block:: python

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'my_database',
            'OPTIONS': {
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }

This sets it for your app, but it does not set it for other connections to your
database server. There is also a roundtrip added for sending a command to the
server on each new connection.

You can change ``sql_mode`` permanently by using ``SET GLOBAL`` from an admin
user on the server, plus changing your configuration files so the setting
survives a server restart. For more information, see
`Using System Variables system variables <https://dev.mysql.com/doc/refman/5.5/en/using-system-variables.html>`_
in the MySQL documentation.


django_mysql.W002: InnoDB Strict Mode
-------------------------------------

InnoDB Strict Mode is similar to the general Strict Mode, but for InnoDB. It
escalates several warnings around InnoDB-specific statements into errors.
Normally this just affects per-table settings for compression. It's recommended
you activate this, but it's not very likely to affect you if you don't.

Docs:
`MySQL <https://dev.mysql.com/doc/refman/5.5/en/innodb-parameters.html#sysvar_innodb_strict_mode>`_ /
`MariaDB <https://mariadb.com/kb/en/mariadb/xtradbinnodb-strict-mode/>`_.

As above, the easiest way to set this is to add ``SET`` to ``init_command`` in
your ``DATABASES`` setting:

.. code-block:: python

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'my_database',
            'OPTIONS': {
                'init_command': 'SET innodb_strict_mode=1',
            },
        }
    }

.. note::

    If you use this along with the ``init_command`` for W001, combine them
    as ``SET sql_mode='STRICT_TRANS_TABLES', innodb_strict_mode=1``.

Also, as above for ``django_mysql.W001``, it's better that you set it
permanently for the server with ``SET GLOBAL`` and a configuration file change.

django_mysql.W003: utf8mb4
--------------------------

MySQL's ``utf8`` character set does not include support for the largest, 4 byte
characters in UTF-8; this basically means it cannot support emoji and custom
Unicode characters. The ``utf8mb4`` character set was added to support all
these characters, and there's really little point in not using it. Django
currently suggests using the ``utf8`` character set for backwards
compatibility, but it's likely to move in time.

It's strongly recommended you change to the ``utf8mb4`` character set and
convert your existing ``utf8`` data as well, unless you're absolutely sure
you'll never see any of these 'supplementary' Unicode characters (note: it's
very easy for users to type emoji on phone keyboards these days!).

Docs:
`MySQL <https://dev.mysql.com/doc/refman/5.5/en/charset-unicode-utf8mb4.html>`_ /
`MariaDB <https://mariadb.com/kb/en/mariadb/unicode/>`_.

Also see this classic blogpost:
`How to support full Unicode in MySQL databases <https://mathiasbynens.be/notes/mysql-utf8mb4>`_.

The easiest way to set this up is to make a couple of changes to your
``DATABASES`` settings. First, add ``OPTIONS`` with ``charset`` to your MySQL
connection, so ``MySQLdb`` connects using the ``utf8mb4`` character set.
Second, add ``TEST`` with ``COLLATION`` and ``CHARSET`` as below, so Django
creates the test database, and thus all tables, with the right character set:

.. code-block:: python

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'my_database',
            'OPTIONS': {
                # Tell MySQLdb to connect with 'utf8mb4' character set
                'charset': 'utf8mb4',
            },
            # Tell Django to build the test database with the 'utf8mb4' character set
            'TEST': {
                'CHARSET': 'utf8mb4',
                'COLLATION': 'utf8mb4_unicode_ci',
            }
        }
    }

Note this does not transform the database, tables, and columns that already
exist. Follow the examples in the 'How to' blog post link above to fix your
database, tables, and character set. It's planned to add a command to
Django-MySQL to help you do this, see
`Issue 216 <https://github.com/adamchainz/django-mysql/issues/216>`_.
