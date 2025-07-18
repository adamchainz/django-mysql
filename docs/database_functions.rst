.. _database_functions:

==================
Database Functions
==================

.. currentmodule:: django_mysql.models.functions

MySQL/MariaDB-specific `database functions
<https://docs.djangoproject.com/en/3.0/ref/models/database-functions/>`_
for the ORM.

The following can be imported from ``django_mysql.models.functions``.

Control Flow Functions
----------------------


.. class:: If(condition, true, false=None)

    Evaluates the expression ``condition`` and returns the value of the
    expression ``true`` if true, and the result of expression ``false`` if
    false. If ``false`` is not given, it will be ``Value(None)``, i.e.
    ``NULL``.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/en/control-flow-functions.html#function_if>`__ /
    `MariaDB <https://mariadb.com/docs/server/reference/sql-functions/control-flow-functions/if-function>`__.

    Usage example:

    .. code-block:: pycon

        >>> Author.objects.annotate(
        ...     is_william=If(Q(name__startswith="William "), True, False)
        ... ).values_list("name", "is_william")
        [('William Shakespeare', True),
         ('Ian Fleming', False),
         ('William Wordsworth', True)]


Numeric Functions
-----------------

.. class:: CRC32(expression)

    Computes a cyclic redundancy check value and returns a 32-bit unsigned
    value. The result is ``NULL`` if the argument is ``NULL``. The argument is
    expected to be a string and (if possible) is treated as one if it is not.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/en/mathematical-functions.html#function_crc32>`__ /
    `MariaDB <https://mariadb.com/docs/server/reference/sql-functions/numeric-functions/crc32>`__.

    Usage example:

    .. code-block:: pycon

        >>> Author.objects.annotate(description_crc=CRC32("description"))

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
    `MySQL <https://dev.mysql.com/doc/refman/en/string-functions.html#function_concat-ws>`__ /
    `MariaDB <https://mariadb.com/docs/server/reference/sql-functions/string-functions/concat_ws>`__.

    Usage example:

    .. code-block:: pycon

        >>> Author.objects.annotate(sales_list=ConcatWS("sales_eu", "sales_us"))

.. class:: ELT(number, values)

    Given a numerical expression ``number``, it returns the ``number``\th
    element from ``values``, 1-indexed. If ``number`` is less than 1 or greater
    than the number of expressions, it will return ``None``. It is the
    complement of the ``Field`` function.

    Note that if ``number`` is a string, it will refer to a field, whereas
    members of ``values`` that are strings will be wrapped with ``Value``
    automatically and thus interpreted as the given string. This is for
    convenience with the most common usage pattern where you have the list
    pre-loaded in python, e.g. a ``choices`` field. If you want to refer to a
    column, use Django's ``F()`` class.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/en/string-functions.html#function_elt>`__ /
    `MariaDB <https://mariadb.com/docs/server/reference/sql-functions/string-functions/elt>`__.

    Usage example:

    .. code-block:: pycon

        >>> # Say Person.life_state is either 1 (alive), 2 (dead), or 3 (M.I.A.)
        >>> Person.objects.annotate(state_name=ELT("life_state", ["Alive", "Dead", "M.I.A."]))

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
    `MySQL <https://dev.mysql.com/doc/refman/en/string-functions.html#function_field>`__ /
    `MariaDB <https://mariadb.com/docs/server/reference/sql-functions/string-functions/field>`__.

    Usage example:

    .. code-block:: pycon

        >>> # Females, then males - but other values of gender (e.g. empty string) first
        >>> Person.objects.all().order_by(Field("gender", ["Female", "Male"]))


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
    `MySQL <https://dev.mysql.com/doc/refman/en/xml-functions.html#function_updatexml>`__ /
    `MariaDB <https://mariadb.com/docs/server/reference/sql-functions/string-functions/updatexml>`__.

    Usage example:

    .. code-block:: pycon

        # Remove 'sagacity' from all authors' xml_attrs
        >>> Author.objects.update(xml_attrs=UpdateXML("xml_attrs", "/sagacity", ""))


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
    `MySQL <https://dev.mysql.com/doc/refman/en/xml-functions.html#function_extractvalue>`__ /
    `MariaDB <https://mariadb.com/docs/server/reference/sql-functions/string-functions/extractvalue>`__.

    Usage example:

    .. code-block:: pycon

        # Count the number of authors with 'sagacity' in their xml_attrs
        >>> num_authors_with_sagacity = (
        ...     Author.objects.annotate(
        ...         has_sagacity=XMLExtractValue("xml_attrs", "count(/sagacity)")
        ...     )
        ...     .filter(has_sagacity="1")
        ...     .count()
        ... )


