import pytest
from django.db import connections
from django.test import TestCase

from django_mysql.test.utils import override_mysql_variables


class OverrideVarsMethodTest(TestCase):
    @override_mysql_variables(TIMESTAMP=123)
    def test_method_decorator(self):
        self.check_timestamp(123)

    def check_timestamp(self, expected, using="default"):
        with connections[using].cursor() as cursor:
            cursor.execute("SELECT @@TIMESTAMP")
            mode = cursor.fetchone()[0]

        assert mode == expected


@override_mysql_variables(TIMESTAMP=123)
class OverrideVarsClassTest(OverrideVarsMethodTest):

    databases = ["default", "other"]

    def test_class_decorator(self):
        self.check_timestamp(123)

    @override_mysql_variables(using="other", TIMESTAMP=456)
    def test_other_connection(self):
        self.check_timestamp(123)
        self.check_timestamp(456, using="other")

    def test_it_fails_on_non_test_classes(self):
        with pytest.raises(Exception):

            @override_mysql_variables(TIMESTAMP=123)
            class MyClass:
                pass
