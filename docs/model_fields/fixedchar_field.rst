.. fixedchar-field:

--------------
FixedCharField
--------------

.. currentmodule:: django_mysql.models

Django’s ``CharField`` uses the ``VARCHAR`` data type, which uses variable
storage space depending on string length. This normally saves storage space,
but for columns with a fixed length, it adds a small overhead.
``FixedCharField`` uses the ``CHAR`` data type, which avoids that overhead.
It only accepts strings with the given length, and uses a corresponding fixed
amount of storage.

Docs:
`MySQL <https://dev.mysql.com/doc/refman/en/char.html>`_ /
`MariaDB <https://mariadb.com/kb/en/char/>`_.

.. class:: FixedCharField(length: int, **kwargs)

    A subclass of Django's :class:`~django.db.models.Charfield` that uses a
    MySQL ``CHAR`` for storage.

    ``length`` is a non-standard Django argument for a field class, however it
    is required for ``FixedCharField``. It must be an integer value within the
    range of 0-255. Supplying values outside that range will throw a ValueError.
    For example:

    .. code-block:: python

        from django_mysql.models import FixedCharField


        class Address(Model):
            zip_code = FixedCharField(length=5)
