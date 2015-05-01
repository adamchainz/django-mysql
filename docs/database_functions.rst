.. _database_functions:

==================
Database Functions
==================

.. currentmodule:: django_mysql.models.functions

MySQL-specific `database functions
<https://docs.djangoproject.com/en/1.8/ref/models/database-functions/>`_
for the ORM.

The following can be imported from ``django_mysql.models.functions``.

.. note::

    Functions were only added to Django in version 1.8.


Comparison Functions
--------------------


.. class:: Greatest(*expressions)

    With two or more arguments, returns the largest (maximum-valued) argument.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/comparison-operators.html#function_greatest>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/greatest/>`_.

    Usage example::

        >>> Author.objects.filter(sales_eu=Greatest('sales_eu', 'sales_us'))


.. class:: Least(*expressions)

    With two or more arguments, returns the smallest (minimum-valued) argument.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/comparison-operators.html#function_least>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/least/>`_.

    Usage example::

        >>> Author.objects.filter(sales_eu=Least('sales_eu', 'sales_us'))


Numeric Functions
-----------------


.. class:: Abs(expression)

    Returns the absolute (non-negative) value of ``expression```. If
    ``expression`` is not a number, it is converted to a numeric type.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/mathematical-functions.html#function_abs>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/abs/>`_.

    Usage example::

        >>> Author.objects.annotate(abs_wealth=Abs('dollars'))


.. class:: Ceiling(expression)

    Returns the smallest integer value not less than `expression`.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/mathematical-functions.html#function_ceiling>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/ceiling/>`_.

    Usage example::

        >>> Author.objects.annotate(years_ceiling=Ceiling('age'))


.. class:: CRC32(expression)

    Computes a cyclic redundancy check value and returns a 32-bit unsigned
    value. The result is ``NULL`` if the argument is ``NULL``. The argument is
    expected to be a string and (if possible) is treated as one if it is not.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/mathematical-functions.html#function_crc32>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/crc32/>`_.

    Usage example::

        >>> Author.objects.annotate(description_crc=CRC32('description'))


.. class:: Floor(expression)

    Returns the largest integer value not greater than ``expression``.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/mathematical-functions.html#function_floor>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/floor/>`_.

    Usage example::

        >> Author.objects.annotate(age_years=Floor('age'))


.. class:: Round(expression, places=0)

    Rounds the argument ``expression`` to ``places`` decimal places. The
    rounding algorithm depends on the data type of ``expression``. ``places``
    defaults to 0 if not specified. ``places`` can be negative to cause
    ``places`` digits left of the decimal point of the value ``expression`` to
    become zero.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/mathematical-functions.html#function_round>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/round/>`_.

    Usage example::

        >>> Author.objects.annotate(kilo_sales=Round('sales', -3))


.. class:: Sign(expression)

    Returns the sign of the argument as -1, 0, or 1, depending on whether
    ``expression`` is negative, zero, or positive.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/mathematical-functions.html#function_sign>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/sign/>`_.

    Usage example::

        >>> Author.objects.annotate(wealth_sign=Sign('wealth'))


String Functions
----------------


.. class:: ConcatWS(*expressions, separator=',')

    ``ConcatWS`` stands for Concatenate With Separator and is a special form of
    :class:`~django.db.models.functions.Concat` (included in Django). It
    concatenates all of its argument expressions as strings with the given
    ``separator``. Since ``NULL`` values are skipped, unlike in ``Concat``, you
    can use the empty string as a separator and it acts as a ``NULL``-safe
    version of ``Concat``.

    If ``separator`` is a string, it will be turned into a
    :class:`~django.db.models.Value`. If you wish to join with the value of a
    field, you can pass in an :class:`~django.db.models.F` object for that
    field.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/string-functions.html#function_concat-ws>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/concat_ws/>`_.

    Usage example::

        >>> Author.objects.annotate(sales_list=ConcatWS('sales_eu', 'sales_us'))

.. class:: ELT(number, values)

    Given a numerical expression ``number``, it returns the ``number``th
    element from ``values``, 1-indexed. If ``number`` is less than 1 or greater
    than the number of expressions, it will return ``None``. It is the
    complement of ``Field``.

    Note that if ``number`` is a string, it will refer to a field, whereas
    members of ``values`` that are strings will be wrapped with ``Value``
    automatically and thus interpreted as the given string. This is for
    convenience with the most common usage pattern where you have the list pre-
    loaded in python, e.g. a ``choices`` field. If you want to refer to a
    column, use Django's ``F()`` class.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/string-functions.html#function_elt>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/elt/>`_.

    Usage example::

        >>> # Say Person.life_state is either 1 (alive), 2 (dead), or 3 (M.I.A.)
        >>> Person.objects.annotate(
        ...     state_name=ELT('life_state', ['Alive', 'Dead', 'M.I.A.'])
        ... )

.. class:: Field(expression, values)

    Given an ``expression`` and a list of strings ``values``, returns the
    1-indexed location of the ``expression``'s value in ``values``, or 0 if not
    found. This is commonly used with ``order_by`` to keep groups of elements
    together. It is the complement of ``ELT``.

    Note that if ``expression`` is a string, it will refer to a field, whereas
    if any member of ``values`` is a string, it will automatically be wrapped
    with ``Value`` and refer to the given string. This is for convenience with
    the most common usage pattern where you have the list of things pre-loaded
    in Python, e.g. in a field's ``choices``. If you want to refer to a column,
    use Django's ``F()`` class.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/string-functions.html#function_field>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/field/>`_.

    Usage example::

        >>> # Females, then males - but other values of gender (e.g. empty string) first
        >>> Person.objects.all().order_by(
        ...     Field('gender', ['Female', 'Male'])
        ... )


Encryption Functions
--------------------


.. class:: MD5(expression)

    Calculates an MD5 128-bit checksum for the string ``expression``.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/encryption-functions.html#function_md5>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/md5/>`_.

    Usage example::

        >>> Author.objects.annotate(description_md5=MD5('description'))


.. class:: SHA1(expression)

    Calculates an SHA-1 160-bit checksum for the string ``expression``, as
    described in RFC 3174 (Secure Hash Algorithm).

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/encryption-functions.html#function_sha1>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/sha1/>`_.

    Usage example::

        >>> Author.objects.annotate(description_sha=SHA1('description'))


.. class:: SHA2(expression, hash_len=512)

    Given a string ``expression``, calculates a SHA-2 checksum, which is
    considered more cryptographically secure than its SHA-1 equivalent. The
    SHA-2 family includes SHA-224, SHA-256, SHA-384, and SHA-512, and the
    ``hash_len`` must correspond to one of these, i.e. 224, 256, 384 or 512.
    The default for ``hash_len`` is 512.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/encryption-functions.html#function_sha2>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/sha2/>`_.

    Usage example::

        >>> Author.objects.annotate(description_sha256=SHA2('description', 256))
