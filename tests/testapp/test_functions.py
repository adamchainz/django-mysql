# -*- coding:utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import hashlib
from unittest import SkipTest

import pytest
from django.db import connection
from django.db.models import F, Q, Value
from django.db.models.functions import Length, Lower, Upper
from django.test import TestCase
from django.utils import six

from django_mysql.models.functions import (
    CRC32, ELT, MD5, SHA1, SHA2, Abs, AsType, Ceiling, ColumnAdd, ColumnDelete,
    ColumnGet, ConcatWS, Field, Floor, Greatest, If, JSONExtract, JSONInsert,
    JSONKeys, JSONLength, JSONReplace, JSONSet, LastInsertId, Least,
    RegexpInstr, RegexpReplace, RegexpSubstr, Round, Sign, UpdateXML,
    XMLExtractValue
)
from django_mysql.utils import connection_is_mariadb
from testapp.models import Alphabet, Author, DynamicModel, JSONModel
from testapp.test_dynamicfield import DynColTestCase
from testapp.test_jsonfield import JSONFieldTestCase


class ComparisonFunctionTests(TestCase):

    def test_greatest(self):
        Alphabet.objects.create(d='A', e='B')
        ab = Alphabet.objects.annotate(best=Greatest('d', 'e')).first()
        assert ab.best == 'B'

    def test_greatest_takes_no_kwargs(self):
        with pytest.raises(TypeError):
            Greatest('a', something='wrong')

    def test_least(self):
        Alphabet.objects.create(a=1, b=2, c=-1)
        ab = Alphabet.objects.annotate(worst=Least('a', 'b', 'c')).first()
        assert ab.worst == -1


class ControlFlowFunctionTests(TestCase):

    def test_if_basic(self):
        Alphabet.objects.create(d='String')
        Alphabet.objects.create(d='')
        Alphabet.objects.create(d='String')
        Alphabet.objects.create(d='')

        results = list(Alphabet.objects.annotate(
            has_d=If(Length('d'), Value(True), Value(False))
        ).order_by('id').values_list('has_d', flat=True))
        assert results == [True, False, True, False]

    def test_if_with_Q(self):
        Alphabet.objects.create(a=12, b=17)
        Alphabet.objects.create(a=13, b=17)
        Alphabet.objects.create(a=14, b=17)

        result = list(Alphabet.objects.annotate(
            conditional=If(Q(a__lte=13), 'a', 'b')
        ).order_by('id').values_list('conditional', flat=True))
        assert result == [12, 13, 17]

    def test_if_with_string_values(self):
        Alphabet.objects.create(a=1, d='Lentils')
        Alphabet.objects.create(a=2, d='Cabbage')
        Alphabet.objects.create(a=3, d='Rice')

        result = list(Alphabet.objects.annotate(
            conditional=If(Q(a=2), Upper('d'), Lower('d'))
        ).order_by('id').values_list('conditional', flat=True))
        assert result == ['lentils', 'CABBAGE', 'rice']

    def test_if_field_lookups_work(self):
        Alphabet.objects.create(a=1, d='Lentils')
        Alphabet.objects.create(a=2, d='Cabbage')
        Alphabet.objects.create(a=3, d='Rice')

        result = list(Alphabet.objects.annotate(
            conditional=If(Q(a__gte=2), Upper('d'), Value(''))
        ).filter(
            conditional__startswith='C'
        ).order_by('id').values_list('conditional', flat=True))
        assert result == ['CABBAGE']

    def test_if_false_default_None(self):
        Alphabet.objects.create(a=1)

        result = list(Alphabet.objects.annotate(
            conditional=If(Q(a=2), Value(1))
        ).filter(
            conditional__isnull=True
        ).values_list('conditional', flat=True))
        assert result == [None]


