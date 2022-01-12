.. fixedchar-field:

---------
FixedCharField
---------

.. currentmodule:: django_mysql.models

Using a ``CharField`` for fixed-width strings leads to variable data
storage since the storage amount can changed depending on the length
of the string, whereas a fixed-width string will always use the same
amount of storage, regardless of the string value. Fixed value columns
can also decrease the storage size overall due to how the engine
indexes strings. MySQL's ``CHAR`` type allows a more compact representation
of such columns. ``FixedCharField`` allows you to use the ``CHAR`` type
with Django.


Docs:
`MySQL <https://dev.mysql.com/doc/refman/en/char.html>`_ /
`MariaDB <https://mariadb.com/kb/en/char/>`_.


.. class:: FixedCharField(length: int = 1, **kwargs)

    A subclass of Django's :class:`~django.db.models.Charfield` that uses a
    MySQL ``CHAR`` for storage.

    ``length`` is a non-standard Django argument for a field class, however it
    is required for ``FixedCharField``. It must be an integer value within the
    range of 0-255. Supplying values outside that range will throw a ValueError.
    For example:

    .. code-block:: python

        from django_mysql.models import FixedWidthField


        class VariousCharLengths(Model):
            zip_code = FixedCharField(length=5)
            default_length = FixedCharField()  # defaults to length=1
            really_long_string = FixedCharField(length=256)  # raise ValueError

    .. note::

        MariaDB defaults to a ``CHAR(1)`` field, while MySQL has no default value.
        ``FixedCharField`` follows the MariaDB behavior and defaults to a
        ``CHAR(1)`` field if a length is not provided.
