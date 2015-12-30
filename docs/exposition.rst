Exposition
==========

Every feature in whistle-stop detail.

-------------------
QuerySet Extensions
-------------------

Django-MySQL comes with a number of extensions to ``QuerySet`` that can be
installed in a number of ways - e.g. adding the ``QuerySetMixin`` to your
existing ``QuerySet`` subclass.


Approximate Counting
--------------------

``SELECT COUNT(*) ...`` can become a slow query, since it requires a scan of
all rows; the ``approx_count`` functions solves this by returning the estimated
count that MySQL keeps in metadata. You can call it directly::

    Author.objects.approx_count()

Or if you have pre-existing code that calls ``count()`` on a ``QuerySet`` you
pass it, such as the Django Admin, you can set the ``QuerySet`` to do try
``approx_count`` first automatically::

    qs = Author.objects.all().count_tries_approx()
    # Now calling qs.count() will try approx_count() first

:ref:`Read more <approximate-counting>`


Query Hints
-----------

Use MySQL's query hints to optimize the SQL your ``QuerySet``\s generate::

    Author.objects.straight_join().filter(book_set__title__startswith="The ")
    # Does SELECT STRAIGHT_JOIN ...

:ref:`Read more <query_hints>`

'Smart' Iteration
-----------------

Sometimes you need to modify every single instance of a model in a big table,
without creating any long running queries that consume large amounts of
resources. The 'smart' iterators traverse the table by slicing it into primary
key ranges which span the table, performing each slice separately, and
dynamically adjusting the slice size to keep them fast::

    # Some authors to fix
    bad_authors = Author.objects.filter(address="Nowhere")

    # Before: bad, we can't fit all these in memory
    for author in bad_authors.all():
        pass

    # After: good, takes small dynamically adjusted slices, wraps in atomic()
    for author in bad_authors.iter_smart():
        author.address = ""
        author.save()
        author.send_apology_email()

:ref:`Read more <smart-iteration>`


Integration with pt-visual-explain
----------------------------------

For interactive debugging of queries, this captures the query that the
``QuerySet`` represents, and passes it through ``EXPLAIN`` and
``pt-visual-explain`` to get a visual representation of the query plan::

    >>> Author.objects.all().pt_visual_explain()
    Table scan
    rows           1020
    +- Table
       table          myapp_author

:ref:`Read more <pt-visual-explain>`


MySQL ``HANDLER`` API
---------------------

MySQL's ``HANDLER`` commands give simple NoSQL-style read access to rows faster
than normal SQL queries, with the ability to perform index lookups or
page-by-page scans. This extension adds an ORM-based API for handlers::

    with Author.objects.handler() as handler:
        for author in handler.iter(chunk_size=1000):
            author.send_apology_email()

:ref:`Read more <handler>`


------------
Model Fields
------------

Fields that use MySQL-specific features!

Dynamic Columns Field
---------------------

Use MariaDB's Dynamic Columns for storing arbitrary, nested dictionaries of
values::

    class ShopItem(Model):
        name = models.CharField(max_length=200)
        attrs = DynamicField()

..

    >>> ShopItem.objects.create(name='Camembert', {'smelliness': 15})
    >>> ShopItem.objects.create(name='Brie', {'smelliness': 5, 'squishiness': 10})
    >>> ShopItem.objects.filter(attrs__smelliness_INTEGER__gte=10)
    [<ShopItem: Camembert>]

:ref:`Read more <dynamic-columns-field>`

List Fields
-----------

Two field classes that allow you to store lists of items in a comma-separated
string::

    class Person(Model):
        name = CharField(max_length=32)
        post_nominals = ListTextField(
            base_field=CharField(max_length=32)
        )

..

    >>> Person.objects.filter(post_nominals__contains='PhD')
    [<Person: Horatio>, <Person: Severus>]

:ref:`Read more <list-fields>`


Set Fields
----------

Two field classes that allow you to store sets of items in a comma-separated
string::

    class Post(Model):
        name = CharField(max_length=32)
        tags = SetTextField(
            base_field=CharField(max_length=10)
        )

..

    >>> Post.objects.create(name='First post', tags={'thoughts', 'django'})
    >>> Post.objects.filter(tags__contains='django')
    [<Post: First post>]

:ref:`Read more <set-fields>`

Enum Fields
-----------

