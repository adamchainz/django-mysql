# -*- coding:utf-8 -*-
from django.test import TestCase

from django_mysql.models import information_schema as i_s
from testapp.models import Author


class TableTests(TestCase):
    def test_objects(self):
        tables = i_s.Table.objects.all()
        for table in tables:
            assert table.name > ''
            assert table.schema == 'test_django_mysql'
            assert table.table_type == 'BASE TABLE'
            assert table.engine == 'InnoDB'

    def test_alldb_objects(self):
        all_count = i_s.Table.objects.count()
        alldb_count = i_s.Table.alldb_objects.count()
        assert alldb_count > all_count  # 'mysql' db tables, etc.

    def test_for_model(self):
        table = i_s.Table.for_model(Author)
        assert table.name == 'testapp_author'
