.. _enum-field:

---------
EnumField
---------

.. currentmodule:: django_mysql.models

Using a ``CharField`` with a limited set of strings leads to inefficient data
storage since the string value is stored over and over on disk. MySQL's
``ENUM`` type allows a more compact representation of such columns by storing
the list of strings just once and using an integer in each row to refer to
which string is there. ``EnumField`` allows you to use the ``ENUM`` type with
Django.


Docs:
`MySQL <https://dev.mysql.com/doc/refman/en/enum.html>`_ /
`MariaDB <https://mariadb.com/docs/server/reference/data-types/string-data-types/enum/>`_.


.. class:: EnumField(choices, **kwargs)

    A subclass of Django's :class:`~django.db.models.Charfield` that uses a
    MySQL ``ENUM`` for storage.

    ``choices`` is a standard Django argument for any field class, however it
    is required for ``EnumField``. It can either be a list of strings, or a
    list of two-tuples of strings, where the first element in each tuple is the
    value used, and the second the human readable name used in forms. The best
    way to form it is with Django’s |TextChoices enumeration type|__.

    .. |TextChoices enumeration type| replace:: ``TextChoices`` enumeration type
    __ https://docs.djangoproject.com/en/stable/ref/models/fields/#field-choices-enum-types

    For example:

    .. code-block:: python

        from django.db import models
        from django_mysql.models import EnumField


        class BookCoverColour(models.TextChoices):
            RED = "red"
            GREEN = "green"
            BLUE = "blue"


        class BookCover(models.Model):
            colour = EnumField(choices=BookCoverColour.choices)


    .. warning::
       It is possible to append new values to ``choices`` in migrations, as
       well as edit the *human readable* names of existing choices.

       However, editing or removing existing choice values will error if MySQL
       Strict Mode is on, and replace the values with the empty string if it is
       not.

       Also the empty string has strange behaviour with ``ENUM``, acting
       somewhat like ``NULL``, but not entirely. It is therefore recommended
       you ensure Strict Mode is on.
