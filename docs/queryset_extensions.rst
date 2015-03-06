QuerySet Extensions
===================

MySQL-specific Model and QuerySet extensions. To add these to your
``Model``/``Manager``/``QuerySet`` trifecta, see :doc:`installation`. Methods
below are all ``QuerySet`` methods; where standalone forms are referred to,
they can be imported from ``django_mysql.models``.

.. currentmodule:: django_mysql.models

.. _approximate-counting:

Approximate Counting
--------------------

.. method:: approx_count(fall_back=True, \
                         return_approx_int=True, \
                         min_size=1000)

    By default a QuerySet's `count()` method runs `SELECT COUNT(*)` on a table.
    Whilst this is fast for ``MyISAM`` tables, for ``InnoDB`` it involves a
    full table scan to produce a consistent number, due to MVCC keeping several
    copies of rows when under transaction. If you have lots of rows, you will
    notice this as a slow query - `percona have some more details
    <http://www.percona.com/blog/2006/12/01/count-for-innodb-tables/>`_.

    This method returns the approximate count found by running ``EXPLAIN SELECT
    COUNT(*) ...``. It can be out by 30-50% in the worst case, but in many
    applications it is closer, and is good enough, such as when presenting many
    pages of results but users will only practically scroll through the first
    few. For example::

        Author.objects.count()  # slow
        Author.objects.approx_count()  # fast, with some error

    Three arguments are taken:

    .. attribute:: fall_back=True

        If ``True`` and the approximate count cannot be calculated, ``count()``
        will be called and returned instead, otherwise ``ValueError`` will be
        raised.

        The approximation can only be found for ``objects.all()``, with no
        filters, ``distinct()`` calls, etc., so it's reasonable to fall back.

    .. attribute:: return_approx_int=True

        When ``True``, an ``int`` is not returned (excpet when falling back),
        but instead a subclass called ``ApproximateInt``. This is for all
        intents and purposes an ``int``, apart from when cast to ``str``, it
        renders as e.g. **'Approximately 12345'** (internationalization
        included). Useful for templates you can't edit (e.g. the admin) and you
        want to communicate that the number is not 100% accurate.

    .. attribute:: min_size=1000

        The threshold at which to use the approximate algorithm; if the
        approximate count comes back as less that this number, ``count()`` will
        be called and returned instead, since it should be so small as to not
        bother your database. Set to ``0`` to disable this behaviour and always
        return the approximation.

        The default of ``1000`` is a bit pessimistic - most tables won't take
        long when calling ``COUNT(*)`` on tens of thousands of rows, but it
        *could* be slow for very wide tables.

