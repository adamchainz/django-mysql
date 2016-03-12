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

    .. note::

        Django core has included this since Django 1.9 as
        :class:`django.db.models.functions.Greatest`; it's preferable to use
        that instead.

    With two or more arguments, returns the largest (maximum-valued) argument.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/comparison-operators.html#function_greatest>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/greatest/>`_.

    Usage example:

    .. code-block:: pycon

        >>> Author.objects.filter(sales_eu=Greatest('sales_eu', 'sales_us'))


.. class:: Least(*expressions)

    .. note::

        Django core has included this since Django 1.9 as
        :class:`django.db.models.functions.Least`; it's preferable to use
        that instead.

    With two or more arguments, returns the smallest (minimum-valued) argument.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/comparison-operators.html#function_least>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/least/>`_.

    Usage example:

    .. code-block:: pycon

        >>> Author.objects.filter(sales_eu=Least('sales_eu', 'sales_us'))


Control Flow Functions
--------------------


.. class:: If(condition, true, false=None)

    Evaluates the expression ``condition`` and returns the value of the
    expression ``true`` if true, and the result of expression ``false`` if
    false. If ``false`` is not given, it will be ``Value(None)``, i.e.
    ``NULL``.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/control-flow-functions.html#function_if>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/if-function/>`_.

    Usage example:

    .. code-block:: pycon

        >>> Author.objects.annotate(
        ...     is_william=If(Q(name__startswith='William '), True, False)
        ... ).values_list('name', 'is_william')
        [('William Shakespeare', True),
         ('Ian Fleming', False),
         ('William Wordsworth', True)]


Numeric Functions
-----------------


.. class:: Abs(expression)

    Returns the absolute (non-negative) value of ``expression```. If
    ``expression`` is not a number, it is converted to a numeric type.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/mathematical-functions.html#function_abs>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/abs/>`_.

    Usage example:

    .. code-block:: pycon

        >>> Author.objects.annotate(abs_wealth=Abs('dollars'))


.. class:: Ceiling(expression)

    Returns the smallest integer value not less than `expression`.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/mathematical-functions.html#function_ceiling>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/ceiling/>`_.

    Usage example:

    .. code-block:: pycon

        >>> Author.objects.annotate(years_ceiling=Ceiling('age'))


.. class:: CRC32(expression)

    Computes a cyclic redundancy check value and returns a 32-bit unsigned
    value. The result is ``NULL`` if the argument is ``NULL``. The argument is
    expected to be a string and (if possible) is treated as one if it is not.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/mathematical-functions.html#function_crc32>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/crc32/>`_.

    Usage example:

    .. code-block:: pycon

        >>> Author.objects.annotate(description_crc=CRC32('description'))


.. class:: Floor(expression)

    Returns the largest integer value not greater than ``expression``.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/mathematical-functions.html#function_floor>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/floor/>`_.

    Usage example:

    .. code-block:: pycon

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

    Usage example:

    .. code-block:: pycon

        >>> Author.objects.annotate(kilo_sales=Round('sales', -3))


.. class:: Sign(expression)

    Returns the sign of the argument as -1, 0, or 1, depending on whether
    ``expression`` is negative, zero, or positive.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/mathematical-functions.html#function_sign>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/sign/>`_.

    Usage example:

    .. code-block:: pycon

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

    Usage example:

    .. code-block:: pycon

        >>> Author.objects.annotate(sales_list=ConcatWS('sales_eu', 'sales_us'))

.. class:: ELT(number, values)

    Given a numerical expression ``number``, it returns the ``number``\th
    element from ``values``, 1-indexed. If ``number`` is less than 1 or greater
    than the number of expressions, it will return ``None``. It is the
    complement of the ``Field`` function.

    Note that if ``number`` is a string, it will refer to a field, whereas
    members of ``values`` that are strings will be wrapped with ``Value``
    automatically and thus interpreted as the given string. This is for
    convenience with the most common usage pattern where you have the list pre-
    loaded in python, e.g. a ``choices`` field. If you want to refer to a
    column, use Django's ``F()`` class.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/string-functions.html#function_elt>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/elt/>`_.

    Usage example:

    .. code-block:: pycon

        >>> # Say Person.life_state is either 1 (alive), 2 (dead), or 3 (M.I.A.)
        >>> Person.objects.annotate(
        ...     state_name=ELT('life_state', ['Alive', 'Dead', 'M.I.A.'])
        ... )

