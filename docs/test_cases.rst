.. _test_cases:

==============
Test Cases
==============

.. currentmodule:: django_mysql.test.cases

The following can be imported from ``django_mysql.test.cases``.


.. class:: FasterTransactionTestCase

    If you have many tables, TransactionTestCase can be slow because Django executes ``TRUNCATE`` on every table after every test. FasterTransactionTestCase will only ``TRUNCATE`` non-empty tables.