class NumericFunctionTests(TestCase):

    def test_abs(self):
        Alphabet.objects.create(a=-2)
        ab = Alphabet.objects.annotate(aaa=Abs('a')).first()
        assert ab.aaa == 2

    def test_ceiling(self):
        Alphabet.objects.create(g=0.5)
        ab = Alphabet.objects.annotate(gceil=Ceiling('g')).first()
        assert ab.gceil == 1

    def test_crc32(self):
        Alphabet.objects.create(d='AAAAAA')
        ab = Alphabet.objects.annotate(crc=CRC32('d')).first()
        # Precalculated this in MySQL prompt. Python's binascii.crc32 doesn't
        # match - maybe sign issues?
        assert ab.crc == 2854018686

    def test_crc32_only_takes_one_arg_no_kwargs(self):
        with pytest.raises(TypeError):
            CRC32('d', 'c')

        with pytest.raises(TypeError):
            CRC32('d', something='wrong')

    def test_floor(self):
        Alphabet.objects.create(g=1.5)
        ab = Alphabet.objects.annotate(gfloor=Floor('g')).first()
        assert ab.gfloor == 1

    def test_round(self):
        Alphabet.objects.create(g=24.459)
        ab = Alphabet.objects.annotate(ground=Round('g')).get()
        assert ab.ground == 24

    def test_round_up(self):
        Alphabet.objects.create(g=27.859)
        ab = Alphabet.objects.annotate(ground=Round('g')).get()
        assert ab.ground == 28

    def test_round_places(self):
        Alphabet.objects.create(a=81731)
        ab = Alphabet.objects.annotate(around=Round('a', -2)).get()
        assert ab.around == 81700

    def test_sign(self):
        Alphabet.objects.create(a=123, b=0, c=-999)
        ab = Alphabet.objects.annotate(
            asign=Sign('a'),
            bsign=Sign('b'),
            csign=Sign('c'),
        ).first()
        assert ab.asign == 1
        assert ab.bsign == 0
        assert ab.csign == -1


class StringFunctionTests(TestCase):

    def test_concat_ws(self):
        Alphabet.objects.create(d='AAA', e='BBB')
        ab = Alphabet.objects.annotate(de=ConcatWS('d', 'e')).first()
        assert ab.de == 'AAA,BBB'

    def test_concat_ws_integers(self):
        Alphabet.objects.create(a=1, b=2)
        ab = Alphabet.objects.annotate(ab=ConcatWS('a', 'b')).first()
        assert ab.ab == '1,2'

    def test_concat_ws_skips_nulls(self):
        Alphabet.objects.create(d='AAA', e=None, f=2)
        ab = Alphabet.objects.annotate(de=ConcatWS('d', 'e', 'f')).first()
        assert ab.de == 'AAA,2'

    def test_concat_ws_separator(self):
        Alphabet.objects.create(d='AAA', e='BBB')
        ab = (
            Alphabet.objects.annotate(de=ConcatWS('d', 'e', separator=':'))
                            .first()
        )
        assert ab.de == 'AAA:BBB'

    def test_concat_ws_separator_null_returns_none(self):
        Alphabet.objects.create(a=1, b=2)
        concat = ConcatWS('a', 'b', separator=None)
        ab = Alphabet.objects.annotate(ab=concat).first()
        assert ab.ab is None

    def test_concat_ws_separator_field(self):
        Alphabet.objects.create(a=1, d='AAA', e='BBB')
        concat = ConcatWS('d', 'e', separator=F('a'))
        ab = Alphabet.objects.annotate(de=concat).first()
        assert ab.de == 'AAA1BBB'

    def test_concat_ws_bad_arg(self):
        with pytest.raises(ValueError) as excinfo:
            ConcatWS('a', 'b', separataaa=',')
        assert ('Invalid keyword arguments for ConcatWS: separataaa' in
                str(excinfo.value))

    def test_concat_ws_too_few_fields(self):
        with pytest.raises(ValueError) as excinfo:
            ConcatWS('a')
        assert ('ConcatWS must take at least two expressions' in
                str(excinfo.value))

    def test_concat_ws_then_lookups_from_textfield(self):
        Alphabet.objects.create(d='AAA', e='BBB')
        Alphabet.objects.create(d='AAA', e='CCC')
        ab = (
            Alphabet.objects.annotate(de=ConcatWS('d', 'e', separator=':'))
                            .filter(de__endswith=':BBB')
                            .first()
        )
        assert ab.de == 'AAA:BBB'

    def test_elt_simple(self):
        Alphabet.objects.create(a=2)
        ab = Alphabet.objects.annotate(elt=ELT('a', ['apple', 'orange'])).get()
        assert ab.elt == 'orange'
        ab = Alphabet.objects.annotate(elt=ELT('a', ['apple'])).get()
        assert ab.elt is None

    def test_field_simple(self):
        Alphabet.objects.create(d='a')
        ab = Alphabet.objects.annotate(dp=Field('d', ['a', 'b'])).first()
        assert ab.dp == 1
        ab = Alphabet.objects.annotate(dp=Field('d', ['b', 'a'])).first()
        assert ab.dp == 2
        ab = Alphabet.objects.annotate(dp=Field('d', ['c', 'd'])).first()
        assert ab.dp == 0

    def test_order_by(self):
        Alphabet.objects.create(a=1, d='AAA')
        Alphabet.objects.create(a=2, d='CCC')
        Alphabet.objects.create(a=4, d='BBB')
        Alphabet.objects.create(a=3, d='BBB')
        avalues = list(
            Alphabet.objects.order_by(Field('d', ['AAA', 'BBB']), 'a')
                            .values_list('a', flat=True)
        )
        assert avalues == [2, 1, 3, 4]


