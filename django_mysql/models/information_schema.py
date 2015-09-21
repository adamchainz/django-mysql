from django.db.models import (
    CharField, DateTimeField, IntegerField, Manager, PositiveIntegerField,
)

from .base import Model
from .functions import Database


class ThisSchemaTableManager(Manager):
    def get_queryset(self):
        qs = super(ThisSchemaTableManager, self).get_queryset()
        return qs.filter(schema=Database())


class Table(Model):
    class Meta(object):
        managed = False
        db_table = 'information_schema`.`tables'

    catalog = CharField(db_column='table_catalog', max_length=512)
    schema = CharField(db_column='table_schema', max_length=64)
    name = CharField(primary_key=True, max_length=64, db_column='table_name')
    table_type = CharField(max_length=64)
    engine = CharField(max_length=64)
    version = IntegerField()
    row_format = CharField(max_length=10)
    rows = PositiveIntegerField(db_column='table_rows')
    avg_row_length = PositiveIntegerField()
    data_length = PositiveIntegerField()
    max_data_length = PositiveIntegerField()
    index_length = PositiveIntegerField()
    data_free = PositiveIntegerField()
    auto_increment = PositiveIntegerField()
    create_time = DateTimeField()
    update_time = DateTimeField()
    check_time = DateTimeField()
    collation = CharField(db_column='table_collation')
    checksum = PositiveIntegerField()
    create_options = CharField(max_length=255)
    comment = CharField(db_column='table_comment', max_length=2048)

    objects = ThisSchemaTableManager()
    alldb_objects = Manager()

    def __str__(self):
        return "`" + self.name + "`"

    @classmethod
    def for_model(cls, model):
        return cls.objects.get(name=model._meta.db_table)
