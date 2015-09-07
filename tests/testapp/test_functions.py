# -*- coding:utf-8 -*-
import hashlib
from unittest import SkipTest, skipIf

import django
import pytest
from django.db import connection
from django.db.models import F
from django.test import TestCase

from django_mysql.models.functions import (
    CRC32, ELT, MD5, SHA1, SHA2, Abs, Ceiling, ConcatWS, Field, Floor,
    Greatest, LastInsertId, Least, RegexpInstr, RegexpReplace, RegexpSubstr,
    Round, Sign
)
from testapp.models import Alphabet, Author

try:
    from django.db.models.functions import Length
except ImportError:
    Length = None

requiresDatabaseFunctions = skipIf(
    django.VERSION <= (1, 8),
    "Requires Database Functions from Django 1.8+"
)


@requiresDatabaseFunctions
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


@requiresDatabaseFunctions
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


@requiresDatabaseFunctions
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


@requiresDatabaseFunctions
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


@requiresDatabaseFunctions
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


@requiresDatabaseFunctions
class RegexpFunctionTests(TestCase):

    def setUp(self):
        super(RegexpFunctionTests, self).setUp()
        have_regex_functions = (
            (connection.is_mariadb and connection.mysql_version >= (10, 0, 5))
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


@skipIf(django.VERSION >= (1, 8),
        "Requires old Django version without Database Functions")
class OldDjangoFunctionTests(TestCase):

    def test_single_arg_doesnt_work(self):
        with pytest.raises(ValueError):
            CRC32('name')

    def test_multi_arg_doesnt_work(self):
        with pytest.raises(ValueError):
            Greatest('a', 'b')

    def test_concat_ws_doesnt_work(self):
        with pytest.raises(ValueError):
            ConcatWS('a', 'b', separator='::')