class XMLFunctionTests(TestCase):

    def test_updatexml_simple(self):
        Alphabet.objects.create(d='<value>123</value>')
        Alphabet.objects.update(
            d=UpdateXML('d', '/value', '<value>456</value>')
        )
        d = Alphabet.objects.get().d
        assert d == '<value>456</value>'

    def test_updatexml_annotate(self):
        Alphabet.objects.create(d='<value>123</value>')
        d2 = Alphabet.objects.annotate(
            d2=UpdateXML('d', '/value', '<value>456</value>')
        ).get().d2
        assert d2 == '<value>456</value>'

    def test_xmlextractvalue_simple(self):
        Alphabet.objects.create(d='<some><xml /></some>')
        Alphabet.objects.create(d='<someother><xml /></someother>')
        Alphabet.objects.create(d='<some></some><some></some>')
        evs = list(
            Alphabet.objects.annotate(ev=XMLExtractValue('d', 'count(/some)'))
                            .values_list('ev', flat=True)
        )
        assert evs == ['1', '0', '2']

    def test_xmlextractvalue_invalid_xml(self):
        Alphabet.objects.create(d='{"this": "isNotXML"}')
        ab = (
            Alphabet.objects.annotate(ev=XMLExtractValue('d', '/some'))
                            .first()
        )
        assert ab.ev == ''


class EncryptionFunctionTests(TestCase):

    def test_md5_string(self):
        string = 'A string'
        Alphabet.objects.create(d=string)
        pymd5 = hashlib.md5(string.encode('ascii')).hexdigest()
        ab = Alphabet.objects.annotate(md5=MD5('d')).first()
        assert ab.md5 == pymd5

    def test_sha1_string(self):
        string = 'A string'
        Alphabet.objects.create(d=string)
        pysha1 = hashlib.sha1(string.encode('ascii')).hexdigest()
        ab = Alphabet.objects.annotate(sha=SHA1('d')).first()
        assert ab.sha == pysha1

    def test_sha2_string(self):
        string = 'A string'
        Alphabet.objects.create(d=string)

        for hash_len in (224, 256, 384, 512):
            sha_func = getattr(hashlib, 'sha{}'.format(hash_len))
            pysha = sha_func(string.encode('ascii')).hexdigest()
            ab = Alphabet.objects.annotate(sha=SHA2('d', hash_len)).first()
            assert ab.sha == pysha

    def test_sha2_string_hash_len_default(self):
        string = 'A string'
        Alphabet.objects.create(d=string)
        pysha512 = hashlib.sha512(string.encode('ascii')).hexdigest()
        ab = Alphabet.objects.annotate(sha=SHA2('d')).first()
        assert ab.sha == pysha512

    def test_sha2_bad_hash_len(self):
        with pytest.raises(ValueError):
            SHA2('a', 123)


