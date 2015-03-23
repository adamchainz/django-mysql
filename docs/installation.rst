=============================
Requirements and Installation
=============================

Requirements
------------

Tested with:

* Python: 2.7, 3.3, 3.4
* Django: 1.7, 1.8 RC
* MySQL: 5.5, 5.6 / MariaDB: 5.5, 10.0, 10.1
* mysqlclient: 1.3.5 (Python 3 compatible version of ``MySQL-python``)

Any combination of these should be good, and also ``MySQL-python`` should work
since it's just an older version of ``mysqlclient``.


Installation
------------

At the command line::

    $ pip install django-mysql

Or add it to your project's ``requirements.txt``.

...or if you're really still using it::

    $ easy_install django-mysql

Add ``'django_mysql'`` to your ``INSTALLED_APPS`` setting::

    INSTALLED_APPS = (
        ...
        'django_mysql',
    )


Extending your QuerySets
------------------------

Half the fun features are extensions to ``QuerySet``. You can add these to your
project in a number of ways, depending on what is easiest for your code - all
imported from ``django_mysql.models``.

.. class:: Model

    The simplest way to add the ``QuerySet`` extensions - this is a subclass of
    Django's :class:`~django.db.models.Model` that sets ``objects`` to use the
    Django-MySQL extended ``QuerySet`` (below) via ``QuerySet.as_manager()``.
    Simply change your model base to get the goodness::

        # from django.db.models import Model - no more!
        from django_mysql.models import Model

        class MySuperModel(Model):
            pass  # TODO: come up with startup idea.


.. class:: QuerySet

    The second way to add the extensions - use this to replace your model's
    default manager::

        from mythings import MyBaseModel
        from django_mysql.models import QuerySet

        class MySuperDuperModel(MyBaseModel):
            objects = QuerySet.as_manager()
            # TODO: what fields should this model have??


.. class:: QuerySetMixin

    The final way to add the extensions, and the container class for the
    extensions.  Add this mixin to your custom ``QuerySet`` class to add in all
    the fun::

        from django.db.models import Model
        from django_mysql.models import QuerySetMixin
        from stackoverflow import CopyPasteQuerySet

        class MySplendidQuerySet(QuerySetMixin, CopyPasteQuerySet):
            pass

        class MySplendidModel(Model):
            objects = MySplendidQuerySet.as_manager()
            # TODO: profit


The extensions are described in :doc:`queryset_extensions`.
