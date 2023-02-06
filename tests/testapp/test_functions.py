from __future__ import annotations

from unittest import SkipTest

import pytest
from django.db import connection
from django.db.models import F
from django.db.models import FloatField
from django.db.models import IntegerField
from django.db.models import Q
from django.db.models import Value
from django.db.models.functions import Length
from django.db.models.functions import Lower
from django.db.models.functions import Upper
from django.test import TestCase

from django_mysql.models.functions import AsType
from django_mysql.models.functions import ColumnAdd
from django_mysql.models.functions import ColumnDelete
from django_mysql.models.functions import ColumnGet
from django_mysql.models.functions import ConcatWS
from django_mysql.models.functions import CRC32
from django_mysql.models.functions import ELT
from django_mysql.models.functions import Field
from django_mysql.models.functions import If
from django_mysql.models.functions import JSONArrayAppend
from django_mysql.models.functions import JSONExtract
from django_mysql.models.functions import JSONInsert
from django_mysql.models.functions import JSONKeys
from django_mysql.models.functions import JSONLength
from django_mysql.models.functions import JSONReplace
from django_mysql.models.functions import JSONSet
from django_mysql.models.functions import LastInsertId
from django_mysql.models.functions import RegexpInstr
from django_mysql.models.functions import RegexpReplace
from django_mysql.models.functions import RegexpSubstr
from django_mysql.models.functions import UpdateXML
from django_mysql.models.functions import XMLExtractValue
from tests.testapp.models import Alphabet
from tests.testapp.models import Author
from tests.testapp.models import DynamicModel
from tests.testapp.models import JSONModel
from tests.testapp.test_dynamicfield import DynColTestCase
from tests.testapp.utils import print_all_queries


class ControlFlowFunctionTests(TestCase):
    def test_if_basic(self):
        Alphabet.objects.create(d="String")
        Alphabet.objects.create(d="")
        Alphabet.objects.create(d="String")
        Alphabet.objects.create(d="")

        results = list(
            Alphabet.objects.annotate(has_d=If(Length("d"), Value(True), Value(False)))
            .order_by("id")
            .values_list("has_d", flat=True)
        )
        assert results == [True, False, True, False]

    def test_if_output_field(self):
        Alphabet.objects.create(a=0, d="Aaa")
        Alphabet.objects.create(a=1, d="Bb")
        Alphabet.objects.create(a=2, d="Ccc")

        results = list(
            Alphabet.objects.annotate(
                d_length=If(
                    "a",
                    Length("d"),
                    Value(0),
                    output_field=IntegerField(),
                )
            )
            .order_by("id")
            .values_list("d_length", flat=True)
        )
        assert results == [0, 2, 3]

    def test_if_with_Q(self):
        Alphabet.objects.create(a=12, b=17)
        Alphabet.objects.create(a=13, b=17)
        Alphabet.objects.create(a=14, b=17)

        result = list(
            Alphabet.objects.annotate(conditional=If(Q(a__lte=13), "a", "b"))
            .order_by("id")
            .values_list("conditional", flat=True)
        )
        assert result == [12, 13, 17]

    def test_if_with_string_values(self):
        Alphabet.objects.create(a=1, d="Lentils")
        Alphabet.objects.create(a=2, d="Cabbage")
        Alphabet.objects.create(a=3, d="Rice")

        result = list(
            Alphabet.objects.annotate(conditional=If(Q(a=2), Upper("d"), Lower("d")))
            .order_by("id")
            .values_list("conditional", flat=True)
        )
        assert result == ["lentils", "CABBAGE", "rice"]

    def test_if_field_lookups_work(self):
        Alphabet.objects.create(a=1, d="Lentils")
        Alphabet.objects.create(a=2, d="Cabbage")
        Alphabet.objects.create(a=3, d="Rice")

        result = list(
            Alphabet.objects.annotate(
                conditional=If(Q(a__gte=2), Upper("d"), Value(""))
            )
            .filter(conditional__startswith="C")
            .order_by("id")
            .values_list("conditional", flat=True)
        )
        assert result == ["CABBAGE"]

    def test_if_false_default_None(self):
        Alphabet.objects.create(a=1)

        result = list(
            Alphabet.objects.annotate(conditional=If(Q(a=2), Value(1)))
            .filter(conditional__isnull=True)
            .values_list("conditional", flat=True)
        )
        assert result == [None]


