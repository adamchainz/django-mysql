.. _tiny-integer-fields:

-------------------
Tiny integer fields
-------------------

.. currentmodule:: django_mysql.models

When working with integers that only take small values, Django’s default integer fields can be a bit wasteful as smallest field class, |SmallIntegerField|__, takes 2 bytes.
MySQL’s smallest integer data type, ``TINYINT``, is 1 byte, half the size!
The below field classes allow you to use the ``TINYINT`` and ``TINYINT UNSIGNED`` types in Django.

.. |SmallIntegerField| replace:: ``SmallIntegerField``
__ https://docs.djangoproject.com/en/stable/ref/models/fields/#django.db.models.SmallIntegerField

Docs:
`MySQL TINYINT <https://dev.mysql.com/doc/refman/en/integer-types.html>`_ /
`MariaDB <https://mariadb.com/kb/en/tinyint/>`_.

.. class:: TinyIntegerField(**kwargs)

    A subclass of Django’s :class:`~django.db.models.IntegerField` that uses a MySQL ``TINYINT`` type for storage.
    It supports signed integer values ranging from -128 to 127.

    Example:

    .. code-block:: python

        from django.db import models
        from myapp.fields import TinyIntegerField


        class ExampleModel(models.Model):
            tiny_value = TinyIntegerField()

.. class:: PositiveTinyIntegerField(**kwargs)

    A subclass of Django’s :class:`~django.db.models.PositiveIntegerField` that uses a MySQL ``TINYINT UNSIGNED`` type for storage.
    It supports unsigned integer values ranging from 0 to 255.

    Example:

    .. code-block:: python

        from django.db import models
        from myapp.fields import PositiveTinyIntegerField


        class ExampleModel(models.Model):
            positive_tiny_value = PositiveTinyIntegerField()