class InformationFunctionTests(TestCase):

    def test_last_insert_id(self):
        Alphabet.objects.create(a=7891)
        Alphabet.objects.update(a=LastInsertId('a') + 1)
        lid = LastInsertId.get()
        assert lid == 7891

    def test_last_insert_id_other_db_connection(self):
        Alphabet.objects.using('other').create(a=9191)
        Alphabet.objects.using('other').update(a=LastInsertId('a') + 9)
        lid = LastInsertId.get(using='other')
        assert lid == 9191

    def test_last_insert_id_in_query(self):
        ab1 = Alphabet.objects.create(a=3719, b=717612)
        ab2 = Alphabet.objects.create(a=1838, b=12636)

        # Delete but store value of b and re-assign it to first second Alphabet
        Alphabet.objects.filter(id=ab1.id, b=LastInsertId('b')).delete()
        Alphabet.objects.filter(id=ab2.id).update(b=LastInsertId())

        ab = Alphabet.objects.get()
        assert ab.b == 717612


class JSONFunctionTests(JSONFieldTestCase):

    def setUp(self):
        super(JSONFunctionTests, self).setUp()
        self.obj = JSONModel.objects.create(attrs={
            'int': 88,
            'flote': 1.5,
            'sub': {
                'document': 'store'
            },
            'arr': ['dee', 'arr', 'arr'],
        })

    def test_json_extract_flote(self):
        results = list(
            JSONModel.objects.annotate(
                x=JSONExtract('attrs', '$.flote')
            ).values_list('x', flat=True)
        )
        assert results == [1.5]
        assert isinstance(results[0], float)

    def test_json_extract_multiple(self):
        results = list(
            JSONModel.objects.annotate(
                x=JSONExtract('attrs', '$.int', '$.flote')
            ).values_list('x', flat=True)
        )
        assert results == [[88, 1.5]]
        assert isinstance(results[0][0], six.integer_types)
        assert isinstance(results[0][1], float)

    def test_json_extract_filter(self):
        results = list(
            JSONModel.objects.annotate(
                x=JSONExtract('attrs', '$.sub')
            ).filter(
                x={'document': 'store'}
            )
        )
        assert results == [self.obj]

    def test_json_keys(self):
        results = list(
            JSONModel.objects.annotate(
                x=JSONKeys('attrs')
            ).values_list('x', flat=True)
        )
        assert set(results[0]) == set(self.obj.attrs.keys())

    def test_json_keys_path(self):
        results = list(
            JSONModel.objects.annotate(
                x=JSONKeys('attrs', '$.sub')
            ).values_list('x', flat=True)
        )
        assert set(results[0]) == set(self.obj.attrs['sub'].keys())

    def test_json_length(self):
        results = list(
            JSONModel.objects.annotate(
                x=JSONLength('attrs')
            ).values_list('x', flat=True)
        )
        assert results == [len(self.obj.attrs)]

    def test_json_length_path(self):
        results = list(
            JSONModel.objects.annotate(
                x=JSONLength('attrs', '$.sub')
            ).values_list('x', flat=True)
        )
        assert results == [len(self.obj.attrs['sub'])]

    def test_json_length_type(self):
        results = list(
            JSONModel.objects.annotate(
                x=JSONLength('attrs')
            ).filter(x__range=[3, 5])
        )
        assert results == [self.obj]

    def test_json_insert(self):
        self.obj.attrs = JSONInsert('attrs', {'$.int': 99, '$.int2': 102})
        self.obj.save()
        self.obj.refresh_from_db()
        assert self.obj.attrs['int'] == 88
        assert self.obj.attrs['int2'] == 102

    def test_json_insert_dict(self):
        self.obj.attrs = JSONInsert(
            'attrs',
            {'$.sub': {'paper': 'drop'}, '$.sub2': {'int': 42, 'foo': 'bar'}}
        )
        self.obj.save()
        self.obj.refresh_from_db()
        assert self.obj.attrs['sub'] == {'document': 'store'}
        assert self.obj.attrs['sub2']['int'] == 42
        assert self.obj.attrs['sub2']['foo'] == 'bar'

    def test_json_insert_array(self):
        self.obj.attrs = JSONInsert(
            'attrs',
            {'$.arr': [1, 'two', 3], '$.arr2': ['one', 2]}
        )
        self.obj.save()
        self.obj.refresh_from_db()
        assert self.obj.attrs['arr'] == ['dee', 'arr', 'arr']
        assert self.obj.attrs['arr2'][0] == 'one'
        assert self.obj.attrs['arr2'][1] == 2

    def test_json_insert_empty_data(self):
        with pytest.raises(ValueError) as excinfo:
            JSONInsert('attrs', {})
        assert '"data" cannot be empty' in str(excinfo.value)

    def test_json_replace_pairs(self):
        self.obj.attrs = JSONReplace('attrs', {'$.int': 101, '$.int2': 102})
        self.obj.save()
        self.obj.refresh_from_db()
        assert self.obj.attrs['int'] == 101
        assert 'int2' not in self.obj.attrs

    def test_json_replace_dict(self):
        self.obj.attrs = JSONReplace(
            'attrs',
            {'$.sub': {'paper': 'drop'}, '$.sub2': {'int': 42, 'foo': 'bar'}}
        )
        self.obj.save()
        self.obj.refresh_from_db()
        assert self.obj.attrs['sub'] == {'paper': 'drop'}
        assert 'sub2' not in self.obj.attrs

    def test_json_replace_array(self):
        self.obj.attrs = JSONReplace(
            'attrs',
            {'$.arr': [1, 'two', 3], '$.arr2': ['one', 2]}
        )
        self.obj.save()
        self.obj.refresh_from_db()
        assert self.obj.attrs['arr'] == [1, 'two', 3]
        assert 'arr2' not in self.obj.attrs

    def test_json_replace_empty_data(self):
        with pytest.raises(ValueError) as excinfo:
            JSONReplace('attrs', {})
        assert '"data" cannot be empty' in str(excinfo.value)

    def test_json_set_pairs(self):
        self.obj.attrs = JSONSet('attrs', {'$.int': 101, '$.int2': 102})
        self.obj.save()
        self.obj.refresh_from_db()
        assert self.obj.attrs['int'] == 101
        assert self.obj.attrs['int2'] == 102

    def test_json_set_dict(self):
        self.obj.attrs = JSONSet(
            'attrs',
            {'$.sub': {'paper': 'drop'}, '$.sub2': {'int': 42, 'foo': 'bar'}}
        )
        self.obj.save()
        self.obj.refresh_from_db()
        assert self.obj.attrs['sub'] == {'paper': 'drop'}
        assert self.obj.attrs['sub2']['int'] == 42
        assert self.obj.attrs['sub2']['foo'] == 'bar'

    def test_json_set_array(self):
        self.obj.attrs = JSONSet(
            'attrs',
            {'$.arr': [1, 'two', 3], '$.arr2': ['one', 2]}
        )
        self.obj.save()
        self.obj.refresh_from_db()
        assert self.obj.attrs['arr'] == [1, 'two', 3]
        assert self.obj.attrs['arr2'][0] == 'one'
        assert self.obj.attrs['arr2'][1] == 2

    def test_json_set_complex_data(self):
        data = {
            'list': ['one', {'int': 2}, None],
            'dict': {
                'sub_list': [1, ['two', 3]],
                'sub_dict': {'paper': 'drop'},
                'sub_null': None,
            },
            'empty': [],
            'null': None,
            'value': 11,
        }
        self.obj.attrs = JSONSet('attrs', {'$.data': data})
        self.obj.save()
        self.obj.refresh_from_db()
        assert self.obj.attrs['data'] == data

    def test_json_set_empty_data(self):
        with pytest.raises(ValueError) as excinfo:
            JSONSet('attrs', {})
        assert '"data" cannot be empty' in str(excinfo.value)


