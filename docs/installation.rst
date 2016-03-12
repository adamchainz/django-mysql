=============================
Requirements and Installation
=============================

Requirements
------------

Tested with all combinations of:

* Python: 2.7, 3.4, 3.5
* Django: 1.7, 1.8, 1.9, master
* MySQL: 5.5, 5.6, 5.7 / MariaDB: 5.5, 10.0, 10.1
* mysqlclient: 1.3.7 (Python 3 compatible version of ``MySQL-python``)

Any combination of these should be good, and also ``MySQL-python`` should work
since it's just an older version of ``mysqlclient``.


Installation
------------

Install it with **pip**:

.. code-block:: console

    $ pip install django-mysql

Or add it to your project's ``requirements.txt``.

Add ``'django_mysql'`` to your ``INSTALLED_APPS`` setting:

.. code-block:: python

    INSTALLED_APPS = (
        ...
        'django_mysql',
    )

Django-MySQL comes with some extra checks to ensure your configuration for
Django + MySQL is optimal. It's best to run these now you've installed to see
if there is anything to fix:

.. code-block:: console

    $ ./manage.py check

For help fixing any warnings, see :doc:`checks`.


Extending your QuerySets
------------------------

Half the fun features are extensions to ``QuerySet``. You can add these to your
project in a number of ways, depending on what is easiest for your code - all
imported from ``django_mysql.models``.

.. class:: Model

    The simplest way to add the ``QuerySet`` extensions - this is a subclass of
    Django's :class:`~django.db.models.Model` that sets ``objects`` to use the
    Django-MySQL extended ``QuerySet`` (below) via ``QuerySet.as_manager()``.
    Simply change your model base to get the goodness:

    .. code-block:: python

        # from django.db.models import Model - no more!
        from django_mysql.models import Model

        class MySuperModel(Model):
            pass  # TODO: come up with startup idea.


.. class:: QuerySet

    The second way to add the extensions - use this to replace your model's
    default manager:

    .. code-block:: python

        from mythings import MyBaseModel
        from django_mysql.models import QuerySet

        class MySuperDuperModel(MyBaseModel):
            objects = QuerySet.as_manager()
            # TODO: what fields should this model have??


.. class:: QuerySetMixin

    The third way to add the extensions, and the container class for the
    extensions.  Add this mixin to your custom ``QuerySet`` class to add in all
    the fun:

    .. code-block:: pycon

        from django.db.models import Model
        from django_mysql.models import QuerySetMixin
        from stackoverflow import CopyPasteQuerySet

        class MySplendidQuerySet(QuerySetMixin, CopyPasteQuerySet):
            pass

        class MySplendidModel(Model):
            objects = MySplendidQuerySet.as_manager()
            # TODO: profit


.. method:: add_QuerySetMixin(queryset)

    A final way to add the extensions, useful when you don't control the
    model class - for example with built in Django models. This function
    creates a subclass of a ``QuerySet``\'s class that has the
    ``QuerySetMixin`` added in and applies it to the ``QuerySet``:

    .. code-block:: python

        from django.contrib.auth.models import User
        from django_mysql.models import add_QuerySetMixin

        qs = User.objects.all()
        qs = add_QuerySetMixin(qs)
        # Now qs has all the extensions!


The extensions are described in :doc:`queryset_extensions`.