.. class:: Field(expression, values)

    Given an ``expression`` and a list of strings ``values``, returns the
    1-indexed location of the ``expression``'s value in ``values``, or 0 if not
    found. This is commonly used with ``order_by`` to keep groups of elements
    together. It is the complement of the ``ELT`` function.

    Note that if ``expression`` is a string, it will refer to a field, whereas
    if any member of ``values`` is a string, it will automatically be wrapped
    with ``Value`` and refer to the given string. This is for convenience with
    the most common usage pattern where you have the list of things pre-loaded
    in Python, e.g. in a field's ``choices``. If you want to refer to a column,
    use Django's ``F()`` class.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/string-functions.html#function_field>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/field/>`_.

    Usage example:

    .. code-block:: pycon

        >>> # Females, then males - but other values of gender (e.g. empty string) first
        >>> Person.objects.all().order_by(
        ...     Field('gender', ['Female', 'Male'])
        ... )


XML Functions
-------------

.. class:: UpdateXML(xml_target, xpath_expr, new_xml)

    Returns the XML fragment ``xml_target`` with the single match for
    ``xpath_expr`` replaced with the xml fragment ``new_xml``. If nothing
    matches ``xpath_expr``, or if multiple matches are found, the original
    ``xml_target`` is returned unchanged.

    This can be used for single-query updates of text fields containing XML.

    Note that if ``xml_target`` is given as a string, it will refer to a
    column, whilst if either ``xpath_expr`` or ``new_xml`` are strings, they
    will be used as strings directly. If you want ``xpath_expr`` or ``new_xml``
    to refer to columns, use Django's ``F()`` class.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/xml-functions.html#function_updatexml>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/updatexml/>`_.

    Usage example:

    .. code-block:: pycon

        # Remove 'sagacity' from all authors' xml_attrs
        >>> Author.objects.update(
        ...     xml_attrs=UpdateXML('xml_attrs', '/sagacity', '')
        ... )


.. class:: XMLExtractValue(xml_frag, xpath_expr)

    Returns the text (``CDATA``) of the first text node which is a child of the
    element(s) in the XML fragment ``xml_frag`` matched by the XPath expression
    ``xpath_expr``. In SQL this function is called ``ExtractValue``; the class
    has the ``XML`` prefix to make it clearer what kind of values are it
    extracts.

    Note that if ``xml_frag`` is given as a string, it will refer to a column,
    whilst if ``xpath_expr`` is a string, it will be used as a string. If you
    want ``xpath_expr`` to refer to a column, use Django's ``F()`` class.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/xml-functions.html#function_extractvalue>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/extractvalue/>`_.

    Usage example:

    .. code-block:: pycon

        # Count the number of authors with 'sagacity' in their xml_attrs
        >>> num_authors_with_sagacity = Author.objects.annotate(
        ...     has_sagacity=XMLExtractValue('xml_attrs', 'count(/sagacity)')
        ... ).filter(has_sagacity='1').count()


Regexp Functions
----------------

.. note::
    These work with MariaDB 10.0.5+ only, which includes PCRE regular
    expressions and these extra functions to use them. More information can be
    found in `its documentation
    <https://mariadb.com/kb/en/mariadb/regular-expressions-overview/>`_.


.. class:: RegexpInstr(expression, regex)

    Returns the 1-indexed position of the first occurrence of the regular
    expression ``regex`` in the string value of ``expression``, or 0 if it was
    not found.

    Note that if ``expression`` is given as a string, it will refer to a
    column, whilst if ``regex`` is a string, it will be used as a string. If
    you want ``regex`` to refer to a column, use Django's ``F()`` class.

    Docs: `MariaDB <https://mariadb.com/kb/en/mariadb/regexp_instr/>`_.

    Usage example:

    .. code-block:: pycon

        >>> Author.objects.annotate(name_pos=RegexpInstr('name', r'ens')) \
        ...               .filter(name_pos__gt=0)
        [<Author: Charles Dickens>, <Author: Robert Louis Stevenson>]