class NumericFunctionTests(TestCase):
    def test_crc32(self):
        Alphabet.objects.create(d="AAAAAA")
        ab = Alphabet.objects.annotate(crc=CRC32("d")).get()

        # Precalculated this in MySQL prompt. Python's binascii.crc32 doesn't
        # match - maybe sign issues?
        assert ab.crc == 2854018686


class StringFunctionTests(TestCase):
    def test_concat_ws(self):
        Alphabet.objects.create(d="AAA", e="BBB")
        ab = Alphabet.objects.annotate(de=ConcatWS("d", "e")).get()
        assert ab.de == "AAA,BBB"

    def test_concat_ws_integers(self):
        Alphabet.objects.create(a=1, b=2)
        ab = Alphabet.objects.annotate(ab=ConcatWS("a", "b")).get()
        assert ab.ab == "1,2"

    def test_concat_ws_skips_nulls(self):
        Alphabet.objects.create(d="AAA", e=None, f=2)
        ab = Alphabet.objects.annotate(de=ConcatWS("d", "e", "f")).get()
        assert ab.de == "AAA,2"

    def test_concat_ws_separator(self):
        Alphabet.objects.create(d="AAA", e="BBB")
        ab = Alphabet.objects.annotate(de=ConcatWS("d", "e", separator=":")).get()
        assert ab.de == "AAA:BBB"

    def test_concat_ws_separator_null_returns_none(self):
        Alphabet.objects.create(a=1, b=2)
        concat = ConcatWS("a", "b", separator=None)
        ab = Alphabet.objects.annotate(ab=concat).get()
        assert ab.ab is None

    def test_concat_ws_separator_field(self):
        Alphabet.objects.create(a=1, d="AAA", e="BBB")
        concat = ConcatWS("d", "e", separator=F("a"))
        ab = Alphabet.objects.annotate(de=concat).get()
        assert ab.de == "AAA1BBB"

    def test_concat_ws_too_few_fields(self):
        with pytest.raises(ValueError) as excinfo:
            ConcatWS("a")
        assert "ConcatWS must take at least two expressions" in str(excinfo.value)

    def test_concat_ws_then_lookups_from_textfield(self):
        Alphabet.objects.create(d="AAA", e="BBB")
        Alphabet.objects.create(d="AAA", e="CCC")
        ab = (
            Alphabet.objects.annotate(de=ConcatWS("d", "e", separator=":"))
            .filter(de__endswith=":BBB")
            .get()
        )
        assert ab.de == "AAA:BBB"

    def test_elt_simple(self):
        Alphabet.objects.create(a=2)
        ab = Alphabet.objects.annotate(elt=ELT("a", ["apple", "orange"])).get()
        assert ab.elt == "orange"
        ab = Alphabet.objects.annotate(elt=ELT("a", ["apple"])).get()
        assert ab.elt is None

    def test_elt_expression(self):
        Alphabet.objects.create(a=1)
        ab = Alphabet.objects.annotate(
            elt=ELT("a", [Value("apple"), Value("orange")])
        ).get()
        assert ab.elt == "apple"

    def test_field_simple(self):
        Alphabet.objects.create(d="a")
        ab = Alphabet.objects.annotate(dp=Field("d", ["a", "b"])).get()
        assert ab.dp == 1
        ab = Alphabet.objects.annotate(dp=Field("d", ["b", "a"])).get()
        assert ab.dp == 2
        ab = Alphabet.objects.annotate(dp=Field("d", ["c", "d"])).get()
        assert ab.dp == 0

    def test_field_expression(self):
        Alphabet.objects.create(d="b")
        ab = Alphabet.objects.annotate(dp=Field("d", [Value("a"), Value("b")])).get()
        assert ab.dp == 2

    def test_order_by(self):
        Alphabet.objects.create(a=1, d="AAA")
        Alphabet.objects.create(a=2, d="CCC")
        Alphabet.objects.create(a=4, d="BBB")
        Alphabet.objects.create(a=3, d="BBB")
        avalues = list(
            Alphabet.objects.order_by(Field("d", ["AAA", "BBB"]), "a").values_list(
                "a", flat=True
            )
        )
        assert avalues == [2, 1, 3, 4]


