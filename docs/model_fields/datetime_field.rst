.. _datetime-field:

---------
DateTimeField
---------

.. currentmodule:: django_mysql.models

Mysql support DDL option ```on update current_timestamp ```
This Field support option ```on_update_current_timestamp=True```.

Docs: `MySQL <https://dev.mysql.com/doc/refman/8.0/en/timestamp-initialization.html>`__.

Django-MySQL supports Updating with CURRENT_TIMESTAMP ``DateTimeField``


.. class:: DateTimeField(**kwargs)

    A field works the same with ```django.db.models.DateTimeField``` except .update().
    when you try to update Model Instance using QuerySet.update()  ```django.db.models.DateTimeField``` is not updated
    even if ```auto_now_add``` option is True
    ``` django_mysql.models.DateTimeField(on_update_current_timestamp=True) ``` resolve this problem

    .. code-block:: python
        from django.db import models
        from django_mysql.models import DateTimeField
        class AModel(models.Model):
            datetime_field = models.DatetimeField(on_update_current_timestamp=True)

         amodel.save()  # datetime_field depend on django timezone
         AModel.objcets.update(a_char='bbb')  # datetime_field depend on mysql timezone

    define DateTimeField as above the field will be updated
    When ```.save() .update() & INSERT UPDATE``` is executed

    .. warning::

         .. code-block:: python
            from django.db import models
            from django_mysql.models import DateTimeField
            # auto_now_add, and on_update_current_timestamp are mutually exclusive
            # does not support 'auto_now_add' option, Use 'on_update_current_timestamp' option
            # fail to makemigrations
            class AModel(models.Model):
                a_char = models.CharField(max_length=16, default="")
                datetime_field = models.DatetimeField(on_update_current_timestamp=True, auto_now=True) # Fail
                datetime_field2 = models.DatetimeField(auto_now_add=True) # Fail

        you should check Django ```settings.TIME_ZONE``` is equal to ``` MySQL TIME_ZONE```
        ``` django_mysql.models.DateTimeField ``` .save() depend on django settings.TIME_ZONE
        AND QuerySet.update() depend on  MySQL TIME_ZONE

        If the physical distance is too far between DjangoServer to Database, (ex: Asia to US)
        ``` django_mysql.models.DateTimeField ``` can raise milli sec time gap to execution .save() & .update()
        because ``` django_mysql.models.DateTimeField ``` .save() depend on django settings.TIME_ZONE
        but .update() depend on MYSQL TIME_ZONE

