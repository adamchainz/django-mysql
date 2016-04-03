.. _dynamic-columns-field:

------------
DynamicField
------------

.. currentmodule:: django_mysql.models

**MariaDB** has a feature called **Dynamic Columns** that allows you to store
different sets of columns for each row in a table. It works by storing the data
in a blob and having a small set of functions to manipulate this blob.
(`Docs <https://mariadb.com/kb/en/mariadb/dynamic-columns/>`_).

Django-MySQL supports the *named* Dynamic Columns of MariaDB 10.0+, as opposed
to the *numbered* format of 5.5+. It uses the
`mariadb-dyncol <https://pypi.python.org/pypi/mariadb-dyncol>`_ python package
to pack and unpack Dynamic Columns blobs in Python rather than in MariaDB
(mostly due to limitations in the Django ORM).


.. class:: DynamicField(spec=None, **kwargs)

    A field for storing Dynamic Columns. The Python data type is ``dict``. Keys
    must be ``str``\s (``unicode`` on Python 2) and values must be one of the
    supported value types in ``mariadb-dyncol``:

    * ``str`` (``unicode`` on Python 2)
    * ``int`` (and also ``long`` on Python 2)
    * ``float``
    * ``datetime.date``
    * ``datetime.datetime``
    * ``datetime.datetime``
    * A nested dict conforming to this spec too

    Note that there are restrictions on the range of values supported for some
    of these types, and that ``decimal.Decimal`` objects are not yet supported
    though they are valid in MariaDB. For more information consult the
    ``mariadb-dyncol`` documentation.

    Values may also be ``None``, though they will then not be stored, since
    dynamic columns do not store ``NULL``, so you should use ``.get()`` to
    retrieve values that may be ``None``.

    To use this field, you'll need to:

    1. Use MariaDB 10.0.2+
    2. Install ``mariadb-dyncol`` (``pip install mariadb-dyncol``)
    3. Use either the ``utf8mb4`` or ``utf8`` character set for your
       database connection.

    These are all checked by the field and you will see sensible errors for
    them when Django's checks run if you have a ``DynamicField`` on a model.

    .. attribute:: spec

        This is an optional type specification that checks that the named
        columns, if present, have the given types. It is validated against on
        ``save()`` to ensure type safety (unlike normal Django validation which
        is only used in forms). It is also used for type information for
        lookups (below).

        ``spec`` should be a ``dict`` with string keys and values that are the
        type classes you expect. You can also nest another such dictionary as a
        value for validating nested dynamic columns.

        For example:

        .. code-block:: python

            import datetime

            class SpecModel(Model):
                attrs = DynamicField(spec={
                    'an_integer_key': int,
                    'created_at': datetime.datetime,
                    'nested_columns': {
                        'lat': int,
                        'lon': int,
                    }
                })

        This will enforce the following rules:

        * ``instance.attrs['an_integer_key']``, if present, is an ``int``
        * ``instance.attrs['created_at']``, if present, is an ``datetime.datetime``
        * ``instance.attrs['nested_columns']``, if present, is a ``dict``
        * ``instance.attrs['nested_columns']['lat']``, if present, is an ``int``
        * ``instance.attrs['nested_columns']['lon']``, if present, is an ``int``

        Trying to save a ``DynamicField`` with data that does not match the
        rules of its ``spec`` will raise ``TypeError``. There is no automatic
        casting, e.g. between ``int`` and ``float``. Note that columns not in
        ``spec`` will still be allowed and have no type enforced.

        For example:

        .. code-block:: python

            >>> SpecModel.objects.create(attrs={'an_integer_key': 1})  # Fine
            >>> SpecModel.objects.create(attrs={'an_integer_key': 2.0})
            Traceback (most recent call last):
            ...
            TypeError: Key 'an_integer_key' should be of type 'int'
            >>> SpecModel.objects.create(attrs={'non_spec_key': 'anytype'})  # Fine

DynamicFields in Forms
----------------------

