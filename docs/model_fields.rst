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

Two fields that store lists of data, grown-up versions of django's
:class:`~django.db.models.CommaSeparatedIntegerField`, cousins of
``django.contrib.postgres``'s
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
occurence of a given element is at a given position. There are no errors if
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
    query about the *first* occurence of the given item. For example, this is
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

    Unlike the similar feature on ``django.contrib.postgres``'s ArrayField,
    'Index transforms', these are lookups, and only allow direct value
    comparison rather than continued chaining with the base-field lookups. This
    is because the field is not a native list type in MySQL.



``ListF()`` expressions
----------------------

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
cousins of django's :class:`~django.db.models.CommaSeparatedIntegerField`.
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

            post.tags = SetF('tags').remove('pthyon')
            post.save()

    .. warning::

        Both of the above methods use SQL expressions with user variables in
        their queries, all of which start with ``@tmp_``. This shouldn't affect
        you much, but if you use user variables in your queries, beware for
        any conflicts.
