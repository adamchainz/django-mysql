.. _test_utilities:

==============
Test Utilities
==============

.. currentmodule:: django_mysql.test.utils

The following can be imported from ``django_mysql.test.utils``.


.. function:: override_mysql_variables(using='default', **options)

    Overrides MySQL system variables for a test method or for every test method
    in a class, similar to Django's :class:`~django.test.override_settings`.
    This can be useful when you're testing code that must run under multiple
    MySQL environments (like most of `django-mysql`). For example:

    .. code-block:: python

        @override_mysql_variables(SQL_MODE="MSSQL")
        class MyTests(TestCase):

            def test_it_works_in_mssql(self):
                run_it()

            @override_mysql_variables(SQL_MODE="ANSI")
            def test_it_works_in_ansi_mode(self):
                run_it()

    During the first test, the ``SQL_MODE`` will be ``MSSQL``, and during the
    second, it will be ``ANSI``; each slightly changes the allowed SQL syntax,
    meaning they are useful to test.

    .. note::

        This only sets the system variables for the session, so if the tested
        code closes and re-opens the database connection the change will be
        reset.

    .. attribute:: using

    The connection alias to set the system variables for, defaults to
    'default'.
