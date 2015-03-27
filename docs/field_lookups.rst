.. _field-lookups:

=============
Field Lookups
=============

ORM extensions for extra filtering. These are all automatically added for the
appropriate field types. Note that lookups specific to only the included
:doc:`model fields <model_fields>` are documented with the field.

-------
Soundex
-------

MySQL implements the `Soundex algorithm
<http://en.wikipedia.org/wiki/Soundex>`_ with its ``SOUNDEX`` function,
allowing you to find words sounding similar to each other (in
English only, regrettably). These lookups allow you to use that function in th
ORM and are added for :class:`~django.db.fields.CharField` and
:class:`~django.db.fields.TextField`.

soundex
-------

Match a given soundex string::

    >>> Author.objects.filter(name__soundex='R163')
    [<Author: Robert>, <Author: Rupert>]

SQL equivalent::

    SELECT ... WHERE SOUNDEX(`name`) = 'R163'


sounds_like
-----------

Match the ``SOUNDEX`` of the given string::

    >>> Author.objects.filter(name__sounds_like='Robert')
    [<Author: Robert>, <Author: Rupert>]

SQL equivalent::

    SELECT ... WHERE `name` SOUNDS LIKE 'Robert'
