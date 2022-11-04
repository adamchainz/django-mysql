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

if django.VERSION < (4, 0):
    from tests.testapp.models import NullBit1Model


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


if django.VERSION < (4, 0):

    class TestNullSaveLoad(TestCase):
        def test_basic(self):
            m = NullBit1Model()
            assert m.flag is None
            m.save()

            m = NullBit1Model.objects.get(id=m.id)
            print(m.flag)
            print(type(m.flag))
            assert m.flag is None

            m.flag = True
            m.save()

            m = NullBit1Model.objects.get(id=m.id)
            assert m.flag

            m.flag = False
            m.save()

            m = NullBit1Model.objects.get(id=m.id)
            assert m.flag is not None and not m.flag

        def test_defaults(self):
            m = NullBit1Model.objects.create()
            assert m.flag is None
            m = NullBit1Model.objects.get(id=m.id)
            assert m.flag is None

        def test_filter(self):
            m = NullBit1Model.objects.create()

            assert list(NullBit1Model.objects.filter(flag=None)) == [m]
            assert list(NullBit1Model.objects.filter(flag=True)) == []
            assert list(NullBit1Model.objects.filter(flag=False)) == []

            m.flag = True
            m.save()

            assert list(NullBit1Model.objects.filter(flag=None)) == []
            assert list(NullBit1Model.objects.filter(flag=True)) == [m]
            assert list(NullBit1Model.objects.filter(flag=False)) == []

            m.flag = False
            m.save()
            assert list(NullBit1Model.objects.filter(flag=None)) == []
            assert list(NullBit1Model.objects.filter(flag=True)) == []
            assert list(NullBit1Model.objects.filter(flag=False)) == [m]

            NullBit1Model.objects.filter(flag=False).update(flag=None)
            assert list(NullBit1Model.objects.filter(flag=None)) == [m]
            assert list(NullBit1Model.objects.filter(flag=True)) == []
            assert list(NullBit1Model.objects.filter(flag=False)) == []

            NullBit1Model.objects.filter(flag=None).update(flag=True)
            assert list(NullBit1Model.objects.filter(flag=None)) == []
            assert list(NullBit1Model.objects.filter(flag=True)) == [m]
            assert list(NullBit1Model.objects.filter(flag=False)) == []

            NullBit1Model.objects.filter(flag=True).update(flag=False)
            assert list(NullBit1Model.objects.filter(flag=None)) == []
            assert list(NullBit1Model.objects.filter(flag=True)) == []
            assert list(NullBit1Model.objects.filter(flag=False)) == [m]

    class TestNullSerialization(SimpleTestCase):
        def test_dumping(self):
            instance = NullBit1Model(flag=None)
            data = json.loads(serializers.serialize("json", [instance]))[0]
            fields = data["fields"]
            assert fields["flag"] is None

        def test_loading(self):
            test_data = """
                [{"fields": {"flag": null},
                  "model": "testapp.NullBit1Model", "pk": null}]
            """
            objs = list(serializers.deserialize("json", test_data))
            assert len(objs) == 1
            instance = objs[0].object
            assert instance.flag is None

else:

    @isolate_apps("tests.testapp")
    class TestNullCheck(SimpleTestCase):
        def test_check_deprecated(self):
            class Invalid(models.Model):
                nb = NullBit1BooleanField()

            assert Invalid.check() == [
                checks.Error(
                    "NullBooleanField is removed except for support in historical "
                    "migrations.",
                    hint="Use BooleanField(null=True) instead.",
                    obj=Invalid._meta.get_field("nb"),
                    id="fields.E903",
                ),
            ]