.. method:: count_tries_approx(activate=False, \
                               fall_back=True, \
                               return_approx_int=True, \
                               min_size=1000)

        This is the 'magic' method to make pre-existing code, such as Django's
        admin, work with ``approx_count``. Calling ``count_tries_approx`` sets
        the QuerySet up such that then calling ``count`` will call
        ``approx_count`` instead, with the given arguments.

        To unset this, call ``count_tries_approx`` with ``activate=False``.

        To 'fix' an Admin class with this, simply do the following (assuming
        ``Author`` inherits from ``django_mysql``'s ``Model``)::

            class AuthorAdmin(ModelAdmin):

                def get_queryset(self, request):
                    qs = super(AuthorAdmin, self).get_queryset(request)
                    return qs.count_tries_approx()

        You'll be able to see this is working on the pagination due to the word
        **'Approximately'** appearing:

        .. figure::  images/approx_count_admin.png
           :align:   center

        You can do this at a base class for all your ``ModelAdmin`` subclasses
        to apply the magical speed increase across your admin interface.


.. _smart-iteration:

'Smart' Iteration
-----------------

Here's a situation we've all been in - we screwed up,
and now we need to fix the data. Let's say we accidentally set the address of all
authors without an address to "Nowhere", rather than the blank string. How can
we fix them??

The simplest way would be to run the following::

    Author.objects.filter(address="Nowhere").update(address="")

Unfortunately with a lot of rows ('a lot' being dependent on your database
server and level of traffic) this will stall other access to the table, since
it will require MySQL to read all the rows and to hold write locks on them in
a single query.

To solve this, we could try updating a chunk of authors at a time; such code
tends to get ugly/complicated pretty quickly::

    min_id = 0
    max_id = 1000
    biggest_author_id = Author.objects.order_by('-id')[0].id
    while True:
        Author.objects.filter(id__gte=min_id, id__lte=BLA BLA BLA

    # I'm not even going to type this all out, it's so much code

Here's the solution to this boilerplate with added safety features - 'smart'
iteration! There are two classes; one yields chunks of the given ``QuerySet``,
and the other yields the objects inside those chunks. Nearly every data update
can be thought of in one of these two methods.

.. class:: SmartChunkedIterator(queryset, atomically=True, \
                                status_thresholds=None, chunk_time=0.5, \
                                chunk_max=10000, report_progress=False, \
                                total=None)

    Implements a smart iteration strategy over the given ``queryset``. There is
    a method ``iter_smart_chunks`` that takes the same arguments on the
    ``QuerySetMixin`` so you can just:

        bad_authors = Author.objects.filter(address="Nowhere")
        for author_chunk in bad_authors.iter_smart_chunks():
            author_chunk.update(address="")

    Iteration proceeds by yielding primary-key based slices of the queryset,
    and dynamically adjusting the size of the chunk to try and take
    ``chunk_time`` seconds. In between chunks, the
    :func:`~django_mysql.status.GlobalStatus.wait_until_load_low` method of
    :class:`~django_mysql.status.GlobalStatus` is called to ensure the database
    is not under high load.

    .. warning::

        Because of the slicing by primary key, there are restrictions on what
        ``QuerySet``\s you can use, and a ``ValueError`` will be raised if the
        queryset doesn't meet that. Specifically, only ``QuerySet``\s on models
        with integer-based primary keys, which are unsliced, and have no
        ``order_by`` will work.

    There are a lot of arguments and the defaults have been picked hopefully
    sensibly, but please check for your case though!

    .. attribute:: queryset

        The queryset to iterate over; if you're calling via
        ``.iter_smart_chunks`` then you don't need to set this since it's the
        queryset you called it on.

    .. attribute:: atomically=True

        If true, wraps each chunk in a transaction via django's
        :func:`transaction.atomic() <django:django.db.transaction.atomic>`.
        Recommended for any write processing.

    .. attribute:: status_thresholds=None

        A dict of status variables and their maximum tolerated values to be
        checked against after each chunk with
        :func:`~django_mysql.status.GlobalStatus.wait_until_load_low`.

        When set to ``None``, it lets
        :class:`~django_mysql.status.GlobalStatus` use its default of
        ``'Threads_running': 5}``. Set to an empty dict to disable status
        checking (not really recommended, it doesn't add much overhead and can
        will probably save your butt one day).

    .. attribute:: chunk_time=0.5

        The time in seconds to aim for each chunk to take. The chunk size is
        dynamically adjusted to try and match this time, via a weighted average
        of the past and current speed of processing. The default and algorithm
        is taken from the analogous ``pt-online-schema-change`` flag
        `--chunk-time <http://www.percona.com/doc/percona-toolkit/2.1/pt-online-schema-change.html#cmdoption-pt-online-schema-change--chunk-time>`_.


    .. attribute:: chunk_max=100000

        The maximum number of objects in a chunk, a kind of sanity bound. Acts
        to prevent harm in the case of iterating over a model with a large
        'hole' in its primary key values, e.g. if only ids 1-10k and 100k-110k
        exist, then the chunk 'slices' could grow very large in between 10k and
        100k since you'd be "processing" the non-existent objects 10k-100k very
        quickly.


    .. attribute:: report_progress=False

        If set to true, display out a running counter and summary on
        ``sys.stdout``. Useful for interactive use. The message looks like
        this::

            AuthorSmartChunkedIterator processed 0/100000 objects (0.00%) in 0 chunks

        And uses ``\r`` to erase itself when re-printing to avoid spamming your
        screen.  At the end ``Finished!`` is printed on a new line.

    .. attribute:: total=None

        By default the total number of objects to process will be calculated
        with :func:`~django_mysql.models.QuerySetMixin.approx_count`, with
        ``fall_back`` set to ``True``. This ``count()`` query could potentially
        be big and slow.

        ``total`` allows you to pass in the total number of objects for
        processing, if you can calculate in a cheaper way, for example if you
        have a read-replica to use.


.. class:: SmartIterator

    A convenience subclass of ``SmartChunkedIterator`` that simply unpacks the
    chunks for you. Can be accessed via the ``iter_smart`` method of
    ``QuerySetMixin``. For example, rather than doing this::

        bad_authors = Author.objects.filter(address="Nowhere")
        for authors_chunk in bad_authors.iter_smart_chunks():
            for author in authors_chunk:
                author.send_apology_email()

    You can do this::

        bad_authors = Author.objects.filter(address="Nowhere")
        for author in bad_authors.iter_smart():
            author.send_apology_email()

    All the same arguments are accepted.


.. _pt-visual-explain:

Integration with pt-visual-explain
----------------------------------

How does MySQL *really* execute a query? The ``EXPLAIN`` statement
(docs: `MySQL<http://dev.mysql.com/doc/refman/5.6/en/explain.html>`_ /
`MariaDB <https://mariadb.com/kb/en/mariadb/explain/>`_),
gives a description of the execution plan, and the ``pt-visual-explain``
`tool <http://www.percona.com/doc/percona-toolkit/2.2/pt-visual-explain.html>`_
can format this in an understandable tree.

Here's a shortcut to turn a ``QuerySet`` into its visual explanation, making it
easy to gain an understanding of what your queries do.

.. method:: pt_visual_explain(display=True)

    Call on a queryset to print its visual explanation, or with
    ``display=False`` to return it as a string. Executes the query, captures
    the SQL, then gets the visual explanation via a subprocess pipeline with
    `mysql` and `pt-visual-explain`. You therefore need the MySQL client and
    Percona Toolkit installed where you run this.

    Example::

        >>> Author.objects.all().pt_visual_explain()
        Table scan
        rows           1020
        +- Table
           table          myapp_author

    Also importable as a standalone function if you can't use the
    ``QuerySetMixin`` or you need it on a model you can't touch::

        >>> from django_mysql.models import pt_visual_explain
        >>> pt_visual_explain(User.objects.all())
        Table scan
        rows           1
        +- Table
           table          auth_user
