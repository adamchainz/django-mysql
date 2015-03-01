======
Models
======

MySQL-specific Model and QuerySet extensions. These classes can be imported
from the ``django_mysql.models`` module.

.. currentmodule:: django_mysql.models

Adding the Extensions
=====================

There are several ways of adding the extensions to your models, and dependent
on your project and other extensions you are adding to your models, you may
need to choose from the below. The simplest is to use the ``Model`` class.

.. class:: Model

    A fully compatible subclass of Django's ``models.Model`` that provides
    MySQL specific extensions. At current this only sets ``objects`` to
    ``QuerySet.as_manager()`` with the below ``QuerySet`` class, providing the
    queryset extensions. Make all your models inherit from this to get the
    goodness!::

        # from django.db.models import Model - no more!
        from django_mysql.models import Model

        class MySuperModel(Model):
            pass  # TODO: come up with startup idea.


.. class:: QuerySet

    A fully compatible subclass of Django's :class:`~django.db.models.QuerySet`
    that provides MySQL-specific extensions by mixing in the below
    ``QuerySetMixin``. Contains all the methods described under 'QuerySet
    Extensions'.

    If you can't use the above ``Model`` class, this is another way of getting
    the extra methods by setting ``objects``::

        from mythings import MyBaseModel
        from django_mysql.models import QuerySet

        class MySuperDuperModel(MyBaseModel):
            objects = QuerySet.as_manager()
            # TODO: what fields should this model have??


.. class:: QuerySetMixin

    A mixin to be applied to ``QuerySet`` classes to add MySQL-specific
    behaviour. Contains all the methods described under 'QuerySet Extensions'.

    Mix in to your custom queryset to get the goodness::

        from django.db.models import Model
        from django_mysql.models import QuerySetMixin
        from stackoverflow import CopyPasteQuerySet

        class MySplendidQuerySet(QuerySetMixin, CopyPasteQuerySet):
            pass

        class MySplendidModel(Model):
            objects = MySplendidQuerySet.as_manager()
            # TODO: profit


QuerySet Extensions
===================

If you've installed ``QuerySetMixin`` onto your model via one of the above
routes then all of these are available to you! They're organized in sections
to make them a bit easier to understand.

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
    applications it is closer, and is good enough. For example, the admin pages
    paginate all objects in a model, and if you have a lot of pages you don't
    need always need an absolute count (more in a second on how to install it
    on the admin).

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

    There are a lot of arguments and the defaults have been picked hopefully
    sensibly, but please check for your case

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