.. class:: RegexpReplace(expression, regex, replace)

    Returns the string value of ``expression`` with all occurrences of the
    regular expression ``regex`` replaced by the string ``replace``. If no
    occurrences are found, then subject is returned as is.

    Note that if ``expression`` is given as a string, it will refer to a
    column, whilst if either ``regex`` or ``replace`` are strings, they will be
    used as strings. If you want ``regex`` or ``replace`` to refer to columns,
    use Django's ``F()`` class.

    Docs: `MariaDB <https://mariadb.com/kb/en/mariadb/regexp_replace/>`_.

    Usage example:

    .. code-block:: pycon

        >>> Author.objects.create(name="Charles Dickens")
        >>> Author.objects.create(name="Roald Dahl")
        >>> qs = Author.objects.annotate(
        ...     surname_first=RegexpReplace('name', r'^(.*) (.*)$', r'\2, \1')
        ... ).order_by('surname_first')
        >>> qs
        [<Author: Roald Dahl>, <Author: Charles Dickens>]
        >>> qs[0].surname_first
        "Dahl, Roald"


.. class:: RegexpSubstr(expression, regex)

    Returns the part of the string value of ``expression`` that matches the
    regular expression ``regex``, or an empty string if ``regex`` was not
    found.

    Note that if ``expression`` is given as a string, it will refer to a
    column, whilst if ``regex`` is a string, it will be used as a string. If
    you want ``regex`` to refer to a column, use Django's ``F()`` class.

    Docs: `MariaDB <https://mariadb.com/kb/en/mariadb/regexp_substr/>`_.

    Usage example:

    .. code-block:: pycon

        >>> Author.objects.create(name="Euripides")
        >>> Author.objects.create(name="Frank Miller")
        >>> Author.objects.create(name="Sophocles")
        >>> Author.objects.annotate(
        ...     name_has_space=CharLength(RegexpSubstr('name', r'\s'))
        ... ).filter(name_has_space=0)
        [<Author: Euripides>, <Author: Sophocles>]

Encryption Functions
--------------------


.. class:: MD5(expression)

    Calculates an MD5 128-bit checksum for the string ``expression``.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/encryption-functions.html#function_md5>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/md5/>`_.

    Usage example:

    .. code-block:: pycon

        >>> Author.objects.annotate(description_md5=MD5('description'))


.. class:: SHA1(expression)

    Calculates an SHA-1 160-bit checksum for the string ``expression``, as
    described in RFC 3174 (Secure Hash Algorithm).

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/encryption-functions.html#function_sha1>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/sha1/>`_.

    Usage example:

    .. code-block:: pycon

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

    Usage example:

    .. code-block:: pycon

        >>> Author.objects.annotate(description_sha256=SHA2('description', 256))


Information Functions
---------------------

.. class:: LastInsertId(expression=None)

    With no argument, returns the last value added to an auto-increment column,
    or set by another call to ``LastInsertId`` with an argument. With an
    argument, sets the 'last insert id' value to the value of the given
    expression, and returns that value. This can be used to implement simple
    ``UPDATE ... RETURNING`` style queries.

    This function also has a class method:

    .. method:: get(using=DEFAULT_DB_ALIAS)

        Returns the value set by a call to ``LastInsertId()`` with an argument,
        by performing a single query. It is stored per-connection, hence you
        may need to pass the alias of the connection that set the
        ``LastInsertId`` as ``using``.

        .. note::

            Any queries on the database connection between setting
            ``LastInsertId`` and calling ``LastInsertId.get()`` can reset the
            value. These might come from Django, which can issue multiple
            queries for ``update()`` with multi-table inheritance, or for
            ``delete()`` with cascading.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/information-functions.html#function_last-insert-id>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/last_insert_id/>`_.

    Usage examples:

    .. code-block:: pycon

        >>> Countable.objects.filter(id=1).update(counter=LastInsertId('counter') + 1)
        1
        >>> # Get the pre-increase value of 'counter' as stored on the server
        >>> LastInsertId.get()
        242

        >>> Author.objects.filter(id=1, age=LastInsertId('age')).delete()
        1
        >>> # We can also use the stored value directly in a query
        >>> Author.objects.filter(id=2).update(age=LastInsertId())
        1
        >>> Author.objects.get(id=2).age
        35