Regexp Functions
----------------

.. note::
    These work with MariaDB 10.0.5+ only, which includes PCRE regular
    expressions and these extra functions to use them. More information can be
    found in `its documentation
    <https://mariadb.com/docs/server/reference/sql-functions/string-functions/regular-expressions-functions/regular-expressions-overview>`_.


.. class:: RegexpInstr(expression, regex)

    Returns the 1-indexed position of the first occurrence of the regular
    expression ``regex`` in the string value of ``expression``, or 0 if it was
    not found.

    Note that if ``expression`` is given as a string, it will refer to a
    column, whilst if ``regex`` is a string, it will be used as a string. If
    you want ``regex`` to refer to a column, use Django's ``F()`` class.

    Docs: `MariaDB <https://mariadb.com/docs/server/reference/sql-functions/string-functions/regular-expressions-functions/regexp_instr>`__.

    Usage example:

    .. code-block:: pycon

        >>> Author.objects.annotate(name_pos=RegexpInstr("name", r"ens")).filter(name_pos__gt=0)
        [<Author: Charles Dickens>, <Author: Robert Louis Stevenson>]


.. class:: RegexpReplace(expression, regex, replace)

    Returns the string value of ``expression`` with all occurrences of the
    regular expression ``regex`` replaced by the string ``replace``. If no
    occurrences are found, then subject is returned as is.

    Note that if ``expression`` is given as a string, it will refer to a
    column, whilst if either ``regex`` or ``replace`` are strings, they will be
    used as strings. If you want ``regex`` or ``replace`` to refer to columns,
    use Django's ``F()`` class.

    Docs: `MariaDB <https://mariadb.com/docs/server/reference/sql-functions/string-functions/regular-expressions-functions/regexp_replace>`__.

    Usage example:

    .. code-block:: pycon

        >>> Author.objects.create(name="Charles Dickens")
        >>> Author.objects.create(name="Roald Dahl")
        >>> qs = Author.objects.annotate(
        ...     surname_first=RegexpReplace("name", r"^(.*) (.*)$", r"\2, \1")
        ... ).order_by("surname_first")
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

    Docs: `MariaDB <https://mariadb.com/docs/server/reference/sql-functions/string-functions/regular-expressions-functions/regexp_substr>`__.

    Usage example:

    .. code-block:: pycon

        >>> Author.objects.create(name="Euripides")
        >>> Author.objects.create(name="Frank Miller")
        >>> Author.objects.create(name="Sophocles")
        >>> Author.objects.annotate(name_has_space=CharLength(RegexpSubstr("name", r"\s"))).filter(
        ...     name_has_space=0
        ... )
        [<Author: Euripides>, <Author: Sophocles>]

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
    `MySQL <https://dev.mysql.com/doc/refman/en/information-functions.html#function_last-insert-id>`__ /
    `MariaDB <https://mariadb.com/docs/server/reference/sql-functions/secondary-functions/information-functions/last_insert_id>`__.

    Usage examples:

    .. code-block:: pycon

        >>> Countable.objects.filter(id=1).update(counter=LastInsertId("counter") + 1)
        1
        >>> # Get the pre-increase value of 'counter' as stored on the server
        >>> LastInsertId.get()
        242

        >>> Author.objects.filter(id=1, age=LastInsertId("age")).delete()
        1
        >>> # We can also use the stored value directly in a query
        >>> Author.objects.filter(id=2).update(age=LastInsertId())
        1
        >>> Author.objects.get(id=2).age
        35

.. _json-database-functions:

JSON Database Functions
-----------------------

These functions work with data stored in Django’s ``JSONField`` on MySQL and
MariaDB only. ``JSONField`` is built in to Django 3.1+ and can be installed on
older Django versions with the
`django-jsonfield-backport <https://pypi.org/project/django-jsonfield-backport/>`__
package.

These functions use JSON paths to address content inside JSON documents - for
more information on their syntax, refer to the docs:
`MySQL <https://dev.mysql.com/doc/refman/8.0/en/json.html#json-path-syntax>`__ /
`MariaDB <https://mariadb.com/docs/server/reference/sql-functions/special-functions/json-functions/jsonpath-expressions>`__.


