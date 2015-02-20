======
Models
======

.. currentmodule:: django_mysql.models

MySQL-specific Model and QuerySet extensions. These classes can be imported
from the ``django_mysql.models`` module.

.. class:: Model

    A fully compatible subclass of Django's ``models.Model`` that provides
    MySQL specific extensions. At current this only sets ``objects`` to
    ``QuerySet.as_manager()`` with the below ``QuerySet`` class. Make all
    your models inherit from this to get the goodness!::

        # from django.db.models import Model - no more!
        from django_mysql.models import Model

        class MySuperModel(Model):
            pass  # TODO: come up with startup idea.


.. class:: QuerySet

    A fully compatible subclass of Django's ``models.QuerySet`` that provides
    MySQL-specific extensions. Mixes the below ``QuerySetMixin`` into Django's
    ``models.QuerySet`` - therefore contains all the below methods.

    If you can't use the above ``Model`` class, you can add the methods using::

        from mythings import MyModel
        from django_mysql.models import QuerySet

        class MySuperDuperModel(MyModel):
            objects = QuerySet.as_manager()
            # TODO: what fields should this model have??


.. class:: QuerySetMixin

    A mixin to be applied to ``QuerySet`` classes to add MySQL-specific
    behaviour. Supplies the below methods:

    .. method:: approx_count(fall_back=True, \
                             return_approx_int=True, \
                             min_size=1000)

        By default a QuerySet's `count()` method runs `SELECT COUNT(*)` on a
        table. Whilst this is fast for ``MyISAM`` tables, for ``InnoDB`` it
        involves a full table scan to produce a consistent number, due to
        MVCC for transactions. If you have lots of rows, you will notice this
        as a slow query.

        This method returns the approximate count found by running ``EXPLAIN
        SELECT COUNT(*) ...``. It can be out by 30-50% in the worst case, but
        in many applications it is closer, and is good enough. For example,
        the admin pages paginate all objects in a model, and if you have a lot
        of pages you don't need always need an absolute count (more in a second
        on how to install it on the admin).

        Three arguments are taken:

        .. attribute:: fall_back=True

            If ``True``, ``count()`` will be called and returned if the
            approximate count cannot be found, otherwise ``ValueError`` will be
            raised.

            The approximation can only be found for ``objects.all()``, with no
            filters, ``distinct()`` calls, etc., so it's reasonable to fall
            back.

        .. attribute:: return_approx_int=True

            When ``True``, an ``int`` is not returned (when not falling back),
            but instead a subclass called ``ApproximateInt``. This is for all
            intents and purposes an ``int``, apart from when cast to ``str``,
            it renders as e.g. **'Approximately 12345'**. Useful for templates
            you can't edit (e.g. the admin) where you must communicate the
            number is not 100% accurate.

        .. attribute:: min_size=1000

            A threshold number at which the approximate count is returned. If
            the approximate count is less that this number, ``count()`` will be
            returned instead, since it should be so small as to not bother your
            database. Set to ``0`` to disable this behaviour and always return
            an approximation.

            The default of ``1000`` is a bit pessimistic; most tables won't
            take long when calling ``COUNT(*)`` on tens of thosuands of rows,
            but it could for very wide tables (lots of long fields), and we
            want this to 'just work' everywhere.

    .. method:: count_tries_approx(activate=False, \
                                   fall_back=True, \
                                   return_approx_int=True, \
                                   min_size=1000)

            This is the magic method to make pre-existing code, such as
            Django's admin, work with ``approx_count``. Calling
            ``count_tries_approx`` sets the QuerySet up such that then calling
            ``count`` will call ``approx_count`` instead, with the given
            arguments.

            To unset this, call ``count_tries_approx`` with ``activate=False``.
            All the other arguments are passed to ``approx_count`` later.

            To 'fix' an Admin class with this, simply do the following
            (assuming ``Author`` inherits from ``django_mysql``'s ``Model``)::

                class AuthorAdmin(ModelAdmin):

                    def get_queryset(self, request):
                        qs = super(AuthorAdmin, self).get_queryset(request)
                        return qs.count_tries_approx()

            You'll be able to see this is working on the pagination due to
            the word **'Approximately'** appearing:

            .. figure::  images/approx_count_admin.png
               :align:   center

            You can do this at a base class for all your ``ModelAdmin``
            subclasses to apply the magical speed increase across your admin
            interface.
