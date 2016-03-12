.. _set-fields:

----------
Set Fields
----------

.. currentmodule:: django_mysql.models

Two fields that store sets of a base field in comma-separated strings -
cousins of Django's :class:`~django.db.models.CommaSeparatedIntegerField`.
There are two versions: ``SetCharField``, which is based on ``CharField`` and
appropriate for storing sets with a small maximum size, and ``SetTextField``,
which is based on ``TextField`` and therefore suitable for sets of (near)
unbounded size (the underlying ``LONGTEXT`` MySQL datatype has a maximum length
of 2\ :sup:`32` - 1 bytes).


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

    Example instantiation:

    .. code-block:: python

        from django.db.models import IntegerField, Model
        from django_mysql.models import SetCharField

        class LotteryTicket(Model):
            numbers = SetCharField(
                base_field=IntegerField(),
                size=6,
                max_length=(6 * 3)  # 6 two digit numbers plus commas
            )

    In Python simply set the field's value as a set:

    .. code-block:: pycon

        >>> lt = LotteryTicket.objects.create(numbers={1, 2, 4, 8, 16, 32})
        >>> lt.numbers
        {1, 2, 4, 8, 16, 32}
        >>> lt.numbers.remove(1)
        >>> lt.numbers.add(3)
        >>> lt.numbers
        {32, 3, 2, 4, 8, 16}
        >>> lt.save()

    .. admonition:: Validation on save()

        When performing the set-to-string conversion for the database,
        ``SetCharField`` performs some validation, and will raise
        ``ValueError`` if there is a problem, to avoid saving bad data.
        The following are invalid:

        * If there is a comma in any member's string representation
        * If the empty string is stored.

    The default form field is :class:`~django_mysql.forms.SimpleSetField`.


.. class:: SetTextField(base_field, size=None, **kwargs):

    The same as ``SetCharField``, but backed by a ``TextField`` and therefore
    much less restricted in length. There is no ``max_length`` argument.

    Example instantiation:

    .. code-block:: python

        from django.db.models import IntegerField, Model
        from django_mysql.models import SetTextField

        class Post(Model):
            tags = SetTextField(
                base_field=CharField(max_length=32),
            )


Querying Set Fields
-------------------

.. warning::

    These fields are not built-in datatypes, and the filters use one or more
    SQL functions to parse the underlying string representation. They may slow
    down on large tables if your queries are not selective on other columns.

contains
~~~~~~~~

The ``contains`` lookup is overridden on ``SetCharField`` and ``SetTextField``
to match where the set field contains the given element, using MySQL's
``FIND_IN_SET`` (docs:
`MariaDB <https://mariadb.com/kb/en/mariadb/find_in_set/>`_ /
`MySQL <http://dev.mysql.com/doc/refman/5.5/en/string-functions.html#function_find-in-set>`_).

For example:

.. code-block:: pycon

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

A transform that converts to the number of items in the set. For example:

.. code-block:: pycon

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
level:

.. code-block:: pycon

    >>> from django_mysql.models import SetF
    >>> Post.objects.filter(tags__contains="django").update(tags=SetF('tags').add('programming'))
    2
    >>> Post.objects.update(tags=SetF('tags').remove('thoughts'))
    2

Or with attribute assignment to a model:

.. code-block:: pycon

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
        contained:

        .. code-block:: python

            post.tags = SetF('tags').add('python')
            post.save()

    .. method:: remove(value)

        Takes an expression and returns a new expression that will remove the
        given item from the set field if it is present:

        .. code-block:: python

            post.tags = SetF('tags').remove('python')
            post.save()

    .. warning::

        Both of the above methods use SQL expressions with user variables in
        their queries, all of which start with ``@tmp_``. This shouldn't affect
        you much, but if you use user variables in your queries, beware for
        any conflicts.