.. class:: JSONExtract(expression, *paths, output_field=None)

    Given ``expression`` that resolves to some JSON data, extract the given
    JSON paths. If there is a single path, the plain value is returned; if
    there is more than one path, the output is a JSON array with the list of
    values represented by the paths. If the expression does not match for a
    particular JSON object, returns ``NULL``.

    If only one path is given, ``output_field`` may also be given as a model
    field instance like ``IntegerField()``, into which Django will load the
    value; the default is ``JSONField()``, as it supports all return types
    including the array of values for multiple paths.

    Note that if ``expression`` is a string, it will refer to a field, whereas
    members of ``paths`` that are strings will be wrapped with ``Value``
    automatically and thus interpreted as the given string. If you want any of
    ``paths`` to refer to a field, use Django's ``F()`` class.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/8.0/en/json-search-functions.html#function_json-extract>`__ /
    `MariaDB <https://mariadb.com/docs/server/reference/sql-functions/special-functions/json-functions/json_extract>`__.

    Usage examples:

    .. code-block:: pycon

        >>> # Fetch a list of tuples (id, size_or_None) for all ShopItems
        >>> ShopItem.objects.annotate(size=JSONExtract("attrs", "$.size")).values_list("id", "size")
        [(1, '3m'), (3, '5nm'), (8, None)]
        >>> # Fetch the distinct values of attrs['colours'][0] for all items
        >>> ShopItem.objects.annotate(
        ...     primary_colour=JSONExtract("attrs", "$.colours[0]")
        ... ).distinct().values_list("primary_colour", flat=True)
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
    `MySQL <https://dev.mysql.com/doc/refman/8.0/en/json-search-functions.html#function_json-keys>`__ /
    `MariaDB <https://mariadb.com/docs/server/reference/sql-functions/special-functions/json-functions/json_keys>`__.

    .. code-block:: pycon

        >>> # Fetch the top-level keys for the first item
        >>> ShopItem.objects.annotate(keys=JSONKeys("attrs")).values_list("keys", flat=True)[0]
        ['size', 'colours', 'age', 'price', 'origin']
        >>> # Fetch the keys in 'origin' for the first item
        >>> ShopItem.objects.annotate(keys=JSONKeys("attrs", "$.origin")).values_list(
        ...     "keys", flat=True
        ... )[0]
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
    `MySQL <https://dev.mysql.com/doc/refman/8.0/en/json-attribute-functions.html#function_json-length>`__ /
    `MariaDB <https://mariadb.com/docs/server/reference/sql-functions/special-functions/json-functions/json_length>`__.

    .. code-block:: pycon

        >>> # Which ShopItems don't have more than three colours?
        >>> ShopItem.objects.annotate(num_colours=JSONLength("attrs", "$.colours")).filter(
        ...     num_colours__gt=3
        ... )
        [<ShopItem: Rainbow Wheel>, <ShopItem: Hard Candies>]


.. class:: JSONInsert(expression, data)

    Given ``expression`` that resolves to some JSON data, adds to it using the
    dictionary ``data`` of JSON paths to new values. If any JSON path in the
    ``data`` dictionary does not match, or if ``expression`` is ``NULL``, it
    returns ``NULL``. Paths that already exist in the original data are
    ignored.

    Note that if ``expression`` is a string, it will refer to a field, whereas
    keys and values within the ``pairs`` dictionary will be wrapped with
    ``Value`` automatically and thus interpreted as the given string. If you
    want a key or value to refer to a field, use Django's ``F()`` class.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/8.0/en/json-modification-functions.html#function_json-insert>`__ /
    `MariaDB <https://mariadb.com/docs/server/reference/sql-functions/special-functions/json-functions/json_insert>`__.

    .. code-block:: pycon

        >>> # Add power_level = 0 for those items that don't have power_level
        >>> ShopItem.objects.update(attrs=JSONInsert("attrs", {"$.power_level": 0}))


.. class:: JSONReplace(expression, data)

    Given ``expression`` that resolves to some JSON data, replaces existing
    paths in it using the dictionary ``data`` of JSON paths to new values. If
    any JSON path within the ``data`` dictionary does not match, or if
    ``expression`` is ``NULL``, it returns ``NULL``. Paths that do not exist in
    the original data are ignored.

    Note that if ``expression`` is a string, it will refer to a field, whereas
    keys and values within the ``pairs`` dictionary will be wrapped with
    ``Value`` automatically and thus interpreted as the given string. If you
    want a key or value to refer to a field, use Django's ``F()`` class.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/8.0/en/json-modification-functions.html#function_json-replace>`__ /
    `MariaDB <https://mariadb.com/docs/server/reference/sql-functions/special-functions/json-functions/json_replace>`__.

    .. code-block:: pycon

        >>> # Reset all items' monthly_sales to 0 directly in MySQL
        >>> ShopItem.objects.update(attrs=JSONReplace("attrs", {"$.monthly_sales": 0}))


