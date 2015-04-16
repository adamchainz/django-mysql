.. _model-fields:

============
Model Fields
============


More ways to store data! The following can be imported from
``django_mysql.models``.

.. currentmodule:: django_mysql.models

.. _dynamic-columns-field:

------------
DynamicField
------------

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
    * A nested dict conforming to thsi spec too

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

    >>> ShopItem.objects.create(name='Camembert', {'smelliness': 15})
    >>> ShopItem.objects.create(name='Cheddar', {'smelliness': 15, 'hardness': 5})

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

    >>> ShopItem.objects.create(name='T-Shirt', {'size': 'Large'})
    >>> ShopItem.objects.create(name='Rocketship', {
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


.. _list-fields:

-----------
List Fields
-----------

Two fields that store lists of data, grown-up versions of Django's
:class:`~django.db.models.CommaSeparatedIntegerField`, cousins of
``django.contrib.postgres``'s
:class:`~django.contrib.postgres.fields.ArrayField`. There are two versions:
``ListCharField``, which is based on ``CharField`` and appropriate for storing
lists with a small maximum size, and ``ListTextField``, which is based on
``TextField`` and therefore suitable for lists of (near) unbounded size (the
underlying ``LONGTEXT`` MySQL datatype has a maximum length of 2\ :sup:`32` -
1 bytes).

For the purposes of keeping documentation short, we'll describe
``ListCharField``, but everything below applies equally to ``ListTextField``,
except for ``max_length`` which is not needed.


.. class:: ListCharField(base_field, size=None, **kwargs)

    A field for storing lists of data, all of which conform to the
    ``base_field``.

    .. attribute:: base_field

        The base type of the data that is stored in the list. Currently, must
        be ``IntegerField``, ``CharField``, or any subclass thereof - except
        from ``ListCharField`` itself.

    .. attribute:: size

        Optionally set the maximum numbers of items in the list. This is only
        checked on form validation, not on model save!

    As ``ListCharField`` is a subclass of ``CharField``, any ``CharField``
    options can be set too. Most importantly you'll need to set ``max_length``
    to determine how many characters to reserve in the database.

    Example instantiation::

        from django.db.models import IntegerField
        # Does not require django_mysql.models.Model - just using it for the
        # QuerySet extensions
        from django_mysql.models import Model, ListCharField

        class Person(Model):
            post_nominals = ListCharField(
                base_field=CharField(max_length=32),
                size=6,
                max_length=(6 * 3)  # 6 two digit numbers plus commas
            )

    .. admonition:: Validation on save()

        When performing the list-to-string conversion for the database,
        ``ListCharField`` performs some validation, and will raise
        ``ValueError`` if there is a problem, to avoid saving bad data.
        The following are invalid:

        * Any member containing a comma in its string representation
        * Any member whose string representation is the empty string

    The default form field is :class:`~django_mysql.forms.SimpleListField`.


Querying Set Fields
-------------------

.. warning::

    These fields are not built-in datatypes, and the filters use one or more
    SQL functions to parse the underlying string representation. They may slow
    down on large tables if your queries are not otherwise selective.

contains
~~~~~~~~

The ``contains`` lookup is overridden on ``ListCharField`` and
``ListTextField`` to match where the set field contains the given element,
using MySQL's ``FIND_IN_SET`` function (docs:
`MariaDB <https://mariadb.com/kb/en/mariadb/find_in_set/>`_ /
`MySQL <http://dev.mysql.com/doc/refman/5.5/en/string-functions.html#function_find-in-set>`_ docs).
For example::

    >>> Person.objects.create(name='Horatio', post_nominals=['PhD', 'Esq.', 'III'])
    >>> Person.objects.create(name='Severus', post_nominals=['PhD', 'DPhil'])
    >>> Person.objects.create(name='Paulus', post_nominals=[])

    >>> Person.objects.filter(post_nominals__contains='PhD')
    [<Person: Horatio>, <Person: Severus>]

    >>> Person.objects.filter(post_nominals__contains='Esq.')
    [<Person: Horatio>]

    >>> Person.objects.filter(post_nominals__contains='DPhil')
    [<Person: Severus>]

    >>> Person.objects.filter(Q(post_nominals__contains='PhD') & Q(post_nominals__contains='III'))
    [<Person: Horatio>]

.. note::

    ``ValueError`` will be raised if you try ``contains`` with a list. It's not
    possible without using ``AND`` in the query, so you should add the filters
    for each item individually, as per the last example.


len
~~~

A transform that converts to the number of items in the list. For example::

    >>> Person.objects.filter(post_nominals__len=0)
    [<Person: Paulus>]

    >>> Person.objects.filter(post_nominals__len=2)
    [<Person: Severus>]

    >>> Person.objects.filter(post_nominals__len__gt=2)
    [<Person: Horatio>]


Index lookups
~~~~~~~~~~~~~

This class of lookups allows you to index into the list to check if the first
occurrence of a given element is at a given position. There are no errors if
it exceeds the ``size`` of the list. For example::

    >>> Person.objects.filter(post_nominals__0='PhD')
    [<Person: Horatio>, <Person: Severus>]

    >>> Person.objects.filter(post_nominals__1='DPhil')
    [<Person: Severus>]

    >>> Person.objects.filter(post_nominals__100='VC')
    []


.. warning::

    The underlying function, ``FIND_IN_SET``, is designed for *sets*, i.e.
    comma-separated lists of unique elements. It therefore only allows you to
    query about the *first* occurrence of the given item. For example, this is
    a non-match::

        >>> Person.objects.create(name='Cacistus', post_nominals=['MSc', 'MSc'])
        >>> Person.objects.filter(post_nominals__1='MSc')
        []  # Cacistus does not appear because his first MSc is at position 0

    This may be fine for your application, but be careful!

.. note::

    ``FIND_IN_SET`` uses 1-based indexing for searches on comma-based strings
    when writing raw SQL. However these indexes use 0-based indexing to be
    consistent with Python.

.. note::

    Unlike the similar feature on ``django.contrib.postgres``'s ``ArrayField``,
    'Index transforms', these are lookups, and only allow direct value
    comparison rather than continued chaining with the base-field lookups. This
    is because the field is not a native list type in MySQL.



``ListF()`` expressions
-----------------------

Similar to Django's :class:`~django.db.models.F` expression, this allows you to
perform an atomic add and remove operations on list fields at the database
level::

    >>> from django_mysql.models import ListF
    >>> Person.objects.filter(post_nominals__contains="PhD").update(
    ...     post_nominals=ListF('post_nominals').append('Sr.')
    ... )
    2
    >>> Person.objects.update(
    ...     post_nominals=ListF('post_nominals').pop()
    ... )
    3

Or with attribute assignment to a model::

    >>> horatio = Person.objects.get(name='Horatio')
    >>> horatio.post_nominals = ListF('post_nominals').append('DSocSci')
    >>> horatio.save()

.. class:: ListF(field_name)

    You should instantiate this class with the name of the field to use, and
    then call one of its methods.

    Note that unlike :class:`~django.db.models.F`, you cannot chain the methods
    - the SQL involved is a bit too complicated, and thus only single
    operations are supported.

    .. method:: append(value)

        Adds the value of the given expression to the (right hand) end of the
        list, like ``list.append``::

            >>> Person.objects.create(name='Horatio', post_nominals=['PhD', 'Esq.', 'III'])
            >>> Person.objects.update(
            ...     post_nominals=ListF('post_nominals').append('DSocSci')
            ... )
            >>> Person.objects.get().full_name
            "Horatio Phd Esq. III DSocSci"

    .. method:: appendleft(value)

        Adds the value of the given expression to the (left hand) end of the
        list, like ``deque.appendleft``::

            >>> Person.objects.update(
            ...     post_nominals=ListF('post_nominals').appendleft('BArch')
            ... )
            >>> Person.objects.get().full_name
            "Horatio BArch Phd Esq. III DSocSci"

    .. method:: pop()

        Takes one value from the (right hand) end of the list, like
        ``list.pop``::

            >>> Person.objects.update(
            ...     post_nominals=ListF('post_nominals').pop()
            ... )
            >>> Person.objects.get().full_name
            "Horatio BArch Phd Esq. III"

    .. method:: popleft()

        Takes one value off the (left hand) end of the list, like
        ``deque.popleft``::

            >>> Person.objects.update(
            ...     post_nominals=ListF('post_nominals').popleft()
            ... )
            >>> Person.objects.get().full_name
            "Horatio Phd Esq. III"

    .. warning::

        All the above methods use SQL expressions with user variables in their
        queries, all of which start with ``@tmp_``. This shouldn't affect you
        much, but if you use user variables in your queries, beware for any
        conflicts.


.. _set-fields:

----------
Set Fields
----------

Two fields that store sets of a base field in comma-separated strings -
cousins of Django's :class:`~django.db.models.CommaSeparatedIntegerField`.
There are two versions: ``SetCharField``, which is based on ``CharField`` and
appropriate for storing sets with a small maximum size, and ``SetTextField``,
which is based on ``TextField`` and therefore suitable for sets of (near)
unbounded size (the underlying ``LONGTEXT`` MySQL datatype has a maximum length
of 2\ :sup:`32` - 1 bytes).

For the purposes of keeping documentation short, we'll describe
``SetCharField``, but everything below applies equally to ``SetTextField``,
except for ``max_length`` which is not needed.


.. class:: SetCharField(base_field, size=None, **kwargs):

    A field for storing sets of data, which all conform to the ``base_field``.

    .. attribute:: base_field

        The base type of the data that is stored in the set. Currently, must be
        ``IntegerField``, ``CharField``, or any subclass thereof - except from
        ``SetCharField`` itself.

    .. attribute:: size

        Optionally set the maximum number of elements in the set. This is only
        checked on form validation, not on model save!

    As ``SetCharField`` is a subclass of ``CharField``, any ``CharField``
    options can be set too. Most importantly you'll need to set ``max_length``
    to determine how many characters to reserve in the database.

    Example instantiation::

        from django.db.models import IntegerField
        # Does not require django_mysql.models.Model - just using it for the
        # QuerySet extensions
        from django_mysql.models import Model, SetCharField

        class LotteryTicket(Model):
            numbers = SetCharField(
                base_field=IntegerField(),
                size=6,
                max_length=(6 * 3)  # 6 two digit numbers plus commas
            )

    .. admonition:: Validation on save()

        When performing the set-to-string conversion for the database,
        ``SetCharField`` performs some validation, and will raise
        ``ValueError`` if there is a problem, to avoid saving bad data.
        The following are invalid:

        * If there is a comma in any member's string representation
        * If the empty string is stored.

    The default form field is :class:`~django_mysql.forms.SimpleSetField`.

Querying Set Fields
-------------------

.. warning::

    These fields are not built-in datatypes, and the filters use one or more
    SQL functions to parse the underlying string representation. They may slow
    down on large tables if your queries are not otherwise selective.

contains
~~~~~~~~

The ``contains`` lookup is overridden on ``SetCharField`` and ``SetTextField``
to match where the set field contains the given element, using MySQL's
``FIND_IN_SET`` (docs:
`MariaDB <https://mariadb.com/kb/en/mariadb/find_in_set/>`_ /
`MySQL <http://dev.mysql.com/doc/refman/5.5/en/string-functions.html#function_find-in-set>`_).
For example::

    >>> Post.objects.create(name='First post', tags={'thoughts', 'django'})
    >>> Post.objects.create(name='Second post', tags={'thoughts'})
    >>> Post.objects.create(name='Third post', tags={'tutorial', 'django'})

    >>> Post.objects.filter(tags__contains='thoughts')
    [<Post: First post>, <Post: Second post>]

    >>> Post.objects.filter(tags__contains='django')
    [<Post: First post>, <Post: Third post>]

    >>> Post.objects.filter(Q(tags__contains='django') & Q(tags__contains='thoughts'))
    [<Post: First post>]


.. note::

    ``ValueError`` will be raised if you try ``contains`` with a set. It's not
    possible without using ``AND`` in the query, so you should add the filters
    for each item individually, as per  the last example.


len
~~~

A transform that converts to the number of items in the set. For example::

    >>> Post.objects.filter(tags__len=1)
    [<Post: Second post>]

    >>> Post.objects.filter(tags__len=2)
    [<Post: First post>, <Post: Third post>]

    >>> Post.objects.filter(tags__len__lt=2)
    [<Post: Second post>]


``SetF()`` expressions
----------------------

Similar to Django's :class:`~django.db.models.F` expression, this
allows you to perform an atomic add or remove on a set field at the database
level::

    >>> from django_mysql.models import SetF
    >>> Post.objects.filter(tags__contains="django").update(tags=SetF('tags').add('programming'))
    2
    >>> Post.objects.update(tags=SetF('tags').remove('thoughts'))
    2

Or with attribute assignment to a model::

    >>> post = Post.objects.earliest('id')
    >>> post.tags = SetF('tags').add('python')
    >>> post.save()

.. class:: SetF(field_name)

    You should instantiate this class with the name of the field to use, and
    then call one of its two methods with a value to be added/removed.

    Note that unlike :class:`~django.db.models.F`, you cannot chain
    the methods - the SQL involved is a bit too complicated, and thus you can
    only perform a single addition or removal.

    .. method:: add(value)

        Takes an expression and returns a new expression that will take the
        value of the original field and add the value to the set if it is not
        contained::

            post.tags = SetF('tags').add('python')
            post.save()

    .. method:: remove(value)

        Takes an expression and returns a new expression that will remove the
        given item from the set field if it is present::

            post.tags = SetF('tags').remove('python')
            post.save()

    .. warning::

        Both of the above methods use SQL expressions with user variables in
        their queries, all of which start with ``@tmp_``. This shouldn't affect
        you much, but if you use user variables in your queries, beware for
        any conflicts.


.. _resizable-blob-text-fields:

----------------------------
Resizable Text/Binary Fields
----------------------------

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
