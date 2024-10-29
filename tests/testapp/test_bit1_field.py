from __future__ import annotations

import json

import django
from django.core import checks
from django.core import serializers
from django.db import models
from django.db.models import F
from django.test import SimpleTestCase
from django.test import TestCase
from django.test.utils import isolate_apps

from django_mysql.models import NullBit1BooleanField
from tests.testapp.models import Bit1Model


class TestSaveLoad(TestCase):
    def test_basic(self):
        m = Bit1Model()
        m.flag_a = False
        m.flag_b = True
        m.save()

        m = Bit1Model.objects.get(id=m.id)
        assert not m.flag_a
        assert m.flag_b

        m.save()

        m = Bit1Model.objects.get(id=m.id)
        assert not m.flag_a
        assert m.flag_b

        m.flag_a = True
        m.flag_b = False
        m.save()

        m = Bit1Model.objects.get(id=m.id)
        assert m.flag_a
        assert not m.flag_b

    def test_defaults(self):
        m = Bit1Model.objects.create()
        assert m.flag_a
        assert not m.flag_b

        m = Bit1Model.objects.get(id=m.id)
        assert m.flag_a
        assert not m.flag_b

    def test_filter(self):
        m = Bit1Model.objects.create(flag_a=True, flag_b=True)

        assert list(Bit1Model.objects.filter(flag_a=True)) == [m]
        assert list(Bit1Model.objects.filter(flag_a=False)) == []

        assert list(Bit1Model.objects.filter(flag_a=F("flag_b"))) == [m]
        assert list(Bit1Model.objects.exclude(flag_a=F("flag_b"))) == []

        m.flag_a = False
        m.save()

        assert list(Bit1Model.objects.filter(flag_a=True)) == []
        assert list(Bit1Model.objects.filter(flag_a=False)) == [m]

        assert list(Bit1Model.objects.filter(flag_a=F("flag_b"))) == []
        assert list(Bit1Model.objects.exclude(flag_a=F("flag_b"))) == [m]

        Bit1Model.objects.filter(flag_a=False).update(flag_a=True)
        assert list(Bit1Model.objects.filter(flag_a=True)) == [m]
        assert list(Bit1Model.objects.filter(flag_a=False)) == []

        Bit1Model.objects.filter(flag_a=True).update(flag_a=False)
        assert list(Bit1Model.objects.filter(flag_a=True)) == []
        assert list(Bit1Model.objects.filter(flag_a=False)) == [m]


class TestSerialization(SimpleTestCase):
    def test_dumping(self):
        instance = Bit1Model(flag_a=True, flag_b=False)
        data = json.loads(serializers.serialize("json", [instance]))[0]
        fields = data["fields"]
        assert fields["flag_a"]
        assert not fields["flag_b"]

    def test_loading(self):
        test_data = """
            [{"fields": {"flag_a": false, "flag_b": true},
              "model": "testapp.Bit1Model", "pk": null}]
        """
        objs = list(serializers.deserialize("json", test_data))
        assert len(objs) == 1
        instance = objs[0].object
        assert not instance.flag_a
        assert instance.flag_b


@isolate_apps("tests.testapp")
class TestNullCheck(SimpleTestCase):
    def test_check_deprecated(self):
        class Invalid(models.Model):
            nb = NullBit1BooleanField()

        if django.VERSION >= (5, 0):
            hint = "Use BooleanField(null=True, blank=True) instead."
        else:
            hint = "Use BooleanField(null=True) instead."

        assert Invalid.check() == [
            checks.Error(
                "NullBooleanField is removed except for support in historical "
                "migrations.",
                hint=hint,
                obj=Invalid._meta.get_field("nb"),
                id="fields.E903",
            ),
        ]
