.. _fixedchar-field:

--------------
FixedCharField
--------------

.. currentmodule:: django_mysql.models

Django’s ``CharField`` uses the ``VARCHAR`` data type, which uses variable
storage space depending on string length. This normally saves storage space,
but for columns with a fixed length, it adds a small overhead.

The alternative ``CHAR`` data type avoids that overhead, but it has the
surprising behaviour of removing trailing space characters, and consequently
ignoring them in comparisons. ``FixedCharField`` provides a Django field for
using ``CHAR``. This can help you interface with databases created by other
systems, but it’s not recommended for general use, due to the trialing space
behaviour.

Docs:
`MySQL <https://dev.mysql.com/doc/refman/en/char.html>`_ /
`MariaDB <https://mariadb.com/docs/server/reference/data-types/string-data-types/char>`_.

.. class:: FixedCharField(*args, max_length: int, **kwargs)

    A subclass of Django's :class:`~django.db.models.Charfield` that uses the
    ``CHAR`` data type. ``max_length`` is as with ``CharField``, but must be
    within the range 0-255.

    For example:

    .. code-block:: python

        from django_mysql.models import FixedCharField


        class Address(Model):
            zip_code = FixedCharField(length=5)
