from __future__ import annotations

from unittest import SkipTest, mock

import django
import pytest
from django.db import DEFAULT_DB_ALIAS, connection, connections
from django.test import SimpleTestCase, TestCase

from django_mysql.utils import (
    WeightedAverageRate,
    connection_is_mariadb,
    format_duration,
    index_name,
)
from tests.testapp.models import Author, AuthorMultiIndex

if django.VERSION < (3, 0):
    from django_mysql.utils import _is_mariadb_cache


class ConnectionIsMariaDBTests(TestCase):
    def setUp(self):
        if django.VERSION >= (3, 0):
            raise SkipTest("Not needed on Django 3.0+")
        super().setUp()
        _is_mariadb_cache.clear()  # type: ignore [attr-defined]

    def test_connection_proxy(self):
        connection_is_mariadb(connection)

    def test_connection(self):
        connection_is_mariadb(connections[DEFAULT_DB_ALIAS])

    def test_non_mysql(self):
        conn = mock.MagicMock(vendor="sqlite3")
        assert not connection_is_mariadb(conn)

    def test_oracle_mysql(self):
        conn = mock.MagicMock(vendor="mysql")
        conn.connection.get_server_info.return_value = "5.7.19"
        assert not connection_is_mariadb(conn)
        # check cached
        conn.connection.get_server_info.side_effect = ValueError("re-called")
        assert not connection_is_mariadb(conn)

    def test_mariadb(self):
        conn = mock.MagicMock(vendor="mysql")
        conn.connection.get_server_info.return_value = "10.4.3-MariaDB-1~precise-log"
        assert connection_is_mariadb(conn)
        conn.connection.get_server_info.side_effect = ValueError("re-called")
        assert connection_is_mariadb(conn)


class WeightedAverageRateTests(SimpleTestCase):
    def test_constant(self):
        # If we keep achieving a rate of 100 rows in 0.5 seconds, it should
        # recommend that we keep there
        rate = WeightedAverageRate(0.5)
        assert rate.update(100, 0.5) == 100
        assert rate.update(100, 0.5) == 100
        assert rate.update(100, 0.5) == 100

    def test_slow(self):
        # If we keep achieving a rate of 100 rows in 1 seconds, it should
        # recommend that we move to 50
        rate = WeightedAverageRate(0.5)
        assert rate.update(100, 1.0) == 50
        assert rate.update(100, 1.0) == 50
        assert rate.update(100, 1.0) == 50

    def test_fast(self):
        # If we keep achieving a rate of 100 rows in 0.25 seconds, it should
        # recommend that we move to 200
        rate = WeightedAverageRate(0.5)
        assert rate.update(100, 0.25) == 200
        assert rate.update(100, 0.25) == 200
        assert rate.update(100, 0.25) == 200

    def test_good_guess(self):
        # If we are first slow then hit the target at 50, we should be good
        rate = WeightedAverageRate(0.5)
        assert rate.update(100, 1.0) == 50
        assert rate.update(50, 0.5) == 50
        assert rate.update(50, 0.5) == 50
        assert rate.update(50, 0.5) == 50

    def test_zero_division(self):
        rate = WeightedAverageRate(0.5)
        assert rate.update(1, 0.0) == 500


class FormatDurationTests(SimpleTestCase):
    def test_seconds(self):
        assert format_duration(0) == "0s"
        assert format_duration(1) == "1s"
        assert format_duration(30) == "30s"
        assert format_duration(59) == "59s"

    def test_minutes(self):
        assert format_duration(60) == "1m0s"
        assert format_duration(61) == "1m1s"
        assert format_duration(120) == "2m0s"
        assert format_duration(3599) == "59m59s"

    def test_hours(self):
        assert format_duration(3600) == "1h0m0s"
        assert format_duration(3601) == "1h0m1s"


class IndexNameTests(TestCase):

    databases = ["default", "other"]

    def test_requires_field_names(self):
        with pytest.raises(ValueError) as excinfo:
            index_name(Author)
        assert "At least one field name required" in str(excinfo.value)

    def test_requires_real_field_names(self):
        with pytest.raises(ValueError) as excinfo:
            index_name(Author, "nonexistent")
        assert "Fields do not exist: nonexistent" in str(excinfo.value)

    def test_primary_key(self):
        assert index_name(Author, "id") == "PRIMARY"

    def test_primary_key_using_other(self):
        assert index_name(Author, "id", using="other") == "PRIMARY"

    def test_secondary_single_field(self):
        name = index_name(Author, "name")
        assert name.startswith("testapp_author_")

    def test_index_does_not_exist(self):
        with pytest.raises(KeyError) as excinfo:
            index_name(Author, "bio")
        assert "There is no index on (bio)" in str(excinfo.value)

    def test_secondary_multiple_fields(self):
        name = index_name(AuthorMultiIndex, "name", "country")
        assert name.startswith("testapp_authormultiindex")

    def test_secondary_multiple_fields_non_existent_reversed_existent(self):
        # Checks that order is preserved
        with pytest.raises(KeyError):
            index_name(AuthorMultiIndex, "country", "name")

    def test_secondary_multiple_fields_non_existent(self):
        with pytest.raises(KeyError):
            index_name(AuthorMultiIndex, "country", "id")
