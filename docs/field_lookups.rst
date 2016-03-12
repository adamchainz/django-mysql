.. _field-lookups:

=============
Field Lookups
=============

ORM extensions for filtering. These are all automatically added for the
appropriate field types when ``django_mysql`` is in your ``INSTALLED_APPS``.
Note that lookups specific to included
:doc:`model fields <model_fields>` are documented with the field, rather than
here.


--------------------------------
Case-sensitive String Comparison
--------------------------------

MySQL string comparison has a case-sensitivity dependent on the collation of
your tables/columns, as the `Django manual describes
<https://docs.djangoproject.com/en/1.8/ref/databases/#collation-settings>`_.
However, it is possible to query in a case-sensitive manner even when your data
is not stored with a case-sensitive collation, using the ``BINARY`` keyword.
The following lookup adds that capability to the ORM for
:class:`~django.db.fields.CharField`, :class:`~django.db.fields.TextField`, and
subclasses thereof.

case_exact
----------

Exact, case-sensitive match for character columns, no matter the underlying
collation:

.. code-block:: pycon

    >>> Author.objects.filter(name__case_exact="dickens")
    []
    >>> Author.objects.filter(name__case_exact="Dickens")
    [<Author: Dickens>]

-------
Soundex
-------

MySQL implements the `Soundex algorithm
<http://en.wikipedia.org/wiki/Soundex>`_ with its ``SOUNDEX`` function,
allowing you to find words sounding similar to each other (in
English only, regrettably). These lookups allow you to use that function in the
ORM and are added for :class:`~django.db.fields.CharField` and
:class:`~django.db.fields.TextField`.

soundex
-------

Match a given soundex string:

.. code-block:: pycon

    >>> Author.objects.filter(name__soundex='R163')
    [<Author: Robert>, <Author: Rupert>]

SQL equivalent:

.. code-block:: mysql

    SELECT ... WHERE SOUNDEX(`name`) = 'R163'


sounds_like
-----------

Match the ``SOUNDEX`` of the given string:

.. code-block:: pycon

    >>> Author.objects.filter(name__sounds_like='Robert')
    [<Author: Robert>, <Author: Rupert>]

SQL equivalent:

.. code-block:: mysql

    SELECT ... WHERE `name` SOUNDS LIKE 'Robert'
