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

        >>> Author.objects.count()  # slow
        509741
        >>> Author.objects.approx_count()  # fast, with some error
        531140

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
        ready). Useful for templates you can't edit (e.g. the admin) and you
        want to communicate that the number is not 100% accurate. For example::

            >>> print(Author.objects.approx_count())  # ApproximateInt
            Approximately 531140
            >>> print(Author.objects.approx_count() + 0)  # plain int
            531140
            >>> print(Author.objects.approx_count(return_approx_int=False))  # plain int
            531140

    .. attribute:: min_size=1000

        The threshold at which to use the approximate algorithm; if the
        approximate count comes back as less that this number, ``count()`` will
        be called and returned instead, since it should be so small as to not
        bother your database. Set to ``0`` to disable this behaviour and always
        return the approximation.

        The default of ``1000`` is a bit pessimistic - most tables won't take
        long when calling ``COUNT(*)`` on tens of thousands of rows, but it
        *could* be slow for very wide tables.

.. method:: count_tries_approx(activate=True, fall_back=True, \
                               return_approx_int=True, min_size=1000)

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
                                status_thresholds=None, pk_range=None, \
                                chunk_time=0.5, chunk_max=10000, \
                                report_progress=False, total=None)

    Implements a smart iteration strategy over the given ``queryset``. There is
    a method ``iter_smart_chunks`` that takes the same arguments on the
    ``QuerySetMixin`` so you can just::

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

    .. attribute:: pk_range=None

        Controls the primary key range to iterate over with slices. By default, with
        ``pk_range=None``, the QuerySet will be searched for its minimum and
        maximum ``pk`` values before starting. On QuerySets that match few
        rows, or whose rows aren't evenly distributed, this can still execute a
        long blocking table scan to find these two rows.
        You can remedy this by givnig a value for ``pk_range``:

        * If set to ``'all'``, the range will be the minimum and maximum PK
          values of the entire table, excluding any filters you have set up -
          that is, for ``Model.objects.all()`` for the given ``QuerySet``'s
          model.

        * If set to a 2-tuple, it will be unpacked and used as the minimum and
          maxmimum values respectively.

        .. note::

            The iterator determines the minimum and maximum at the start of
            iteration and does not update them whilst iterating, which is
            normally a safe assumption, since if you're "fixing things" you
            probably aren't creating any more bad data. If you do need to
            process *every* row then set ``pk_range`` to have a maximum far
            greater than what you expect would be reached by inserts that occur
            during iteration.

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
(docs: `MySQL <http://dev.mysql.com/doc/refman/5.6/en/explain.html>`_ /
`MariaDB <https://mariadb.com/kb/en/mariadb/explain/>`_),
gives a description of the execution plan, and the ``pt-visual-explain``
`tool <http://www.percona.com/doc/percona-toolkit/2.2/pt-visual-explain.html>`_
can format this in an understandable tree.

This function is a shortcut to turn a ``QuerySet`` into its visual explanation,
making it easy to gain a better understanding of what your queries really end
up doing.

.. method:: pt_visual_explain(display=True)

    Call on a ``QuerySet`` to print its visual explanation, or with
    ``display=False`` to return it as a string. It prepends the SQL of the
    query with 'EXPLAIN' and passes it through the ``mysql`` and
    ``pt-visual-explain`` commands to get the output. You therefore need the
    MySQL client and Percona Toolkit installed where you run this.

    Example::

        >>> Author.objects.all().pt_visual_explain()
        Table scan
        rows           1020
        +- Table
           table          myapp_author

    Can also be imported as a standalone function if you want to use it on a
    ``QuerySet`` that does not have the ``QuerySetMixin`` added, e.g. for
    built-in django models::

        >>> from django_mysql.models import pt_visual_explain
        >>> pt_visual_explain(User.objects.all())
        Table scan
        rows           1
        +- Table
           table          auth_user


.. _handler:

Handler
-------

.. currentmodule:: django_mysql.models.handler

MySQL's ``HANDLER`` commands give you simple NoSQL-style read access, faster
than full SQL queries, with the ability to perform index lookups or paginated
scans (docs:
`MySQL <http://dev.mysql.com/doc/refman/5.6/en/handler.html>`_ /
`MariaDB <https://mariadb.com/kb/en/mariadb/handler-commands/>`_).

This extension adds an ORM-based API for handlers. You can instantiate them
from a ``QuerySet`` (and thus from `.objects`), and open/close them as context
managers::

    with Author.objects.handler() as handler:

        first_author_by_pk = handler.read()

        first_ten_authors_by_pk = handler.read(limit=10)

        for author in handler.iter(chunk_size=1000):
            author.send_apology_email()


The ``.handler()`` method simply returns a ``Handler`` instance; the class can
be imported and applied to ``QuerySet``\s from models without the extensions
easily as well::

    from django_mysql.models.handler import Handler

    with Handler(User.objects.all()) as handler:

        for user in handler.iter(chunk_size=1000):
            user.send_notification_email()

.. warning::

    ``HANDLER`` is lower level than ``SELECT``, and has some optimizations
    that mean it permits 'for example' **dirty reads**. Check the database
    documentation and understand the consequences of this before you replace
    any SQL queries!


