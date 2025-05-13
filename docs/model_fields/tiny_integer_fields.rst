.. _tiny-integer-fields:

-------------------
Tiny integer fields
-------------------

.. currentmodule:: django_mysql.models

When working with integers that fit within small ranges, the default integer
fields can lead to excessive storage usage. MySQL’s ``TINYINT`` type allows
efficient storage by limiting the size to one byte.
The `TinyIntegerField` and `PositiveTinyIntegerField` make it easy to use
the ``TINYINT`` and ``TINYINT UNSIGNED`` types in Django.

Docs:
`MySQL TINYINT <https://dev.mysql.com/doc/refman/en/numeric-types.html>`_ /
`MariaDB <https://mariadb.com/kb/en/tinyint/>`_.

.. class:: TinyIntegerField(**kwargs)

    A subclass of Django’s :class:`~django.db.models.SmallIntegerField` that uses a MySQL
    ``TINYINT`` type for storage. It supports signed integer values ranging from -128 to 127.

    Example:

    .. code-block:: python

        from django.db import models
        from myapp.fields import TinyIntegerField


        class ExampleModel(models.Model):
            tiny_value = TinyIntegerField()

.. class:: PositiveTinyIntegerField(**kwargs)

    A subclass of Django’s :class:`~django.db.models.PositiveSmallIntegerField` that uses a
    MySQL ``TINYINT UNSIGNED`` type for storage. It supports unsigned integer values ranging
    from 0 to 255.

    Example:

    .. code-block:: python

        from django.db import models
        from myapp.fields import PositiveTinyIntegerField


        class ExampleModel(models.Model):
            positive_tiny_value = PositiveTinyIntegerField()

.. note::
    Ensure that existing data values fall within the specified ranges before migrating
    to this field, as values outside these ranges will cause migration operations to fail.