.. _json-database-functions:

JSON Database Functions
-----------------------

These are for MySQL 5.7+ only, for use with JSON data stored in a
``CharField``, ``TextField``, or most importantly, a
:class:`~django_mysql.models.JSONField` (with which the functions are much
faster due to the JSON being stored in a binary representation).

These functions use JSON paths to address content inside JSON documents - for
more information on their syntax, refer to the MySQL documentation.


.. class:: JSONExtract(expression, *paths)

    Given ``expression`` that resolves to some JSON data, extract the given
    JSON paths. If there is a single path, the plain value is returned; if
    there is more than one path, the output is a JSON array with the list of
    values represented by the paths. If the expression does not match for a
    particular JSON object, returns ``NULL``.

    Note that if ``expression`` is a string, it will refer to a field, whereas
    members of ``paths`` that are strings will be wrapped with ``Value``
    automatically and thus interpreted as the given string. If you want any of
    ``paths`` to refer to a field, use Django's ``F()`` class.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.7/en/json-search-functions.html#function_json-extract>`_.

    Usage examples:

    .. code-block:: pycon

        >>> # Fetch a list of tuples (id, size_or_None) for all ShopItems
        >>> ShopItem.objects.annotate(
        ...     size=JSONExtract('attrs', '$.size')
        ... ).values_list('id', 'size')
        [(1, '3m'), (3, '5nm'), (8, None)]
        >>> # Fetch the distinct values of attrs['colours'][0] for all items
        >>> ShopItem.objects.annotate(
        ...     primary_colour=JSONExtract('attrs', '$.colours[0]')
        ... ).distinct().values_list('primary_colour', flat=True)
        ['Red', 'Blue', None]


.. class:: JSONKeys(expression, path=None)

    Given ``expression`` that resolves to some JSON data containing a JSON
    object, return the keys in that top-level object as a JSON array, or if
    ``path`` is given, return the keys at that path. If the path does not
    match, or if ``expression`` is not a JSON object (e.g. it contains a JSON
    array instead), returns ``NULL``.

    Note that if ``expression`` is a string, it will refer to a field, whereas
    if ``path`` is a string it will be wrapped with ``Value`` automatically and
    thus interpreted as the given string. If you want ``path`` to refer to a
    field, use Django's ``F()`` class.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.7/en/json-search-functions.html#function_json-keys>`_.

    .. code-block:: pycon

        >>> # Fetch the top-level keys for the first item
        >>> ShopItem.objects.annotate(
        ...     keys=JSONKeys('attrs')
        ... ).values_list('keys', flat=True)[0]
        ['size', 'colours', 'age', 'price', 'origin']
        >>> # Fetch the keys in 'origin' for the first item
        >>> ShopItem.objects.annotate(
        ...     keys=JSONKeys('attrs', '$.origin')
        ... ).values_list('keys', flat=True)[0]
        ['continent', 'country', 'town']


.. class:: JSONLength(expression, path=None)

    Given ``expression`` that resolves to some JSON data, return the length of
    that data, or if ``path`` is given, return the length of the data at that
    path. If the path does not match, or if ``expression`` is ``NULL`` it
    returns ``NULL``.

    As per the MySQL documentation, the length of a document is determined as
    follows:

    * The length of a scalar is 1.
    * The length of an array is the number of array elements.
    * The length of an object is the number of object members.
    * The length does not count the length of nested arrays or objects.

    Note that if ``expression`` is a string, it will refer to a field, whereas
    if ``path`` is a string it will be wrapped with ``Value`` automatically and
    thus interpreted as the given string. If you want ``path`` to refer to a
    field, use Django's ``F()`` class.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.7/en/json-attribute-functions.html#function_json-length>`_.

    .. code-block:: pycon

        >>> # Which ShopItems don't have more than three colours?
        >>> ShopItem.objects.annotate(
        ...     num_colours=JSONLength('attrs', '$.colours')
        ... ).filter(num_colours__gt=3)
        [<ShopItem: Rainbow Wheel>, <ShopItem: Hard Candies>]


