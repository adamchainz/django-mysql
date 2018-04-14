# -*- coding:utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals,
)

import pytest
from django.core.management import call_command
from django.db import connection
from django.db.migrations.writer import MigrationWriter
from django.db.transaction import atomic
from django.db.utils import DataError
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.utils import six

from django_mysql.models import SizedBinaryField, SizedTextField
from django_mysql.test.utils import override_mysql_variables
from testapp.models import SizeFieldModel, TemporaryModel
from testapp.utils import column_type

# Ensure we aren't just warned about the data truncation
forceDataError = override_mysql_variables(SQL_MODE='STRICT_TRANS_TABLES')


def migrate(name):
    call_command('migrate', 'testapp', name,
                 verbosity=0, skip_checks=True, interactive=False)


class SubSizedBinaryField(SizedBinaryField):
    """
    Used below, has a different path for deconstruct()
    """


@forceDataError
class SizedBinaryFieldTests(TestCase):

    def test_binaryfield_checks(self):
        class InvalidSizedBinaryModel(TemporaryModel):
            field = SizedBinaryField(size_class=5)

        errors = InvalidSizedBinaryModel.check(actually_check=True)
        assert len(errors) == 1
        assert errors[0].id == 'django_mysql.E007'
        assert errors[0].msg == 'size_class must be 1, 2, 3, or 4'

    def test_binaryfield_default_length(self):
        # By default, SizedBinaryField should act like BinaryField
        field = SizedBinaryField()
        assert field.size_class == 4
        assert field.db_type(None) == 'longblob'

    @atomic
    def test_binary_1_max_length(self):
        # Okay
        m = SizeFieldModel(binary1=six.binary_type(1) * (2**8 - 1))
        m.save()

        # Bad - Data too long
        m = SizeFieldModel(binary1=six.binary_type(1) * (2**8))
        with pytest.raises(DataError) as excinfo:
            m.save()
        assert excinfo.value.args[0] == 1406

    def test_deconstruct_path(self):
        field = SizedBinaryField(size_class=1)
        name, path, args, kwargs = field.deconstruct()
        assert path == 'django_mysql.models.SizedBinaryField'

    def test_deconstruct_subclass_path(self):
        field = SubSizedBinaryField(size_class=1)
        name, path, args, kwargs = field.deconstruct()
        assert path == 'tests.testapp.test_size_fields.SubSizedBinaryField'

    def test_deconstruct_size_class_4(self):
        field = SizedBinaryField(size_class=4)
        name, path, args, kwargs = field.deconstruct()
        new = SizedBinaryField(*args, **kwargs)
        assert new.size_class == field.size_class

    def test_deconstruct_size_class_2(self):
        field = SizedBinaryField(size_class=2)
        name, path, args, kwargs = field.deconstruct()
        new = SizedBinaryField(*args, **kwargs)
        assert new.size_class == field.size_class

    def test_makemigrations(self):
        field = SizedBinaryField(size_class=1)
        statement, imports = MigrationWriter.serialize(field)

        assert (
            statement ==
            "django_mysql.models.SizedBinaryField(size_class=1)"
        )

    def test_makemigrations_size_class_implicit(self):
        field = SizedBinaryField()
        statement, imports = MigrationWriter.serialize(field)

        assert (
            statement ==
            "django_mysql.models.SizedBinaryField(size_class=4)"
        )


@forceDataError
class SizedBinaryFieldMigrationTests(TransactionTestCase):

    @override_settings(MIGRATION_MODULES={
        "testapp": "testapp.sizedbinaryfield_migrations",
    })
    def test_adding_field_with_default(self):
        table_name = 'testapp_sizedbinaryaltermodel'
        table_names = connection.introspection.table_names

        with connection.cursor() as cursor:
            assert table_name not in table_names(cursor)

        migrate('0001_initial')
        with connection.cursor() as cursor:
            assert table_name in table_names(cursor)
            assert column_type(table_name, 'field') == 'longblob'

        migrate('0002_alter_field')
        with connection.cursor() as cursor:
            assert table_name in table_names(cursor)
            assert column_type(table_name, 'field') == 'blob'

        migrate('0001_initial')
        with connection.cursor() as cursor:
            assert table_name in table_names(cursor)
            assert column_type(table_name, 'field') == 'longblob'

        migrate('zero')
        with connection.cursor() as cursor:
            assert table_name not in table_names(cursor)