class XMLFunctionTests(TestCase):
    def test_updatexml_simple(self):
        Alphabet.objects.create(d="<value>123</value>")
        Alphabet.objects.update(d=UpdateXML("d", "/value", "<value>456</value>"))
        d = Alphabet.objects.get().d
        assert d == "<value>456</value>"

    def test_updatexml_expressions(self):
        Alphabet.objects.create(d="<value>123</value>")
        Alphabet.objects.update(
            d=UpdateXML("d", Value("/value"), Value("<value>456</value>"))
        )
        d = Alphabet.objects.get().d
        assert d == "<value>456</value>"

    def test_updatexml_annotate(self):
        Alphabet.objects.create(d="<value>123</value>")
        d2 = (
            Alphabet.objects.annotate(d2=UpdateXML("d", "/value", "<value>456</value>"))
            .get()
            .d2
        )
        assert d2 == "<value>456</value>"

    def test_xmlextractvalue_simple(self):
        Alphabet.objects.create(d="<some><xml /></some>")
        Alphabet.objects.create(d="<someother><xml /></someother>")
        Alphabet.objects.create(d="<some></some><some></some>")
        evs = list(
            Alphabet.objects.annotate(
                ev=XMLExtractValue("d", "count(/some)")
            ).values_list("ev", flat=True)
        )
        assert evs == ["1", "0", "2"]

    def test_xmlextractvalue_expression(self):
        Alphabet.objects.create(d="<some><xml /></some>")
        evs = list(
            Alphabet.objects.annotate(
                ev=XMLExtractValue("d", Value("count(/some)"))
            ).values_list("ev", flat=True)
        )
        assert evs == ["1"]

    def test_xmlextractvalue_invalid_xml(self):
        Alphabet.objects.create(d='{"this": "isNotXML"}')
        ab = Alphabet.objects.annotate(ev=XMLExtractValue("d", "/some")).get()
        assert ab.ev == ""


class InformationFunctionTests(TestCase):
    databases = {"default", "other"}

    def test_last_insert_id(self):
        Alphabet.objects.create(a=7891)
        Alphabet.objects.update(a=LastInsertId("a") + 1)
        lid = LastInsertId.get()
        assert lid == 7891

    def test_last_insert_id_other_db_connection(self):
        Alphabet.objects.using("other").create(a=9191)
        Alphabet.objects.using("other").update(a=LastInsertId("a") + 9)
        lid = LastInsertId.get(using="other")
        assert lid == 9191

    def test_last_insert_id_in_query(self):
        ab1 = Alphabet.objects.create(a=3719, b=717612)
        ab2 = Alphabet.objects.create(a=1838, b=12636)

        # Delete but store value of b and re-assign it to first second Alphabet
        Alphabet.objects.filter(id=ab1.id, b=LastInsertId("b")).delete()
        Alphabet.objects.filter(id=ab2.id).update(b=LastInsertId())

        ab = Alphabet.objects.get()
        assert ab.b == 717612


