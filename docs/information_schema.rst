.. _information_schema:

==================
Information Schema
==================

.. currentmodule:: django_mysql.models.functions

MySQL provides the ``information_schema`` virtual database as a repository of
metadata. It contains read-only tables that allow you to query such things as
the number of tables, their size, the existing foreign key constraints, etc.

This module provides Django models that point at those tables, allowing you to
query them for table metadata.

Docs:
`MySQL <https://dev.mysql.com/doc/refman/5.5/en/information-schema.html>`_ /
`MariaDB <https://mariadb.com/kb/en/mariadb/information-schema-tables/>`_.


.. class:: Table

    Represents table metadata. Most of the columns match up with the names in
    the table in lowercase, however to be more DRY the prefix ``table_`` has
    been removed from some. Consult the model file for more information.

    By default ``objects`` is filtered to only the tables in the current
    database. The manager that gives you access to all tables is called
    ``alldb_objects`` - you'll probably need this less often unless you are
    doing multi-database stuff.

    Note that when querying this you can greatly speed up queries by only
    selecting the fields you need with e.g. Django's ``only()`` method on
    ``QuerySet``\s, as some of the data takes time for MySQL to figure out.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/tables-table.html>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/information-schema-tables-table/>`_.

    Example usage:

    .. code-block:: pycon

        >>> from django_mysql.models import information_schema as i_s
        >>> # The number of tables in this database
        >>> i_s.Table.objects.all().count()
        34
        >>> i_s.Table.objects.values_list('name', 'avg_row_length') \
        ...                  .order_by('-avg_row_length')[0]
        ('django_migrations', 1638)

    .. classmethod:: for_model(model)

        A class method for getting the ``Table`` related to a given model.

        Example usage:

        .. code-block:: pycon

            >>> from django.contrib.auth.models import User
            >>> user_table = i_s.Table.for_model(User)
            >>> user_table.rows  # The approximate number of users
            1273
