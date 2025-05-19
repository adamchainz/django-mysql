from __future__ import annotations

import pytest
from django.test import SimpleTestCase, TestCase

from django_mysql.utils import WeightedAverageRate, format_duration, index_name
from tests.testapp.models import Author, AuthorMultiIndex


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
    databases = {"default", "other"}

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
        assert name == "testapp_authormultiindex_uniq"

    def test_secondary_multiple_fields_non_existent_reversed_existent(self):
        # Checks that order is preserved
        with pytest.raises(KeyError):
            index_name(AuthorMultiIndex, "country", "name")

    def test_secondary_multiple_fields_non_existent(self):
        with pytest.raises(KeyError):
            index_name(AuthorMultiIndex, "country", "id")
