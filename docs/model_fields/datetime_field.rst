.. _datetime-field:

---------
DateTimeField
---------

.. currentmodule:: django_mysql.models

Mysql support DDL option ```on update current_timestamp ```
This Field support option ```on_update_current_timestamp=True```.

Docs: `MySQL <https://dev.mysql.com/doc/refman/8.0/en/timestamp-initialization.html>`__.

Django-MySQL supports Updating for TIMESTAMP ``DateTimeField``


.. class:: DateTimeField(**kwargs)

    A field works the same with ```django.db.models.DateTimeField``` except .update().
    when you try to update Model Instance using QuerySet.update()  ```django.db.models.DateTimeField``` is not updated
    even if ```auto_now_add``` option is True
    ``` django_mysql.models.DateTimeField(on_update_current_timestamp=True) ``` resolve this problem

    .. code-block:: python

        from django_mysql.models import DateTimeField
        datetime_field = models.DatetimeField(on_update_current_timestamp=True, auto_now=True)

    define DateTimeField as above the field will be updated
    When ```.save() .update() & INSERT UPDATE``` is executed

    .. warning::

         .. code-block:: python
            from django_mysql.models import DateTimeField
            # auto_now_add, and on_update_current_timestamp are mutually exclusive
            # fail to makemigrations
            datetime_field = models.DatetimeField(on_update_current_timestamp=True,auto_now_add=True)

        you should check Django ```settings.TIME_ZONE``` is equal to ``` MySQL TIME_ZONE```
        ``` django_mysql.models.DateTimeField ``` .save() depend on django settings.TIME_ZONE
        AND QuerySet.update() depend on  MySQL TIME_ZONE