You can take advantage of MySQL's ``ENUM`` type through the ``EnumField``
provided by django-mysql. Using ``ENUM`` provides the benefit of storing
recurring strings in a very space efficient manner.

    class BookCover(Model):
        color = EnumField(choices=['red', 'green', 'blue'])

:ref:`Read more <enum-fields>`


Resizable Text/Binary Fields
----------------------------

Django's :class:`~django.db.models.TextField` and
:class:`~django.db.models.BinaryField` fields are fixed at the MySQL level to
use the maximum size class for the ``BLOB`` and ``TEXT`` data types - these
fields allow you to use the other sizes, and migrate between them::

    class BookBlurb(Model):
        blurb = SizedTextField(size_class=3)
        # Has a maximum length of 16MiB, compared to plain TextField which has
        # a limit of 4GB (!)

:ref:`Read more <resizable-blob-text-fields>`


BIT(1) Boolean Fields
---------------------

Some database systems, such as the Java Hibernate ORM, don't use MySQL's
``bool`` data type for storing boolean flags and instead use ``BIT(1)``. This
field class allows you to interact with those fields::

    class HibernateModel(Model):
        some_bool = Bit1BooleanField()
        some_nullable_bool = NullBit1BooleanField()

:ref:`Read more <bit1booleanfields>`

-------------
Field Lookups
-------------

ORM extensions to built-in fields::

    >>> Author.objects.filter(name__sounds_like='Robert')
    [<Author: Robert>, <Author: Rupert>]

:ref:`Read more <field-lookups>`


----------
Aggregates
----------

MySQL's powerful ``GROUP_CONCAT`` statement is added as an aggregate, allowing
you to bring back the concatenation of values from a group in one query::

    >>> author = Author.objects.annotate(
    ...     book_ids=GroupConcat('books__id')
    ... ).get(name="William Shakespeare")
    >>> author.book_ids
    "1,2,5,17,29"

:ref:`Read more <aggregates>`


------------------
Database Functions
------------------

MySQL-specific database functions for the ORM::

    >>> Author.objects.annotate(
    ...     full_name=ConcatWS('first_name', 'last_name', separator=' ')
    ... ).first().full_name
    "Charles Dickens"

:ref:`Read more <database_functions>`


--------------------
Migration Operations
--------------------

MySQL-specific operations for django migrations::

    from django.db import migrations
    from django_mysql.operations import InstallPlugin


    class Migration(migrations.Migration):
        dependencies = []

        operations = [
            InstallPlugin("metadata_lock_info", "metadata_lock_info.so")
        ]

:ref:`Read more <migration_operations>`

-----
Cache
-----

An efficient backend for Django's cache framework using MySQL features::

    cache.set("my_key", "my_value")  # Uses only one query
    cache.get_many(["key1", "key2"])  # Only one query to do this too!
    cache.set("another_key", some_big_value)  # Compressed above 5kb by default

:ref:`Read more <cache>`


-----
Locks
-----

Use MySQL as a locking server for arbitrarily named locks::

    with Lock("ExternalAPI", timeout=10.0):
        do_some_external_api_stuff()

:ref:`Read more <locks>`


------
Status
------

Easy access to global or session status variables::

    if global_status.get('Threads_running') > 100:
        raise BorkError("Server too busy right now, come back later")

:ref:`Read more <status>`


-------------------
Management Commands
-------------------

Easy inclusion of your database parameters from settings in commandline tools::

.. code-block:: console

    $ mysqldump $(python manage.py dbparams) > dump.sql

:ref:`Read more <management_commands>`


---------
Utilities
---------

Fingerprint queries quickly with the ``pt-fingerprint`` wrapper::

    >>> pt_fingerprint("SELECT * FROM myapp_author WHERE id = 5")
    "select * from myapp_author where id = 5"

:ref:`Read more <utilities>`


--------------
Test Utilities
--------------

Set some MySQL server variables on a test case for every method or just a
specific one::

    class MyTests(TestCase):

        @override_mysql_variables(SQL_MODE="ANSI")
        def test_it_works_in_ansi_mode(self):
            self.run_it()

:ref:`Read more <test_utilities>`


--------------
Monkey Patches
--------------

You can test to see if you are running MariaDB from the
``djagno.db.connection`` object::

    >>> from django.db import connections
    >>> connections['default'].is_mariadb
    False

:ref:`Read more <monkey_patches>`