Dynamic Columns Functions
-------------------------

These are MariaDB 10.0+ only, and for use with ``DynamicField``.


.. class:: AsType(expression, data_type)

    A partial function that should be used as part of a ``ColumnAdd``
    expression when you want to ensure that ``expression`` will be stored as
    a given type ``data_type``. The possible values for ``data_type`` are the
    same as documented for the ``DynamicField`` lookups.

    Note that this is not a valid standalone function and must be used as part
    of ``ColumnAdd`` - see below.

.. class:: ColumnAdd(expression, to_add)

    Given ``expression`` that resolves to a ``DynamicField`` (most often a
    field name), add/update with the dictionary ``to_add`` and return the new
    Dynamic Columns value. This can be used for atomic single-query updates on
    Dynamic Columns.

    Note that you can add optional types (and you should!). These can not be
    drawn from the ``spec`` of the ``DynamicField`` due to ORM restrictions, so
    there are no guarantees about the types that will get used if you do not.
    To add a type cast, wrap the value with an ``AsType`` (above) - see
    examples below.

    Docs:
    `MariaDB <https://mariadb.com/kb/en/mariadb/column_add/>`_.

    Usage examples:

    .. code-block:: pycon

        >>> # Add default 'for_sale' as INTEGER 1 to every item
        >>> ShopItem.objects.update(
        ...     attrs=ColumnAdd('attrs', {'for_sale': AsType(1, 'INTEGER')})
        ... )
        >>> # Fix some data
        >>> ShopItem.objects.filter(attrs__size='L').update(
        ...     attrs=ColumnAdd('attrs', {'size': AsType('Large', 'CHAR')})
        ... )


.. class:: ColumnDelete(expression, *to_delete)

    Given ``expression`` that resolves to a ``DynamicField`` (most often a
    field name), delete the columns listed by the other expressions
    ``to_delete``, and return the new Dynamic Columns value. This can be used
    for atomic single-query deletions on Dynamic Columns.

    Note that strings in ``to_delete`` will be wrapped with ``Value``
    automatically and thus interpreted as the given string - if they weren't,
    Django would interpret them as meaning "the value in this (non-dynamic)
    column". If you do mean that, use ``F('fieldname')``.

    Docs:
    `MariaDB <https://mariadb.com/kb/en/mariadb/column_delete/>`_.

    Usage examples:

    .. code-block:: pycon

        >>> # Remove 'for_sail' and 'for_purchase' from every item
        >>> ShopItem.objects.update(
        ...     attrs=ColumnDelete('attrs', 'for_sail', 'for_purchase')
        ... )


.. class:: ColumnGet(expression, name, data_type)

    Given ``expression`` that resolves to a ``DynamicField`` (most often a
    field name), return the value of the column ``name`` when cast to the type
    ``data_type``, or ``NULL`` / ``None`` if the column does not exist. This
    can be used to select a subset of column values when you don't want to
    fetch the whole blob. The possible values for ``data_type`` are the same as
    documented for the ``DynamicField`` lookups.

    Docs:
    `MariaDB <https://mariadb.com/kb/en/mariadb/column_get/>`_.

    Usage examples:

    .. code-block:: pycon

        >>> # Fetch a list of tuples (id, size_or_None) for all items
        >>> ShopItem.objects.annotate(
        ...     size=ColumnGet('attrs', 'size', 'CHAR')
        ... ).values_list('id', 'size')
        >>> # Fetch the distinct values of attrs['seller']['url'] for all items
        >>> ShopItem.objects.annotate(
        ...     seller_url=ColumnGet(ColumnGet('attrs', 'seller', 'BINARY'), 'url', 'CHAR')
        ... ).distinct().values_list('seller_url', flat=True)
