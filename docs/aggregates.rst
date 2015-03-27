.. _aggregates:

==========
Aggregates
==========

.. currentmodule:: django_mysql.models

MySQL-specific `database aggregates
<https://docs.djangoproject.com/en/dev/topics/db/aggregation/>`_
for the ORM.

The following can be imported from ``django_mysql.models``.

.. class:: GroupConcat(column, distinct=False, separator=',')

    An aggregate that concatenates values from a column of the grouped rows.
    Useful mostly for bringing back lists of ids in a single query.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/group-by-functions.html#function_group-concat>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/group_concat/>`_.

    Example usage::

            >>> from django_mysql.models import GroupConcat
            >>> author = Author.objects.annotate(
            ...     book_ids=GroupConcat('books__id')
            ... ).get(name="William Shakespeare")
            >>> author.book_ids
            "1,2,5,17,29"

    .. warning::

        MySQL will truncate the value at the value of ``group_concat_max_len``,
        which by default is quite low at 1024 characters. You should probably
        increase it if you're using this for any sizeable groups.

        ``group_concat_max_len`` docs:
        `MySQL <https://dev.mysql.com/doc/refman/5.5/en/server-system-variables.html#sysvar_group_concat_max_len>`_ /
        `MariaDB <https://mariadb.com/kb/en/server-system-variables/#group_concat_max_len>`_.

    Has two optional arguments:

    .. attribute:: distinct=False

        If set to ``True``, removes duplicates from the group.

    .. attribute:: separator=','

        By default the separator is a comma. You can use any other string as a
        separator, including the empty string.

        .. warning::

            Due to limitations in the Django aggregate API, this is not
            protected against SQL injection. Don't pass in user input for the
            separator.