By default a ``DynamicField`` has no form field, because there isn't really a
practical way to edit its contents. If required, is possible to add extra form
fields to a ``ModelForm`` that then update specific dynamic column names on the
instance in the form's ``save()``.

Querying DynamicField
---------------------

You can query by names, including nested names. In cases where names collide
with existing lookups (e.g. you have a column named ``'exact'``), you might
want to use the :class:`~django_mysql.models.functions.ColumnGet` database
function. You can also use the
:class:`~django_mysql.models.functions.ColumnAdd` and
:class:`~django_mysql.models.functions.ColumnDelete` functions for atomically
modifying the contents of dynamic columns at the database layer.

We'll use the following example model:

.. code-block:: python

    from django_mysql.models import DynamicField, Model

    class ShopItem(Model):
        name = models.CharField(max_length=200)
        attrs = DynamicField(spec={
            'size': str,
        })

        def __str__(self):  # __unicode__ on Python 2
            return self.name

Exact Lookups
~~~~~~~~~~~~~

To query based on an exact match, just use a dictionary.

For example:

.. code-block:: python

    >>> ShopItem.objects.create(name='Camembert', attrs={'smelliness': 15})
    >>> ShopItem.objects.create(name='Cheddar', attrs={'smelliness': 15, 'hardness': 5})

    >>> ShopItem.objects.filter(attrs={'smelliness': 15})
    [<ShopItem: Camembert>]
    >>> ShopItem.objects.filter(attrs={'smelliness': 15, 'hardness': 5})
    [<ShopItem: Cheddar>]


Name Lookups
~~~~~~~~~~~~

To query based on a column name, use that name as a lookup with one of the
below SQL types added after an underscore. If the column name is in your
field's ``spec``, you can omit the SQL type and it will be extracted
automatically - this includes keys in nested ``dict``\s.

The list of SQL types is:

* ``BINARY`` - ``dict`` (a nested ``DynamicField``)
* ``CHAR`` - ``str`` (``unicode`` on Python 2)
* ``DATE`` - ``datetime.date``
* ``DATETIME`` - ``datetime.datetime``
* ``DOUBLE`` - ``float``
* ``INTEGER`` - ``int`` (and also ``long`` on Python 2)
* ``TIME`` - ``datetime.time``

These will also use the correct Django ORM field so chained lookups based on
that type are possible, e.g. ``dynamicfield__age_INTEGER__gte=20``.

Beware that getting a named column can always return ``NULL`` if the column is
not defined for a row.

For example:

.. code-block:: python

    >>> ShopItem.objects.create(name='T-Shirt', attrs={'size': 'Large'})
    >>> ShopItem.objects.create(name='Rocketship', attrs={
    ...     'speed_mph': 300,
    ...     'dimensions': {'width_m': 10, 'height_m': 50}
    ... })

    # Basic template: DynamicField + '__' + column name + '_' + SQL type
    >>> ShopItem.objects.filter(attrs__size_CHAR='Large')
    [<ShopItem: T-Shirt>]

    # As 'size' is in the field's spec, there is no need to give the SQL type
    >>> ShopItem.objects.filter(attrs__size='Large')
    [<ShopItem: T-Shirt>]

    # Chained lookups are possible based on the data type
    >>> ShopItem.objects.filter(attrs__speed_mph_INTEGER__gte=100)
    [<ShopItem: Rocketship>]

    # Nested keys can be looked up
    >>> ShopItem.objects.filter(attrs__dimensions_BINARY__width_m_INTEGER=10)
    [<ShopItem: Rocketship>]

    # Nested DynamicFields can be queried as ``dict``s, as per the ``exact`` lookup
    >>> ShopItem.objects.filter(attrs__dimensions_BINARY={'width_m': 10, 'height_m': 50})
    [<ShopItem: Rocketship>]

    # Missing keys are always NULL
    >>> ShopItem.objects.filter(attrs__blablabla_INTEGER__isnull=True)
    [<ShopItem: T-Shirt>, <ShopItem: Rocketship>]
