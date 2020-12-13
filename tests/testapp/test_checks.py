from django.core.management import call_command
from django.test import TestCase, TransactionTestCase

from django_mysql.checks import check_variables
from django_mysql.test.utils import override_mysql_variables
from tests.testapp.utils import skip_if_django_3_1_plus, skip_if_django_before_3_1


class CallCheckTest(TestCase):

    databases = ["default", "other"]

    @skip_if_django_3_1_plus
    def test_check_old_django(self):
        call_command("check")

    @skip_if_django_before_3_1
    def test_check(self):
        call_command("check", "--database", "default", "--database", "other")


class VariablesTests(TransactionTestCase):

    databases = ["default", "other"]

    @skip_if_django_3_1_plus
    def test_passes_old_django(self):
        assert check_variables(app_configs=None) == []

    @skip_if_django_before_3_1
    def test_passes(self):
        assert check_variables(app_configs=None, databases=["default", "other"]) == []

    @skip_if_django_before_3_1
    @override_mysql_variables(sql_mode="")
    def test_passes_databases_none(self):
        errors = check_variables(app_configs=None, databases=None)
        assert errors == []

    @skip_if_django_before_3_1
    @override_mysql_variables(sql_mode="")
    def test_passes_databases_other(self):
        errors = check_variables(app_configs=None, databases=["other"])
        assert errors == []

    @skip_if_django_3_1_plus
    @override_mysql_variables(sql_mode="")
    def test_fails_if_no_strict_old_django(self):
        errors = check_variables(app_configs=None)
        assert len(errors) == 1
        assert errors[0].id == "django_mysql.W001"
        assert "MySQL Strict Mode" in errors[0].msg

    @skip_if_django_before_3_1
    @override_mysql_variables(sql_mode="")
    def test_fails_if_no_strict(self):
        errors = check_variables(app_configs=None, databases=["default", "other"])
        assert len(errors) == 1
        assert errors[0].id == "django_mysql.W001"
        assert "MySQL Strict Mode" in errors[0].msg

    @skip_if_django_3_1_plus
    @override_mysql_variables(innodb_strict_mode=0)
    def test_fails_if_no_innodb_strict_old_django(self):
        errors = check_variables(app_configs=None)
        assert len(errors) == 1
        assert errors[0].id == "django_mysql.W002"
        assert "InnoDB Strict Mode" in errors[0].msg

    @skip_if_django_before_3_1
    @override_mysql_variables(innodb_strict_mode=0)
    def test_fails_if_no_innodb_strict(self):
        errors = check_variables(app_configs=None, databases=["default", "other"])
        assert len(errors) == 1
        assert errors[0].id == "django_mysql.W002"
        assert "InnoDB Strict Mode" in errors[0].msg

    @skip_if_django_3_1_plus
    @override_mysql_variables(character_set_connection="utf8")
    def test_fails_if_not_utf8mb4_old_django(self):
        errors = check_variables(app_configs=None)
        assert len(errors) == 1
        assert errors[0].id == "django_mysql.W003"
        assert "utf8mb4" in errors[0].msg

    @skip_if_django_before_3_1
    @override_mysql_variables(character_set_connection="utf8")
    def test_fails_if_not_utf8mb4(self):
        errors = check_variables(app_configs=None, databases=["default", "other"])
        assert len(errors) == 1
        assert errors[0].id == "django_mysql.W003"
        assert "utf8mb4" in errors[0].msg
