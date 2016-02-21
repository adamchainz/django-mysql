.. _resizable-blob-text-fields:

----------------------------
Resizable Text/Binary Fields
----------------------------

.. currentmodule:: django_mysql.models

Django's :class:`~django.db.models.TextField` and
:class:`~django.db.models.BinaryField` fields are fixed at the MySQL level to
use the maximum size class for the ``BLOB`` and ``TEXT`` data types. This is
fine for most applications, however if you are working with a legacy database,
or you want to be stricter about the maximum size of data that can be stored,
you might want one of the other sizes.

The following field classes are simple subclasses that allow you to provide an
extra parameter to determine which size class to use. They work with
migrations, allowing you to swap them for the existing Django class and then
use a migration to change their size class. This might help when taking over a
legacy database for example.

.. warning::

    One caveat on migrations - you won't be able to use a `default` properly at
    sizes other than ``LONGTEXT``/``LONGBLOB`` until Django 1.9 which includes
    a fix from `Django Ticket 24846
    <https://code.djangoproject.com/ticket/24846>`_. This is anyway mostly due
    to a MySQL limitation - ``DEFAULT`` cannot be specified, other than the
    empty string, for ``TEXT`` and ``BLOB`` columns.

Docs:
`MySQL <https://dev.mysql.com/doc/refman/5.5/en/storage-requirements.html>`_ /
`MariaDB <https://mariadb.com/kb/en/mariadb/data-type-storage-requirements/>`_.


.. class:: SizedTextField(size_class, **kwargs)

    A subclass of Django's :class:`~django.db.models.TextField` that allows you
    to use the other sizes of ``TEXT`` data type. Set ``size_class`` to:

        * ``1`` for a ``TINYTEXT`` field, which has a maximum length of 255
          bytes
        * ``2`` for a ``TEXT`` field, which has a maximum length of 65,535
          bytes
        * ``3`` for a ``MEDIUMTEXT`` field, which has a maximum length of
          16,777,215 bytes (16MiB)
        * ``4`` for a ``LONGTEXT`` field, which has a maximum length of
          4,294,967,295 bytes (4GiB)


.. class:: SizedBinaryField(size_class, **kwargs)

    A subclass of Django's :class:`~django.db.models.BinaryField` that allows
    you to use the other sizes of ``BLOB`` data type. Set ``size_class`` to:

        * ``1`` for a ``TINYBLOB`` field, which has a maximum length of 255
          bytes
        * ``2`` for a ``BLOB`` field, which has a maximum length of 65,535
          bytes
        * ``3`` for a ``MEDIUMBLOB`` field, which has a maximum length of
          16,777,215 bytes (16MiB)
        * ``4`` for a ``LONGBLOB`` field, which has a maximum length of
          4,294,967,295 bytes (4GiB)