class SubSizedTextField(SizedTextField):
    """
    Used below, has a different path for deconstruct()
    """


@forceDataError
class SizedTextFieldTests(TestCase):

    def test_check_max_length(self):
        class InvalidSizedTextModel(TemporaryModel):
            field = SizedTextField(size_class=5)

        errors = InvalidSizedTextModel.check(actually_check=True)
        assert len(errors) == 1
        assert errors[0].id == 'django_mysql.E008'
        assert errors[0].msg == 'size_class must be 1, 2, 3, or 4'

    def test_textfield_default_length(self):
        # By default, SizedTextField should act like TextField
        field = SizedTextField()
        assert field.size_class == 4
        assert field.db_type(None) == 'longtext'

    def test_tinytext_max_length(self):
        # Okay
        m = SizeFieldModel(text1='a' * (2**8 - 1))
        m.save()

        # Bad - Data too long
        m = SizeFieldModel(text1='a' * (2**8))
        with atomic(), pytest.raises(DataError) as excinfo:
            m.save()
        assert excinfo.value.args[0] == 1406

    def test_deconstruct_path(self):
        field = SizedTextField(size_class=1)
        name, path, args, kwargs = field.deconstruct()
        assert path == 'django_mysql.models.SizedTextField'

    def test_deconstruct_subclass_path(self):
        field = SubSizedTextField(size_class=1)
        name, path, args, kwargs = field.deconstruct()
        assert path == 'tests.testapp.test_size_fields.SubSizedTextField'

    def test_deconstruct_size_class_4(self):
        field = SizedTextField(size_class=4)
        name, path, args, kwargs = field.deconstruct()
        new = SizedTextField(*args, **kwargs)
        assert new.size_class == field.size_class

    def test_deconstruct_size_class_2(self):
        field = SizedTextField(size_class=2)
        name, path, args, kwargs = field.deconstruct()
        new = SizedTextField(*args, **kwargs)
        assert new.size_class == field.size_class

    def test_makemigrations(self):
        field = SizedTextField(size_class=1)
        statement, imports = MigrationWriter.serialize(field)

        assert (
            statement ==
            "django_mysql.models.SizedTextField(size_class=1)"
        )

    def test_makemigrations_size_class_implicit(self):
        field = SizedTextField()
        statement, imports = MigrationWriter.serialize(field)

        assert (
            statement ==
            "django_mysql.models.SizedTextField(size_class=4)"
        )


@forceDataError
class SizedTextFieldMigrationTests(TransactionTestCase):

    @override_settings(MIGRATION_MODULES={
        "testapp": "testapp.sizedtextfield_migrations",
    })
    def test_adding_field_with_default(self):
        table_name = 'testapp_sizedtextaltermodel'
        table_names = connection.introspection.table_names

        with connection.cursor() as cursor:
            assert table_name not in table_names(cursor)

        migrate('0001_initial')
        with connection.cursor() as cursor:
            assert table_name in table_names(cursor)
            assert column_type(table_name, 'field') == 'mediumtext'

        migrate('0002_alter_field')
        with connection.cursor() as cursor:
            assert table_name in table_names(cursor)
            assert column_type(table_name, 'field') == 'tinytext'

        migrate('0001_initial')
        with connection.cursor() as cursor:
            assert table_name in table_names(cursor)
            assert column_type(table_name, 'field') == 'mediumtext'

        migrate('zero')
        with connection.cursor() as cursor:
            assert table_name not in table_names(cursor)
