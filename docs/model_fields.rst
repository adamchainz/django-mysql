.. _model-fields:

============
Model Fields
============


More ways to store data! The following can be imported from
``django_mysql.models``.

.. currentmodule:: django_mysql.models


.. _list-fields:

-----------
List Fields
-----------

Two fields that store lists of data, big brothers of django's
:class:`~django.db.models.CommaSeparatedIntegerField`, contenders to
`django.contrib.postgres`'s
:class:`~django.contrib.postgres.fields.ArrayField`. There are two versions:
``ListCharField``, which is based on ``CharField`` and appropriate for storing
lists with a small maximum size, and ``ListTextField``, which is based on
``TextField`` and therefore suitable for lists of unbounded size.

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
        from django_mysql.models import Model, ListCharField

        class Person(Model):
            post_nominals = ListCharField(
                base_field=CharField(),
                size=6,
                max_length=(6 * 3)  # 6 two digit numbers plus commas
            )

    .. admonition:: Validation on save()

        When performing the list-to-string conversion for the database,
        ``SetCharField`` performs some validation, and will raise
        ``ValueError`` if there is a problem, to avoid saving bad data.
        The following are invalid:

        * Any member containing a comma in its string representation
        * Any member whose string representation is the empty string

    The default form field is :class:`~django_mysql.forms.SimpleListField`.


Querying Set Fields
-------------------

.. warning::

    These fields not built-in datatypes, and the filters use one or more SQL
    functions to parse the underlying string representation. They may slow down
    on large tables if your queries are not otherwise selective.

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

    >>> Person.objects.filter(middle_names__contains='PhD')
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

This class of lookups allows you to index into the list to check if a certain
element is in a certain position. There are no errors if it exceeds the
``size`` of the list. For example::

    >>> Person.objects.filter(post_nominals__0='PhD')
    [<Person: Horatio>, <Person: Severus>]

    >>> Person.objects.filter(post_nominals__1='DPhil')
    [<Person: Severus>]

    >>> Person.objects.filter(post_nominals__100='VC')
    []


.. note::

    ``FIND_IN_SET`` uses 1-based indexing for searches on comma-based strings
    when writing raw SQL. However these indexes use 0-based indexing to be
    consistent with Python

.. note::

    Unlike the similar feature on ``django.contrib.postgres``'s ArrayField,
    'Index transforms', these are lookups, and only allow direct value
    comparison rather than continued chaining with the base-field lookups. This
    is because the field is not a native list type in MySQL.


.. _set-fields:

----------
Set Fields
----------

Two fields that store sets of a base field in comma-separated strings - big
brothers of django's :class:`~django.db.models.CommaSeparatedIntegerField`.
There are two versions: ``SetCharField``, which is based on ``CharField`` and
appropriate for storing sets with a small maximum size, and ``SetTextField``,
which is based on ``TextField`` and therefore suitable for sets of unbounded
size.

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

    These fields not built-in datatypes, and the filters use one or more SQL
    functions to parse the underlying string representation. They may slow down
    on large tables if your queries are not otherwise selective.

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
