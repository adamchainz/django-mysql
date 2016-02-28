.. _json-field:

---------
JSONField
---------

.. currentmodule:: django_mysql.models

**MySQL 5.7** comes with a JSON data type that stores JSON in a way that is
queryable and updatable in place. This is ideal for data that varies widely, or
very sparse columns, or just for storing API responses that you don't have time
to turn into the relational format.

Docs: `MySQL <https://dev.mysql.com/doc/refman/5.7/en/json.html>`_.

Django-MySQL supports the JSON data type and related functions through
``JSONField`` plus some
:ref:`JSON database functions <json-database-functions>`.


.. class:: JSONField(**kwargs)

    A field for storing JSON. The Python data type may be either ``str``
    (``unicode`` on Python 2), ``int``, ``float``, ``dict``, or ``list`` -
    basically anything that is supported by ``json.dumps``. There is no
    restriction between these types - this may be surprising if you expect it
    to just store JSON objects/``dict``\s.

    So for example, the following all work:

    .. code-block:: python

        mymodel.myfield = "a string"
        mymodel.myfield = 1
        mymodel.myfield = 0.3
        mymodel.myfield = ["a", "list"]
        mymodel.myfield = {"a": "dict"}

    This field requires Django 1.8+ and MySQL 5.7+. Both requirements are
    checked by the field and you'll get sensible errors for them when Django's
    checks run if you're not up to date on either.

JSONFields in Forms
-------------------

By default this uses the simple Django-MySQL form field
:class:`~django_mysql.forms.JSONField`, which simply displays the JSON in an
HTML ``<textarea>``.


Querying JSONField
------------------

You can query by object keys as well as array positions. In cases where names
collide with existing lookups, you might want to use the
:class:`~django_mysql.models.functions.JSONExtract` database function.

.. warning::

    Most of the standard lookups don't make sense for ``JSONField`` and so have
    been made to fail with ``NotImplementedError``. There is scope for making
    some of them work in the future, but it's non-trivial. Only the lookups
    documented below work.

    Also be careful with the key lookups. Since any string could be a key in a
    JSON object, any lookup name other than the standard ones or those listed
    below will be interpreted as a key lookup. No errors are raised. Be extra
    careful for typing mistakes, and always check your queries, e.g.
    ``myfield__eaxct`` as a typo of ``myfield__exact`` will not do what the
    author intended!

We'll use the following example model:

.. code-block:: python

    from django_mysql.models import DynamicField, Model

    class ShopItem(Model):
        name = models.CharField(max_length=200)
        attrs = JSONField()

        def __str__(self):  # __unicode__ on Python 3
            return self.name

Exact Lookups
~~~~~~~~~~~~~

To query based on an exact match, just use an object of any JSON type.

For example:

.. code-block:: python

    >>> ShopItem.objects.create(name='Gruyère', attrs={'smelliness': 5})
    >>> ShopItem.objects.create(name='Feta', attrs={'smelliness': 3, 'crumbliness': 10})
    >>> ShopItem.objects.create(name='Hack', attrs=[1, 'arbitrary', 'data'])

    >>> ShopItem.objects.filter(attrs={'smelliness': 5})
    [<ShopItem: Gruyère>]
    >>> ShopItem.objects.filter(attrs__exact={'smelliness': 3, 'crumbliness': 10})
    [<ShopItem: Feta>]
    >>> ShopItem.objects.filter(attrs=[1, 'arbitrary', 'data'])
    [<ShopItem: Hack>]


Ordering Lookups
~~~~~~~~~~~~~~~~

MySQL defines an ordering on JSON objects - see
`the docs <https://dev.mysql.com/doc/refman/5.7/en/json.html#json-comparison>`_
for more details. The ordering rules can make sense for some types (e.g.
strings, arrays), however they can also be confusing if your data is of mixed
types, so be careful. You can use the ordering by querying with Django's
built-in ``gt``, ``gte``, ``lt``, and ``lte`` lookups.

For example:

.. code-block:: py

    >>> ShopItem.objects.create(name='Cheshire', attrs=['Dense', 'Crumbly'])
    >>> ShopItem.objects.create(name='Double Gloucester', attrs=['Semi-hard'])

    >>> ShopItem.objects.filter(attrs__gt=['Dense', 'Crumbly'])
    [<ShopItem: Double Gloucester>]
    >>> ShopItem.objects.filter(attrs__lte=['ZZZ'])
    [<ShopItem: Cheshire>, <ShopItem: Double Gloucester>]

Key, Index, and Path Lookups
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To query based on a given dictionary key, use that key as the lookup name:

.. code-block:: python

    >>> ShopItem.objects.create(name='Gruyère', attrs={
        'smelliness': 5,
        'origin': {
            'country': 'Switzerland',
        }
        'certifications': ['Swiss AOC', 'Swiss AOP'],
    })
    >>> ShopItem.objects.create(name='Feta', attrs={'smelliness': 3, 'crumbliness': 10})

    >>> ShopItem.objects.filter(attrs__smelliness=3)
    [<ShopItem: Feta>]

Multiple keys can be chained together to form a path lookup:

.. code-block:: python

    >>> ShopItem.objects.filter(attrs__origin__country='Switzerland')
    [<ShopItem: Gruyère>]

If the key is an integer, it will be interpreted as an index lookup in an
array:

.. code-block:: python

    >>> ShopItem.objects.filter(attrs__certifications__0='Swiss AOC')
    [<ShopItem: Gruyère>]

If the key you wish to query is not valid for a Python keyword argument (e.g.
it contains unicode characters), or it clashes with the name of another field
lookup, use the :class:`~django_mysql.models.functions.JSONExtract` database
function to fetch it.