class RegexpFunctionTests(TestCase):

    def setUp(self):
        super(RegexpFunctionTests, self).setUp()
        have_regex_functions = (
            connection_is_mariadb(connection) and
            connection.mysql_version >= (10, 0, 5)
        )
        if not have_regex_functions:
            raise SkipTest("MariaDB 10.0.5+ is required")

    def test_regex_instr(self):
        Alphabet.objects.create(d="ABC")
        Alphabet.objects.create(d="ABBC")
        ab = (
            Alphabet.objects.annotate(d_double_pos=RegexpInstr('d', r'[b]{2}'))
                            .filter(d_double_pos__gt=0)
                            .get()
        )
        assert ab.d == "ABBC"
        assert ab.d_double_pos == 2

    def test_regex_instr_update(self):
        Alphabet.objects.create(d="A string to search")
        Alphabet.objects.create(d="Something to query")
        Alphabet.objects.create(d="Please do inspect me")
        Alphabet.objects.update(
            a=RegexpInstr('d', r'search|query|inspect') - 1
        )
        all_abs = Alphabet.objects.all().order_by('id')
        assert all_abs[0].a == 12
        assert all_abs[1].a == 13
        assert all_abs[2].a == 10

    def test_regex_replace_update(self):
        Alphabet.objects.create(d="I'm feeling sad")
        n = Alphabet.objects.update(d=RegexpReplace('d', r'\bsad\b', 'happy'))
        assert n == 1
        ab = Alphabet.objects.get()
        assert ab.d == "I'm feeling happy"

    def test_regex_replace_update_groups(self):
        Alphabet.objects.create(d="A,,List,with,,empty,,,,strings, ")
        n = Alphabet.objects.update(d=RegexpReplace('d', r',{2,}', ','))
        assert n == 1
        ab = Alphabet.objects.get()
        assert ab.d == "A,List,with,empty,strings, "

    def test_regex_replace_filter_backref(self):
        Author.objects.create(name="Charles Dickens")
        Author.objects.create(name="Roald Dahl")
        qs = (
            Author.objects.annotate(
                surname_first=RegexpReplace('name', r'^(.*) (.*)$', r'\2, \1')
            ).order_by('surname_first')
        )
        assert qs[0].name == "Roald Dahl"
        assert qs[1].name == "Charles Dickens"

    def test_regex_substr(self):
        Alphabet.objects.create(d='The <tag> is there')
        qs = (
            Alphabet.objects.annotate(d_tag=RegexpSubstr('d', r'<[^>]+>'))
                            .filter(d_tag__gt='')
        )
        ab = qs.get()
        assert ab.d_tag == '<tag>'

    def test_regex_substr_field(self):
        Alphabet.objects.create(d='This is the string', e=r'\bis\b')
        qs = (
            Alphabet.objects.annotate(substr=RegexpSubstr('d', F('e')))
                            .filter(substr__gt='')
                            .values_list('substr', flat=True)
        )
        substr = qs[0]
        assert substr == 'is'

    def test_regex_substr_filter(self):
        Author.objects.create(name="Euripides")
        Author.objects.create(name="Frank Miller")
        Author.objects.create(name="Sophocles")
        qs = list(
            Author.objects.annotate(
                name_has_space=Length(RegexpSubstr('name', r'\s'))
            ).filter(name_has_space=0)
            .order_by('id').values_list('name', flat=True)
        )
        assert qs == ['Euripides', 'Sophocles']