.. class:: Handler(queryset)

    Implements a handler for the given queryset's model. The ``WHERE`` clause
    and query parameters, if they exist, will be extracted from the queryset's
    SQL. Since ``HANDLER`` statements can only operate on one table at a time,
    only relatively simple querysets can be used - others will result in a
    ``ValueError`` being raised.

    A ``Handler`` is only opened and available for reads when used as a context
    manager. You may have multiple handlers open at once, even on the same
    table, but you cannot open the same one twice.

    .. method:: read(index='PRIMARY', value__LOOKUP=None, mode=None, \
                     where=None, limit=None)

        Returns the result of a ``HANDLER .. READ`` statement as a
        :class:`~django.db.models.RawQuerySet` for the given ``queryset``'s
        model (which, like all ``QuerySet``\s, is lazy).

        .. note::
            The ``HANDLER`` statements must select whole rows, therefore there
            is no way of optimizing by returning only certain columns (like
            ``QuerySet``'s :meth:`~django.db.models.query.QuerySet.only()`).

        MySQL has three forms of ``HANDLER .. READ`` statements, but only the
        **first two forms** of ``HANDLER .. READ`` statements are supported -
        you can specify index lookups, or pagination. The third form, 'natural
        row order', only makes sense for MyISAM tables.

        .. attribute:: index='PRIMARY'

            The name of the index of the table to read, defaulting to the
            primary key. You must provide the index name as known by MySQL, not
            the names of the indexed column[s] as Django's ``db_index`` and
            ``index_together`` let you specify. This will only be checked by
            MySQL so an ``OperationalError`` will be raised if you specify a
            wrong name.

            Both single and multi-column indexes are supported.

        .. attribute:: value__LOOKUP=None

            The 'first form' of ``HANDLER .. READ`` supports index lookups.
            ``value__LOOKUP`` allows you to specify a lookup on ``index`` using
            the same style as Django's ORM, and is mutually exclusive with
            ``mode``. You may only have one index lookup on a ``read`` - other
            conditions must be filtered with ``where``. For example::

                # Read objects with primary key <= 100
                handler.read(value__lte=100, limit=100)

            The valid lookups are:

                * ``value__lt=x`` - index value ``<`` x
                * ``value__lte=x`` - index value ``<=`` x
                * ``value=x``, ``value__exact=x`` - index value ``=`` x
                * ``value__gte=x`` - index value ``>=`` x
                * ``value__gt=x`` - index value ``>`` x

            For single-column indexes, specify the value; for multi-column
            indexes, specify the tuple of values. For example::

                grisham = handler.read(index='full_name_idx',
                                       value=('John', 'Grisham'))

        .. attribute:: mode=None

            The 'second form' of ``HANDLER .. READ`` supports paging over a
            table, fetching one batch of results at a time whilst the handler
            object on MySQL's end retains state, somewhat like a 'cursor'. This
            is mututally exclusive with ``value__LOOKUP``, and if neither is
            specified, this is the default.

            There are four modes::

                * ``first`` - commence iteration at the start
                * ``next`` - continue ascending/go forward one page
                * ``last`` - commence iteration at the end (in reverse)
                * ``prev`` - continue descending/go backward one page

            To iterate forwards, use ``'first'`` and then
            repeatedly ``'next'``. To iterate backwards, use ``'last'`` and
            then repeatedly ``'prev'``. The page size is set with ``limit``.

            N.B. the below ``iter`` method below is recommended for most
            iteration.

        .. attribute:: where=None

            ``HANDLER .. READ`` statements support ``WHERE`` clauses for
            columns on the same table, which apply after the index filtering.
            By default the ``WHERE`` clause from the ``queryset`` used to
            construct the ``Handler`` will be applied. Passing a different
            ``QuerySet`` as ``where`` allows you to read with different
            filters. For example::

                with Author.objects.handler() as handler:

                    old = Author.objects.filter(age__gte=50) first_old_author =
                    handler.read(where=old)[0]

                    young = Author.objects.filter(age__lte=50)
                    first_young_author = handler.read(where=young)[0]

        .. attribute:: limit=None

            By default every ``HANDLER .. READ`` statement returns *only* the
            first row. Specify ``limit`` to retrieve a different number of
            rows.

    .. method:: iter(index='PRIMARY', where=None, chunk_size=100, \
                     reverse=False)

        Iterate over a table via the named index, one chunk at a time, yielding
        the individual objects. Acts as a wrapper around repeated calls to
        ``read``.

        .. attribute:: index='PRIMARY'

            The name of the index to iterate over. As detailed above, this must
            be the index name on MySQL.

        .. attribute:: where=None

            A ``QuerySet`` for filter conditions, the same as ``read``'s
            ``where`` argument, as detailed above.

        .. attribute:: chunk_size=100

            The size of the chunks to read during iteration.

        .. attribute:: reverse=False

            The direction of iteration over the index. By default set to
            ``True``, the index will be iterated in ascending order; set to
            ``False``, the index will be iterated in descending order.

            Sets ``mode`` on ``read`` to either ``FIRST`` then repeatedly
            ``NEXT`` or ``LAST`` then repeatedly ``PREV`` respectively.

            .. warning::

                You can only have one iteration happening at a time per
                ``Handler``, otherwise on the MySQL side it loses its position.
                There is no checking for this in ``Handler`` class.
