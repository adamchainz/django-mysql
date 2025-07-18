Checks
======

Django-MySQL adds some extra checks to Django's system check framework to
advise on your database configuration. If triggered, the checks give a brief
message, and a link here for documentation on how to fix it.

.. warning::

    From Django 3.1 onwards, database checks are not automatically run in most
    situations. You should use the ``--database`` argument to
    ``manage.py check`` to run the checks. For example, with just one database
    connection you can run ``manage.py check --database default``.

.. note::

    A reminder: as per
    `the Django docs <https://docs.djangoproject.com/en/3.0/ref/settings/#std:setting-SILENCED_SYSTEM_CHECKS>`_,
    you can silence individual checks in your settings. For example, if you
    determine ``django_mysql.W002`` doesn't require your attention, add the
    following to ``settings.py``:

    .. code-block:: python

        SILENCED_SYSTEM_CHECKS = [
            "django_mysql.W002",
        ]


django_mysql.W001: Strict Mode
------------------------------

This check has been removed since Django itself includes such a check,
``mysql.W002``, since version 1.10. See `its documentation
<https://docs.djangoproject.com/en/stable/ref/checks/#mysql-and-mariadb>`__.


django_mysql.W002: InnoDB Strict Mode
-------------------------------------

InnoDB Strict Mode is similar to the general Strict Mode, but for InnoDB. It
escalates several warnings around InnoDB-specific statements into errors.
Normally this just affects per-table settings for compression. It's recommended
you activate this, but it's not very likely to affect you if you don't.

Docs:
`MySQL <https://dev.mysql.com/doc/refman/en/innodb-parameters.html#sysvar_innodb_strict_mode>`__ /
`MariaDB <https://mariadb.com/docs/server/server-usage/storage-engines/innodb/innodb-system-variables#innodb_strict_mode>`__.

As above, the easiest way to set this is to add ``SET`` to ``init_command`` in
your ``DATABASES`` setting:

.. code-block:: python

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": "my_database",
            "OPTIONS": {
                "init_command": "SET innodb_strict_mode=1",
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
`MySQL <https://dev.mysql.com/doc/refman/en/charset-unicode-utf8mb4.html>`__ /
`MariaDB <https://mariadb.com/docs/server/reference/data-types/string-data-types/character-sets/unicode>`__.

Also see this classic blogpost:
`How to support full Unicode in MySQL databases <https://mathiasbynens.be/notes/mysql-utf8mb4>`_.

The easiest way to set this up is to make a couple of changes to your
``DATABASES`` settings. First, add ``OPTIONS`` with ``charset`` to your MySQL
connection, so ``MySQLdb`` connects using the ``utf8mb4`` character set.
Second, add ``TEST`` with ``COLLATION`` and ``CHARSET`` as below, so Django
creates the test database, and thus all tables, with the right character set:

.. code-block:: python

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": "my_database",
            "OPTIONS": {
                # Tell MySQLdb to connect with 'utf8mb4' character set
                "charset": "utf8mb4",
            },
            # Tell Django to build the test database with the 'utf8mb4' character set
            "TEST": {
                "CHARSET": "utf8mb4",
                "COLLATION": "utf8mb4_unicode_ci",
            },
        }
    }

Note this does not transform the database, tables, and columns that already
exist. Follow the examples in the 'How to' blog post link above to fix your
database, tables, and character set. It's planned to add a command to
Django-MySQL to help you do this, see
`Issue 216 <https://github.com/adamchainz/django-mysql/issues/216>`__.
