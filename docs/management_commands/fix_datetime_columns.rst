.. _fix_datetime_columns:

================================
``fix_datetime_columns`` command
================================

This command scans your database and outputs the SQL necessary to fix any
``datetime`` columns into ``datetime(6)`` columns, as is necessary when
upgrading to MySQL 5.6, or MariaDB 5.3+.

If you upgrade MySQL to 5.6, Django will have created all your
``DateTimeField``\s as ``datetime``, although they can be turned into
``datetime(6)`` now with microsecond support. Even if microsecond support is
not necessary for your database, it's best to convert them over so that you
aren't surprised by a future migration that upgrades them; Django's migration
system doesn't check the type in the database and will assume all
``DateTimeField``\s are already ``datetime(6)``.

Example usage:

.. code-block:: sh

    $ python manage.py fix_datetime_columns
    ALTER TABLE `app1_table1`
        MODIFY COLUMN `created_time` datetime(6) DEFAULT NULL;
    ALTER TABLE `app1_table2`
        MODIFY COLUMN `created_time` datetime(6) DEFAULT NULL,
        MODIFY COLUMN `updated_time` datetime(6) DEFAULT NULL;

You can run this SQL straight away with:

.. code-block:: sh

    $ python manage.py fix_datetime_columns | python manage.py dbshell

However you might want to put the SQL into a file and run it as a Django
migration, or use tools such as
`pt-online-schema-change <https://www.percona.com/doc/percona-toolkit/2.2/pt-online-schema-change.html>`_.

The format of parameters is:

.. code-block:: sh

    $ python manage.py fix_datetime_columns <optional-connection-alias>

If the database alias is given, it should be alias of a connection from the
``DATABASES`` setting; defaults to 'default'. Only MySQL connections are
supported - the command will fail for other connection vendors.