class JSONFunctionTests(TestCase):
    obj: JSONModel

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.obj = JSONModel.objects.create(
            attrs={
                "int": 88,
                "flote": 1.5,
                "sub": {"document": "store"},
                "arr": ["dee", "arr", "arr"],
            }
        )

    def test_json_extract_output_field_too_many_paths(self):
        with pytest.raises(TypeError) as excinfo:
            JSONExtract("foo", "bar", "baz", output_field=FloatField())
        assert "output_field won't work with more than one path" in str(excinfo.value)

    def test_json_extract_flote(self):
        results = list(
            JSONModel.objects.annotate(x=JSONExtract("attrs", "$.flote")).values_list(
                "x", flat=True
            )
        )
        assert results == [1.5]
        assert isinstance(results[0], float)

    def test_json_extract_flote_expression(self):
        results = list(
            JSONModel.objects.annotate(
                x=JSONExtract("attrs", Value("$.flote"))
            ).values_list("x", flat=True)
        )
        assert results == [1.5]
        assert isinstance(results[0], float)

    def test_json_extract_flote_as_float(self):
        results = list(
            JSONModel.objects.annotate(
                x=JSONExtract("attrs", "$.flote", output_field=FloatField())
            )
            .filter(x__gt=0.1)
            .values_list("x", flat=True)
        )
        assert results == [1.5]
        assert isinstance(results[0], float)

    def test_json_extract_multiple(self):
        results = list(
            JSONModel.objects.annotate(
                x=JSONExtract("attrs", "$.int", "$.flote")
            ).values_list("x", flat=True)
        )
        assert results == [[88, 1.5]]
        assert isinstance(results[0][0], int)
        assert isinstance(results[0][1], float)

    def test_json_extract_filter(self):
        results = list(
            JSONModel.objects.annotate(x=JSONExtract("attrs", "$.sub")).filter(
                x={"document": "store"}
            )
        )
        assert results == [self.obj]

    def test_json_keys(self):
        results = list(
            JSONModel.objects.annotate(x=JSONKeys("attrs")).values_list("x", flat=True)
        )
        assert set(results[0]) == set(self.obj.attrs.keys())

    def test_json_keys_path(self):
        results = list(
            JSONModel.objects.annotate(x=JSONKeys("attrs", "$.sub")).values_list(
                "x", flat=True
            )
        )
        assert set(results[0]) == set(self.obj.attrs["sub"].keys())

    def test_json_keys_path_expression(self):
        results = list(
            JSONModel.objects.annotate(x=JSONKeys("attrs", Value("$.sub"))).values_list(
                "x", flat=True
            )
        )
        assert set(results[0]) == set(self.obj.attrs["sub"].keys())

    def test_json_length(self):
        results = list(
            JSONModel.objects.annotate(x=JSONLength("attrs")).values_list(
                "x", flat=True
            )
        )
        assert results == [len(self.obj.attrs)]

    def test_json_length_output_field(self):
        results = list(
            JSONModel.objects.annotate(
                x=JSONLength("attrs", output_field=IntegerField())
            ).values_list("x", flat=True)
        )
        assert results == [len(self.obj.attrs)]

    def test_json_length_path(self):
        results = list(
            JSONModel.objects.annotate(x=JSONLength("attrs", "$.sub")).values_list(
                "x", flat=True
            )
        )
        assert results == [len(self.obj.attrs["sub"])]

    def test_json_length_path_expression(self):
        results = list(
            JSONModel.objects.annotate(
                x=JSONLength("attrs", Value("$.sub"))
            ).values_list("x", flat=True)
        )
        assert results == [len(self.obj.attrs["sub"])]

    def test_json_length_type(self):
        results = list(
            JSONModel.objects.annotate(x=JSONLength("attrs")).filter(x__range=[3, 5])
        )
        assert results == [self.obj]

    def test_json_insert(self):
        self.obj.attrs = JSONInsert("attrs", {"$.int": 99, "$.int2": 102})
        self.obj.save()

        obj = JSONModel.objects.get()
        assert obj.attrs["int"] == 88
        assert obj.attrs["int2"] == 102

    def test_json_insert_expression(self):
        self.obj.attrs = JSONInsert("attrs", {Value("$.int"): Value(99)})
        self.obj.save()

        obj = JSONModel.objects.get()
        assert obj.attrs["int"] == 88

    def test_json_insert_dict(self):
        self.obj.attrs = JSONInsert(
            "attrs", {"$.sub": {"paper": "drop"}, "$.sub2": {"int": 42, "foo": "bar"}}
        )
        self.obj.save()

        obj = JSONModel.objects.get()
        assert obj.attrs["sub"] == {"document": "store"}
        assert obj.attrs["sub2"]["int"] == 42
        assert obj.attrs["sub2"]["foo"] == "bar"

    def test_json_insert_array(self):
        self.obj.attrs = JSONInsert(
            "attrs", {"$.arr": [1, "two", 3], "$.arr2": ["one", 2]}
        )
        self.obj.save()

        obj = JSONModel.objects.get()
        assert obj.attrs["arr"] == ["dee", "arr", "arr"]
        assert obj.attrs["arr2"][0] == "one"
        assert obj.attrs["arr2"][1] == 2

    def test_json_insert_empty_data(self):
        with pytest.raises(ValueError) as excinfo:
            JSONInsert("attrs", {})
        assert '"data" cannot be empty' in str(excinfo.value)

    def test_json_replace_pairs(self):
        self.obj.attrs = JSONReplace("attrs", {"$.int": 101, "$.int2": 102})
        self.obj.save()

        obj = JSONModel.objects.get()
        assert obj.attrs["int"] == 101
        assert "int2" not in obj.attrs

    def test_json_replace_dict(self):
        self.obj.attrs = JSONReplace(
            "attrs", {"$.sub": {"paper": "drop"}, "$.sub2": {"int": 42, "foo": "bar"}}
        )
        self.obj.save()

        obj = JSONModel.objects.get()
        assert obj.attrs["sub"] == {"paper": "drop"}
        assert "sub2" not in obj.attrs

    def test_json_replace_array(self):
        self.obj.attrs = JSONReplace(
            "attrs", {"$.arr": [1, "two", 3], "$.arr2": ["one", 2]}
        )
        self.obj.save()

        obj = JSONModel.objects.get()
        assert obj.attrs["arr"] == [1, "two", 3]
        assert "arr2" not in obj.attrs

    def test_json_replace_empty_data(self):
        with pytest.raises(ValueError) as excinfo:
            JSONReplace("attrs", {})
        assert '"data" cannot be empty' in str(excinfo.value)

    def test_json_set_pairs(self):
        with print_all_queries():
            self.obj.attrs = JSONSet("attrs", {"$.int": 101, "$.int2": 102})
            self.obj.save()

            obj = JSONModel.objects.get()
            assert obj.attrs["int"] == 101
            assert obj.attrs["int2"] == 102

    def test_json_set_dict(self):
        self.obj.attrs = JSONSet(
            "attrs", {"$.sub": {"paper": "drop"}, "$.sub2": {"int": 42, "foo": "bar"}}
        )
        self.obj.save()

        obj = JSONModel.objects.get()
        assert obj.attrs["sub"] == {"paper": "drop"}
        assert obj.attrs["sub2"]["int"] == 42
        assert obj.attrs["sub2"]["foo"] == "bar"

    def test_json_set_array(self):
        self.obj.attrs = JSONSet(
            "attrs", {"$.arr": [1, "two", 3], "$.arr2": ["one", 2]}
        )
        self.obj.save()

        obj = JSONModel.objects.get()
        assert obj.attrs["arr"] == [1, "two", 3]
        assert obj.attrs["arr2"][0] == "one"
        assert obj.attrs["arr2"][1] == 2

    def test_json_set_complex_data(self):
        data = {
            "list": ["one", {"int": 2}, None],
            "dict": {
                "sub_list": [1, ["two", 3]],
                "sub_dict": {"paper": "drop"},
                "sub_null": None,
            },
            "empty": [],
            "null": None,
            "value": 11,
        }
        self.obj.attrs = JSONSet("attrs", {"$.data": data})
        self.obj.save()

        obj = JSONModel.objects.get()
        assert obj.attrs["data"] == data

    def test_json_set_empty_data(self):
        with pytest.raises(ValueError) as excinfo:
            JSONSet("attrs", {})
        assert '"data" cannot be empty' in str(excinfo.value)

    def test_json_array_append(self):
        self.obj.attrs = JSONArrayAppend(
            "attrs", {"$.arr": "max", "$.arr[0]": 1.1, "$.sub.document": 3}
        )
        self.obj.save()

        obj = JSONModel.objects.get()
        assert obj.attrs["arr"] == [["dee", 1.1], "arr", "arr", "max"]
        assert obj.attrs["sub"]["document"] == ["store", 3]