.. class:: JSONSet(expression, data)

    Given ``expression`` that resolves to some JSON data, updates it using the
    dictionary ``data`` of JSON paths to new values. If any of the JSON paths
    within the data dictionary does not match, or if ``expression`` is
    ``NULL``, it returns ``NULL``. All paths can be modified - those that did
    not exist before and those that did.

    Note that if ``expression`` is a string, it will refer to a field, whereas
    keys and values within the ``data`` dictionary will be wrapped with
    ``Value`` automatically and thus interpreted as the given string. If you
    want a key or value to refer to a field, use Django's ``F()`` class.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/8.0/en/json-modification-functions.html#function_json-set>`__ /
    `MariaDB <https://mariadb.com/docs/server/reference/sql-functions/special-functions/json-functions/json_set>`__.

    .. code-block:: pycon

        >>> # Modify 'size' value to '10m' directly in MySQL
        >>> shop_item = ShopItem.objects.latest()
        >>> shop_item.attrs = JSONSet("attrs", {"$.size": "10m"})
        >>> shop_item.save()


.. class:: JSONArrayAppend(expression, data)

    Given ``expression`` that resolves to some JSON data, adds to it using the
    dictionary ``data`` of JSON paths to new values. If a path selects an
    array, the new value will be appended to it. On the other hand, if a path
    selects a scalar or object value, that value is autowrapped within an array
    and the new value is added to that array. If any of the JSON paths within
    the data dictionary does not match, or if ``expression`` is ``NULL``, it
    returns ``NULL``.

    Note that if ``expression`` is a string, it will refer to a field, whereas
    keys and values within the ``data`` dictionary will be wrapped with
    ``Value`` automatically and thus interpreted as the given string. If you
    want a key or value to refer to a field, use Django's ``F()`` class.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/8.0/en/json-modification-functions.html#function_json-array-append>`__ /
    `MariaDB <https://mariadb.com/docs/server/reference/sql-functions/special-functions/json-functions/json_array_append>`__.

    .. code-block:: pycon

        >>> # Append the string '10m' to the array 'sizes' directly in MySQL
        >>> shop_item = ShopItem.objects.latest()
        >>> shop_item.attrs = JSONArrayAppend("attrs", {"$.sizes": "10m"})
        >>> shop_item.save()


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
    `MariaDB <https://mariadb.com/docs/server/reference/sql-functions/special-functions/dynamic-columns-functions/column_add>`__.

    Usage examples:

    .. code-block:: pycon

        >>> # Add default 'for_sale' as INTEGER 1 to every item
        >>> ShopItem.objects.update(attrs=ColumnAdd("attrs", {"for_sale": AsType(1, "INTEGER")}))
        >>> # Fix some data
        >>> ShopItem.objects.filter(attrs__size="L").update(
        ...     attrs=ColumnAdd("attrs", {"size": AsType("Large", "CHAR")})
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
    `MariaDB <https://mariadb.com/docs/server/reference/sql-functions/special-functions/dynamic-columns-functions/column_delete>`__.

    Usage examples:

    .. code-block:: pycon

        >>> # Remove 'for_sail' and 'for_purchase' from every item
        >>> ShopItem.objects.update(attrs=ColumnDelete("attrs", "for_sail", "for_purchase"))


.. class:: ColumnGet(expression, name, data_type)

    Given ``expression`` that resolves to a ``DynamicField`` (most often a
    field name), return the value of the column ``name`` when cast to the type
    ``data_type``, or ``NULL`` / ``None`` if the column does not exist. This
    can be used to select a subset of column values when you don't want to
    fetch the whole blob. The possible values for ``data_type`` are the same as
    documented for the ``DynamicField`` lookups.

    Docs:
    `MariaDB <https://mariadb.com/docs/server/reference/sql-functions/special-functions/dynamic-columns-functions/column_get>`__.

    Usage examples:

    .. code-block:: pycon

        >>> # Fetch a list of tuples (id, size_or_None) for all items
        >>> ShopItem.objects.annotate(size=ColumnGet("attrs", "size", "CHAR")).values_list(
        ...     "id", "size"
        ... )
        >>> # Fetch the distinct values of attrs['seller']['url'] for all items
        >>> ShopItem.objects.annotate(
        ...     seller_url=ColumnGet(ColumnGet("attrs", "seller", "BINARY"), "url", "CHAR")
        ... ).distinct().values_list("seller_url", flat=True)
