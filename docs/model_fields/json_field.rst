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

    .. warning::

        If you give the field a ``default``, ensure it's a callable, such as
        ``dict``, ``list``, or ``lambda: {'key': 'value'}``. Incorrectly using
        a mutable object, such as ``default={}``, creates a single object that
        is shared between all instances of the field. There's a field check
        that errors if a plain ``list`` or ``dict`` instance is used for
        ``default``, so there is some protection against this.

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

Key Presence Lookups
~~~~~~~~~~~~~~~~~~~~

To query to check if an object has a given key, use the ``has_key`` lookup:

.. code-block:: python

    # Find all ShopItems with a hardness rating
    >>> ShopItem.objects.filter(attrs__has_key='hardness')
    []
    # Find all ShopItems missing certification information
    >>> ShopItem.objects.exclude(attrs__has_key='certifications')
    [<ShopItem: Feta>]

To check if an object has several keys, use the ``has_keys`` lookup with a list
of keys:

.. code-block:: python

    # Find all ShopItems with both origin and certification information
    >>> ShopItem.objects.filter(attrs_has_keys=['origin', 'certifications'])
    [<ShopItem: Gruyère>]

To find objects with one of several keys, use the ``has_any_keys`` lookup with
a list of keys:

.. code-block:: python

    # Find all ShopItems with either a smelliness or a hardness rating
    >>> ShopItem.objects.filter(attrs_has_any_keys=['smelliness', 'hardness'])
    [<ShopItem: Gruyère>, <ShopItem: Feta>]

Length Lookup
~~~~~~~~~~~~~

This is very similar to the :class:`~django_mysql.models.functions:JSONLength`
database function. You can use it to filter based upon the length of the JSON
documents in the field, using the MySQL ``JSON_LENGTH`` function.

As per the MySQL documentation, the length of a document is determined as
follows:

* The length of a scalar is 1.
* The length of an array is the number of array elements.
* The length of an object is the number of object members.
* The length does not count the length of nested arrays or objects.

Docs:
`MySQL <https://dev.mysql.com/doc/refman/5.7/en/json-attribute-functions.html#function_json-length>`_.

For example:

.. code-block:: python

    # Find all the ShopItems with nothing in 'attrs'
    >>> ShopItems.objects.filter(attrs__length=0)
    []
    # Find all the ShopItems with >50 keys in 'attrs'
    >>> ShopItems.objects.filter(attrs__length__gt=50)
    [<ShopItem: Incredible Cheese>]

Containment Lookups
~~~~~~~~~~~~~~~~~~~

The ``contains`` lookup is overriden on ``JSONField`` to support the MySQL
``JSON_CONTAINS`` function. This allows you to search, for example, JSON
objects that contain at least a given set of key-value pairs. Additionally you
can do the inverse with ``contained_by``, i.e. find values where the objects
are contained by a given value.

The definition of containment is, as per the MySQL docs:

* A candidate scalar is contained in a target scalar if and only if they are
  comparable and are equal. Two scalar values are comparable if they have the
  same ``JSON_TYPE()`` types, with the exception that values of types
  ``INTEGER`` and ``DECIMAL`` are also comparable to each other.

* A candidate array is contained in a target array if and only if every element
  in the candidate is contained in some element of the target.

* A candidate nonarray is contained in a target array if and only if the
  candidate is contained in some element of the target.

* A candidate object is contained in a target object if and only if for each
  key in the candidate there is a key with the same name in the target and the
  value associated with the candidate key is contained in the value associated
  with the target key.

Docs:
`MySQL <https://dev.mysql.com/doc/refman/5.7/en/json-search-functions.html#function_json-contains>`_.

For example:

.. code-block:: python

    # Find all ShopItems with a crumbliness of 10 and a smelliness of 5
    >>> ShopItems.objects.filter(attrs__contains={
        'crumbliness': 10,
        'smelliness': 5,
    })
    [<ShopItem: Feta>]

    # Find all ShopItems that have either 0 properties, or 1 or more of the given properties
    >>> ShopItems.objects.filter(attrs__contained_by={
        'crumbliness': 10,
        'hardness': 1,
        'smelliness': 5,
    })
    [<ShopItem: Feta>]
g
