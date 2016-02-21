.. _bit1booleanfields:

---------------------
BIT(1) Boolean Fields
---------------------

Some database systems, such as the Java Hibernate ORM, don't use MySQL's
``bool`` data type for storing boolean flags and instead use ``BIT(1)``.
Django's default ``BooleanField`` and ``NullBooleanField`` classes can't work
with this.

The following subclasses are boolean fields that work with ``BIT(1)`` columns
that will help when connecting to a legacy database. If you are using
``inspectdb`` to generate models from the database, use these to replace the
``TextField`` output for your ``BIT(1)`` columns.


.. class:: Bit1BooleanField()

    A subclass of Django's :class:`~django.db.models.BooleanField` that uses
    the ``BIT(1)`` column type instead of ``bool``.


.. class:: NullBit1BooleanField()

    A subclass of Django's :class:`~django.db.models.NullBooleanField` that
    uses the ``BIT(1)`` column type instead of ``bool``.