class DynamicColumnsFunctionTests(DynColTestCase):

    def setUp(self):
        super(DynamicColumnsFunctionTests, self).setUp()
        DynamicModel.objects.create(attrs={
            'flote': 1.0,
            'sub': {
                'document': 'store'
            }
        })

    def test_get_float(self):
        results = list(
            DynamicModel.objects.annotate(
                x=ColumnGet('attrs', 'flote', 'DOUBLE')
            ).values_list('x', flat=True)
        )
        assert results == [1.0]
        assert isinstance(results[0], float)

    def test_get_int(self):
        results = list(
            DynamicModel.objects.annotate(
                x=ColumnGet('attrs', 'flote', 'INTEGER')
            ).values_list('x', flat=True)
        )
        assert results == [1]
        assert isinstance(results[0], int)

    def test_get_null(self):
        results = list(
            DynamicModel.objects.annotate(
                x=ColumnGet('attrs', 'nonexistent', 'INTEGER')
            ).values_list('x', flat=True)
        )
        assert results == [None]

    def test_get_nested(self):
        results = list(
            DynamicModel.objects.annotate(
                x=ColumnGet(
                    ColumnGet('attrs', 'sub', 'BINARY'),
                    'document',
                    'CHAR'
                )
            ).values_list('x', flat=True)
        )
        assert results == ['store']

    def test_get_invalid_data_type(self):
        with pytest.raises(ValueError) as excinfo:
            ColumnGet('bla', 'key', 'INTGRRR')
        assert "Invalid data_type 'INTGRRR'" in str(excinfo.value)

    def test_add(self):
        results = list(
            DynamicModel.objects.annotate(
                attrs2=ColumnAdd('attrs', {'another': 'key'})
            ).values_list('attrs2', flat=True)
        )
        assert results == [{
            'flote': 1.0,
            'sub': {'document': 'store'},
            'another': 'key'
        }]

    def test_add_nested(self):
        with pytest.raises(ValueError) as excinfo:
            list(
                DynamicModel.objects.annotate(
                    attrs2=ColumnAdd('attrs', {'sub2': {'document': 'store'}})
                ).values_list('attrs2', flat=True)
            )
        assert "nested values is not supported" in str(excinfo.value)

    def test_add_update(self):
        DynamicModel.objects.update(attrs=ColumnAdd('attrs', {'over': 9000}))
        m = DynamicModel.objects.get()
        assert m.attrs == {
            'flote': 1.0,
            'sub': {'document': 'store'},
            'over': 9000,
        }

    def test_as_type_instantiation(self):
        with pytest.raises(ValueError) as excinfo:
            AsType(1, 'PANTS')
        assert "Invalid data_type 'PANTS'" in str(excinfo.value)

    def test_add_update_typed(self):
        DynamicModel.objects.update(
            attrs=ColumnAdd('attrs', {'over': AsType(9000, 'DOUBLE')})
        )
        m = DynamicModel.objects.get()
        assert isinstance(m.attrs['over'], float)
        assert m.attrs['over'] == 9000.0

    def test_delete(self):
        DynamicModel.objects.update(attrs=ColumnDelete('attrs', 'sub'))
        m = DynamicModel.objects.get()
        assert m.attrs == {'flote': 1.0}

    def test_delete_subfunc(self):
        say_sub = ConcatWS(Value('s'), Value('ub'), separator='')
        DynamicModel.objects.update(attrs=ColumnDelete('attrs', say_sub))
        m = DynamicModel.objects.get()
        assert m.attrs == {'flote': 1.0}
