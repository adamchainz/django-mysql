Exposition
==========

Every feature in whistle-stop detail.

-------------------
QuerySet Extensions
-------------------

Django-MySQL comes with a number of extensions to QuerySets that can be
installed in a number of ways - e.g. adding the ``QuerySetMixin`` to your
existing ``QuerySet`` subclass. They perform different utilities.


Approximate Counting
--------------------

``SELECT COUNT(*) ...`` can become a slow query since it requires a scan of all
data - so we provide a way to access the approximation of the count that MySQL
knows. You can call it directly::

    Author.objects.count()

Or if you have pre-existing code that calls ``count()`` later, e.g. the Django
Admin, you can set the ``QuerySet`` to do this automatically::

    qs = Author.objects.all().count_tries_approx()
    # Now calling qs.count() will try approx_count() first


'Smart' Iteration
-----------------

Sometimes you need to modify every single instance of a model in your big
database, and without creating any long running queries. The 'smart' iterators
fetch the specified rows by slicing the ``QuerySet`` up into primary-key-ranged
slices which traverse the table, whilst dynamically adjusting the slice size::

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


pt-visual-explain
-----------------

For interactive use - capture the query this ``QuerySet`` represents, and give
its ``EXPLAIN`` to ``pt-visual-explain`` to see what the query plan is::

    >>> Author.objects.all().pt_visual_explain()
    Table scan
    rows           1020
    +- Table
       table          myapp_author


-----
Locks
-----

A little-known MySQL feature, this allows you to lock an arbitrary string to
prevent concurrent access to some resource::

    with Lock("ExternalAPI", timeout=10.0):
        do_some_external_api_stuff()


------
Status
------

Do you know what your server is doing, or what your code is doing to it? Quick
programmatic access to global or session status variables::

    status = GlobalStatus()
    if status.get('Threads_running') > 100:
        raise BorkError("Server too busy right now, come back later")