class RegexpFunctionTests(TestCase):
    def setUp(self):
        super().setUp()
        if not connection.mysql_is_mariadb:
            raise SkipTest("MariaDB is required")

    def test_regex_instr(self):
        Alphabet.objects.create(d="ABC")
        Alphabet.objects.create(d="ABBC")
        ab = (
            Alphabet.objects.annotate(d_double_pos=RegexpInstr("d", r"[b]{2}"))
            .filter(d_double_pos__gt=0)
            .get()
        )
        assert ab.d == "ABBC"
        assert ab.d_double_pos == 2

    def test_regex_instr_expression(self):
        Alphabet.objects.create(d="ABBC")
        ab = (
            Alphabet.objects.annotate(d_double_pos=RegexpInstr("d", Value(r"[b]{2}")))
            .filter(d_double_pos__gt=0)
            .get()
        )
        assert ab.d == "ABBC"
        assert ab.d_double_pos == 2

    def test_regex_instr_update(self):
        Alphabet.objects.create(d="A string to search")
        Alphabet.objects.create(d="Something to query")
        Alphabet.objects.create(d="Please do inspect me")
        Alphabet.objects.update(a=RegexpInstr("d", r"search|query|inspect") - 1)
        all_abs = Alphabet.objects.all().order_by("id")
        assert all_abs[0].a == 12
        assert all_abs[1].a == 13
        assert all_abs[2].a == 10

    def test_regex_replace_update(self):
        Alphabet.objects.create(d="I'm feeling sad")
        n = Alphabet.objects.update(d=RegexpReplace("d", r"\bsad\b", "happy"))
        assert n == 1
        ab = Alphabet.objects.get()
        assert ab.d == "I'm feeling happy"

    def test_regex_replace_update_expressions(self):
        Alphabet.objects.create(d="I'm feeling sad")
        n = Alphabet.objects.update(
            d=RegexpReplace("d", Value(r"\bsad\b"), Value("happy"))
        )
        assert n == 1
        ab = Alphabet.objects.get()
        assert ab.d == "I'm feeling happy"

    def test_regex_replace_update_groups(self):
        Alphabet.objects.create(d="A,,List,with,,empty,,,,strings, ")
        n = Alphabet.objects.update(d=RegexpReplace("d", r",{2,}", ","))
        assert n == 1
        ab = Alphabet.objects.get()
        assert ab.d == "A,List,with,empty,strings, "

    def test_regex_replace_filter_backref(self):
        Author.objects.create(name="Charles Dickens")
        Author.objects.create(name="Roald Dahl")
        qs = Author.objects.annotate(
            surname_first=RegexpReplace("name", r"^(.*) (.*)$", r"\2, \1")
        ).order_by("surname_first")
        assert qs[0].name == "Roald Dahl"
        assert qs[1].name == "Charles Dickens"

    def test_regex_substr(self):
        Alphabet.objects.create(d="The <tag> is there")
        qs = Alphabet.objects.annotate(d_tag=RegexpSubstr("d", r"<[^>]+>")).filter(
            d_tag__gt=""
        )
        ab = qs.get()
        assert ab.d_tag == "<tag>"

    def test_regex_substr_field(self):
        Alphabet.objects.create(d="This is the string", e=r"\bis\b")
        qs = (
            Alphabet.objects.annotate(substr=RegexpSubstr("d", F("e")))
            .filter(substr__gt="")
            .values_list("substr", flat=True)
        )
        substr = qs[0]
        assert substr == "is"

    def test_regex_substr_filter(self):
        Author.objects.create(name="Euripides")
        Author.objects.create(name="Frank Miller")
        Author.objects.create(name="Sophocles")
        qs = list(
            Author.objects.annotate(name_has_space=Length(RegexpSubstr("name", r"\s")))
            .filter(name_has_space=0)
            .order_by("id")
            .values_list("name", flat=True)
        )
        assert qs == ["Euripides", "Sophocles"]


