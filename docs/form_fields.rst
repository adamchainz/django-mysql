.. _form-fields:

===========
Form Fields
===========

The following can be imported from ``django_mysql.forms``.

.. currentmodule:: django_mysql.forms

---------------
SimpleListField
---------------

.. class:: SimpleListField(base_field, max_length=None, min_length=None)

    A simple field which maps to a list, with items separated by commas. It is
    represented by an HTML ``<input>``. Empty items, resulting from leading,
    trailing, or double commas, are disallowed.

    .. attribute:: base_field

        This is a required argument.

        It specifies the underlying form field for the set. It is not used to
        render any HTML, but it does process and validate the submitted data.
        For example::

            >>> from django import forms
            >>> from django_mysql.forms import SimpleListField

            >>> class NumberListForm(forms.Form):
            ...     numbers = SimpleListField(forms.IntegerField())

            >>> form = NumberListForm({'numbers': '1,2,3'})
            >>> form.is_valid()
            True
            >>> form.cleaned_data
            {'numbers': [1, 2, 3]}

            >>> form = NumberListForm({'numbers': '1,2,a'})
            >>> form.is_valid()
            False

    .. attribute:: max_length

        This is an optional argument which validates that the list does not
        exceed the given length.

    .. attribute:: min_length

        This is an optional argument which validates that the list reaches at
        least the given length.

.. admonition:: User friendly forms

    ``SimpleListField`` is not particularly user friendly in most cases, however
    it's better than nothing.


--------------
SimpleSetField
--------------

.. class:: SimpleSetField(base_field, max_length=None, min_length=None)

    A simple field which maps to a set, with items separated by commas. It is
    represented by an HTML ``<input>``. Empty items, resulting from leading,
    trailing, or double commas, are disallowed.

    .. attribute:: base_field

        This is a required argument.

        It specifies the underlying form field for the set. It is not used to
        render any HTML, but it does process and validate the submitted data.
        For example::

            >>> from django import forms
            >>> from django_mysql.forms import SimpleSetField

            >>> class NumberSetForm(forms.Form):
            ...     numbers = SimpleSetField(forms.IntegerField())

            >>> form = NumberSetForm({'numbers': '1,2,3'})
            >>> form.is_valid()
            True
            >>> form.cleaned_data
            {'numbers': set([1, 2, 3])}

            >>> form = NumberSetForm({'numbers': '1,2,a'})
            >>> form.is_valid()
            False

    .. attribute:: max_length

        This is an optional argument which validates that the set does not
        exceed the given length.

    .. attribute:: min_length

        This is an optional argument which validates that the set reaches at
        least the given length.

.. admonition:: User friendly forms

    ``SimpleSetField`` is not particularly user friendly in most cases, however
    it's better than nothing.
