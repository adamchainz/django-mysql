.. _list-fields:

-----------
List Fields
-----------

.. currentmodule:: django_mysql.models

Two fields that store lists of data, grown-up versions of Django's
:class:`~django.db.models.CommaSeparatedIntegerField`, cousins of
``django.contrib.postgres``'s
:class:`~django.contrib.postgres.fields.ArrayField`. There are two versions:
``ListCharField``, which is based on ``CharField`` and appropriate for storing
lists with a small maximum size, and ``ListTextField``, which is based on
``TextField`` and therefore suitable for lists of (near) unbounded size (the
underlying ``LONGTEXT`` MySQL datatype has a maximum length of 2\ :sup:`32` -
1 bytes).


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

    Example instantiation:

    .. code-block:: python

        from django.db.models import CharField, Model
        from django_mysql.models import ListCharField

        class Person(Model):
            name = CharField()
            post_nominals = ListCharField(
                base_field=CharField(max_length=10),
                size=6,
                max_length=(6 * 11)  # 6 * 10 character nominals, plus commas
            )

    In Python simply set the field's value as a list:

    .. code-block:: pycon

        >>> p = Person.objects.create(name='Horatio', post_nominals=['PhD', 'Esq.'])
        >>> p.post_nominals
        ['PhD', 'Esq.']
        >>> p.post_nominals.append('III')
        >>> p.post_nominals
        ['PhD', 'Esq.', 'III']
        >>> p.save()

    .. admonition:: Validation on save()

        When performing the list-to-string conversion for the database,
        ``ListCharField`` performs some validation, and will raise
        ``ValueError`` if there is a problem, to avoid saving bad data.
        The following are invalid:

        * Any member containing a comma in its string representation
        * Any member whose string representation is the empty string

    The default form field is :class:`~django_mysql.forms.SimpleListField`.


.. class:: ListTextField(base_field, size=None, **kwargs)

    The same as ``ListCharField``, but backed by a ``TextField`` and therefore
    much less restricted in length. There is no ``max_length`` argument.

    Example instantiation:

    .. code-block:: python

        from django.db.models import IntegerField, Model
        from django_mysql.models import ListTextField

        class Widget(Model):
            widget_group_ids = ListTextField(
                base_field=IntegerField(),
                size=100,  # Maximum of 100 ids in list
            )


Querying List Fields
--------------------

.. warning::

    These fields are not built-in datatypes, and the filters use one or more
    SQL functions to parse the underlying string representation. They may slow
    down on large tables if your queries are not selective on other columns.

contains
~~~~~~~~

The ``contains`` lookup is overridden on ``ListCharField`` and
``ListTextField`` to match where the set field contains the given element,
using MySQL's ``FIND_IN_SET`` function (docs:
`MariaDB <https://mariadb.com/kb/en/mariadb/find_in_set/>`_ /
`MySQL <http://dev.mysql.com/doc/refman/5.5/en/string-functions.html#function_find-in-set>`_ docs).

For example:

.. code-block:: pycon

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

A transform that converts to the number of items in the list. For example:

.. code-block:: pycon

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
it exceeds the ``size`` of the list. For example:

.. code-block:: pycon

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
    a non-match:

    .. code-block:: pycon

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
level:

.. code-block:: pycon

    >>> from django_mysql.models import ListF
    >>> Person.objects.filter(post_nominals__contains="PhD").update(
    ...     post_nominals=ListF('post_nominals').append('Sr.')
    ... )
    2
    >>> Person.objects.update(
    ...     post_nominals=ListF('post_nominals').pop()
    ... )
    3

Or with attribute assignment to a model:

.. code-block:: pycon

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
        list, like ``list.append``:

        .. code-block:: pycon

            >>> Person.objects.create(name='Horatio', post_nominals=['PhD', 'Esq.', 'III'])
            >>> Person.objects.update(
            ...     post_nominals=ListF('post_nominals').append('DSocSci')
            ... )
            >>> Person.objects.get().full_name
            "Horatio Phd Esq. III DSocSci"

    .. method:: appendleft(value)

        Adds the value of the given expression to the (left hand) end of the
        list, like ``deque.appendleft``:

        .. code-block:: pycon

            >>> Person.objects.update(
            ...     post_nominals=ListF('post_nominals').appendleft('BArch')
            ... )
            >>> Person.objects.get().full_name
            "Horatio BArch Phd Esq. III DSocSci"

    .. method:: pop()

        Takes one value from the (right hand) end of the list, like
        ``list.pop``:

        .. code-block:: pycon

            >>> Person.objects.update(
            ...     post_nominals=ListF('post_nominals').pop()
            ... )
            >>> Person.objects.get().full_name
            "Horatio BArch Phd Esq. III"

    .. method:: popleft()

        Takes one value off the (left hand) end of the list, like
        ``deque.popleft``:

        .. code-block:: pycon

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