class DynamicColumnsFunctionTests(DynColTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        DynamicModel.objects.create(attrs={"flote": 1.0, "sub": {"document": "store"}})

    def test_get_float(self):
        results = list(
            DynamicModel.objects.annotate(
                x=ColumnGet("attrs", "flote", "DOUBLE")
            ).values_list("x", flat=True)
        )
        assert results == [1.0]
        assert isinstance(results[0], float)

    def test_get_float_expression(self):
        results = list(
            DynamicModel.objects.annotate(
                x=ColumnGet("attrs", Value("flote"), "DOUBLE")
            ).values_list("x", flat=True)
        )
        assert results == [1.0]
        assert isinstance(results[0], float)

    def test_get_int(self):
        results = list(
            DynamicModel.objects.annotate(
                x=ColumnGet("attrs", "flote", "INTEGER")
            ).values_list("x", flat=True)
        )
        assert results == [1]
        assert isinstance(results[0], int)

    def test_get_null(self):
        results = list(
            DynamicModel.objects.annotate(
                x=ColumnGet("attrs", "nonexistent", "INTEGER")
            ).values_list("x", flat=True)
        )
        assert results == [None]

    def test_get_nested(self):
        results = list(
            DynamicModel.objects.annotate(
                x=ColumnGet(ColumnGet("attrs", "sub", "BINARY"), "document", "CHAR")
            ).values_list("x", flat=True)
        )
        assert results == ["store"]

    def test_get_invalid_data_type(self):
        with pytest.raises(ValueError) as excinfo:
            ColumnGet("bla", "key", "INTGRRR")
        assert "Invalid data_type 'INTGRRR'" in str(excinfo.value)

    def test_add(self):
        results = list(
            DynamicModel.objects.annotate(
                attrs2=ColumnAdd("attrs", {"another": "key"})
            ).values_list("attrs2", flat=True)
        )
        assert results == [
            {"flote": 1.0, "sub": {"document": "store"}, "another": "key"}
        ]

    def test_add_nested(self):
        with pytest.raises(ValueError) as excinfo:
            list(
                DynamicModel.objects.annotate(
                    attrs2=ColumnAdd("attrs", {"sub2": {"document": "store"}})
                ).values_list("attrs2", flat=True)
            )
        assert "nested values is not supported" in str(excinfo.value)

    def test_add_update(self):
        DynamicModel.objects.update(attrs=ColumnAdd("attrs", {"over": 9000}))
        m = DynamicModel.objects.get()
        assert m.attrs == {"flote": 1.0, "sub": {"document": "store"}, "over": 9000}

    def test_as_type_instantiation(self):
        with pytest.raises(ValueError) as excinfo:
            AsType(1, "PANTS")
        assert "Invalid data_type 'PANTS'" in str(excinfo.value)

    def test_add_update_typed(self):
        DynamicModel.objects.update(
            attrs=ColumnAdd("attrs", {"over": AsType(9000, "DOUBLE")})
        )
        m = DynamicModel.objects.get()
        assert isinstance(m.attrs["over"], float)
        assert m.attrs["over"] == 9000.0

    def test_add_update_typed_expressions(self):
        DynamicModel.objects.update(
            attrs=ColumnAdd("attrs", {Value("over"): AsType(Value(9000), "DOUBLE")})
        )
        m = DynamicModel.objects.get()
        assert isinstance(m.attrs["over"], float)
        assert m.attrs["over"] == 9000.0

    def test_delete(self):
        DynamicModel.objects.update(attrs=ColumnDelete("attrs", "sub"))
        m = DynamicModel.objects.get()
        assert m.attrs == {"flote": 1.0}

    def test_delete_subfunc(self):
        say_sub = ConcatWS(Value("s"), Value("ub"), separator="")
        DynamicModel.objects.update(attrs=ColumnDelete("attrs", say_sub))
        m = DynamicModel.objects.get()
        assert m.attrs == {"flote": 1.0}
