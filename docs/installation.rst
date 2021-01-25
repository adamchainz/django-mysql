=============================
Requirements and Installation
=============================

Requirements
------------

Python 3.6 to 3.9 supported.

Django 2.2 to 3.2 supported.

MySQL 5.6 to 8.0 supported.

MariaDB 10.1 to 10.5 supported.

mysqclient 1.3 to 1.4 supported.

Installation
------------

Install it with **pip**:

.. code-block:: console

    $ python -m pip install django-mysql

Or add it to your project's ``requirements.txt``.

Add ``'django_mysql'`` to your ``INSTALLED_APPS`` setting:

.. code-block:: python

    INSTALLED_APPS = (
        ...
        'django_mysql',
    )

Django-MySQL comes with some extra checks to ensure your database configuration
is optimal. It's best to run these now you've installed to see if there is
anything to fix:

.. code-block:: console

    $ python manage.py check --database default

(The ``--database`` argument is new in Django 3.1.)

For help fixing any warnings, see :doc:`checks`.

----

**Are your tests slow?**
Check out my book `Speed Up Your Django Tests <https://gumroad.com/l/suydt>`__ which covers loads of best practices so you can write faster, more accurate tests.

----

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

    If you are using a custom manager, you can combine this like so:

    .. code-block:: python

        from django.db import models
        from django_mysql.models import QuerySet

        class MySuperDuperManager(models.Manager):
            pass


        class MySuperDuperModel(models.Model):
            objects = MySuperDuperManager.from_queryset(QuerySet)()
            # TODO: fields

.. class:: QuerySetMixin

    The third way to add the extensions, and the container class for the
    extensions.  Add this mixin to your custom ``QuerySet`` class to add in all
    the fun:

    .. code-block:: python

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
