.. _management_commands:

===================
Management Commands
===================


MySQL-specific management commands. These are automatically available with
your ``manage.py`` when you add ``django_mysql`` to your ``INSTALLED_APPS``.

.. _dbparams:

--------
dbparams
--------

Outputs your database connection parameters in a form suitable for inclusion in
other CLI commands, helping avoid copy/paste errors and accidental copying of
passwords to shell history files. Knows how to output parameters in two formats
- for ``mysql`` related tools, or the DSN format that some percona tools take.
For example:

.. code-block:: console

    $ python manage.py dbparams
    --user=ausername --password=apassword --host=ahost.example.com mydatabase
    $ mysql $(python manage.py dbparams)  # The same as manage.py dbshell
    $ mysqldump $(python manage.py dbparams)  # Aha

The format of parameters is::

    python manage.py dbparams [--mysql | --dsn] <optional db alias>

If the database alias is given, it should be alias of a connection from the
``DATABASES`` setting; defaults to 'default'. Only MySQL connections are
supported - the command will fail for other connection vendors.

Mutually exclusive format flags:

``--mysql``
-----------

    Default, so shouldn't need passing. Allows you to do, e.g.:

    .. code-block:: console

        $ mysqldump $(python manage.py dbparams)

    Which will translate to include all the relevant flags, including your
    database.

``--dsn``
---------

    Outputs the parameters in the DSN format, which is what many percona tools
    take, e.g.:

    .. code-block:: console

        $ pt-online-schema-change $(python manage.py --dsn),t=app_author \
              --alter "ENGINE=INNODB"

    .. note::

        If you are using SSL to connect, the percona tools don't support SSL
        configuration being given in their DSN format; you must pass them via a
        MySQL configuration file instead.  ``dbparams`` will output a warning
        on stderr if this is the case. For more info see the `percona blog
        <http://www.percona.com/blog/2014/10/16/percona-toolkit-for-mysql-with-mysql-ssl-connections/>`_.
