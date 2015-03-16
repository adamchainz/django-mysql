.. _model-fields:

============
Model Fields
============


More ways to store data! The following can be imported from
``django_mysql.models``.

.. currentmodule:: django_mysql.models

.. _set-fields:

----------
Set Fields
----------

Two fields that store sets of a base type in comma-separated strings - big
brothers of django's :class:`~django.db.models.CommaSeparatedIntegerField`.
There are two versions: ``SetCharField`` which is based on ``CharField``,
appropriate for storing sets with a small maximum size, and ``SetTextField``
which is based on ``TextField``, and therefore suitable for sets of unbounded
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

    The default form field is :class:`~django_mysql.forms.SimpleSetField`.

Querying Set Fields
-------------------

.. warning::

    These fields not built-in datatypes, and the filters use one or more SQL
    functions to parse the underlying string representation. They may slow down
    on large tables if your queries are not selective via some other column.

contains
~~~~~~~~

The ``contains`` lookup is overridden on ``SetCharField`` and ``SetTextField``
to match only where the set contains the given element, using MySQL's
``FIND_IN_SET``. For example::

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

Matches based upon the number of items in the set. For example::

    >>> Post.objects.filter(tags__len=1)
    [<Post: Second post>]

    >>> Post.objects.filter(tags__len=2)
    [<Post: First post>, <Post: Third post>]

    >>> Post.objects.filter(tags__len=0)
    []
