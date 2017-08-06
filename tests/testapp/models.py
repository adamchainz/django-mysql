# -*- coding:utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import json
from datetime import date, datetime, time

from django.db import connection
from django.db.models import Model as VanillaModel
from django.db.models import (
    CharField, DateTimeField, DecimalField, ForeignKey, IntegerField,
    OneToOneField, TextField
)
from django.utils import six, timezone

from django_mysql.models import (
    Bit1BooleanField, DynamicField, EnumField, JSONField, ListCharField,
    ListTextField, Model, NullBit1BooleanField, SetCharField, SetTextField,
    SizedBinaryField, SizedTextField
)
from django_mysql.utils import connection_is_mariadb


class TemporaryModel(Model):
    """
    Used for temporary, mostly invalid models created in tests - check() is
    disabled unless an extra parameter is provided, in case the checks get run
    during tests, e.g. from call_command.
    """
    class Meta:
        app_label = 'testapp'
        abstract = True

    @classmethod
    def check(cls, **kwargs):
        actually_check = kwargs.pop('actually_check', False)
        if actually_check:
            return super(TemporaryModel, cls).check(**kwargs)
        else:
            return []


class EnumModel(Model):
    field = EnumField(choices=[
        ('red', 'Red'),
        ('bloodred', 'Blood Red'),
        'green',
        ('blue', 'Navy Blue'),
        ('coralblue', 'Coral Blue'),
    ])


class NullableEnumModel(Model):
    field = EnumField(choices=[
        'goat',
        ('deer', 'Deer'),
        'bull',
        "dog's",   # Test if escaping works
    ], null=True)


class CharSetModel(Model):
    field = SetCharField(
        base_field=CharField(max_length=8),
        size=3,
        max_length=32,
    )
    field2 = SetCharField(
        base_field=CharField(max_length=8),
        max_length=255
    )


class CharListModel(Model):
    field = ListCharField(
        base_field=CharField(max_length=8),
        size=3,
        max_length=32,
    )


class IntSetModel(Model):
    field = SetCharField(base_field=IntegerField(), size=5, max_length=32)


class IntListModel(Model):
    field = ListCharField(base_field=IntegerField(), size=5, max_length=32)


class CharSetDefaultModel(Model):
    field = SetCharField(base_field=CharField(max_length=5),
                         size=5,
                         max_length=32,
                         default=lambda: {"a", "d"})


class CharListDefaultModel(Model):
    field = ListCharField(base_field=CharField(max_length=5),
                          size=5,
                          max_length=32,
                          default=lambda: ["a", "d"])


class BigCharSetModel(Model):
    field = SetTextField(
        base_field=CharField(max_length=8),
        max_length=32,
    )


class BigCharListModel(Model):
    field = ListTextField(base_field=CharField(max_length=8))


class BigIntSetModel(Model):
    field = SetTextField(base_field=IntegerField())


class BigIntListModel(Model):
    field = ListTextField(base_field=IntegerField())


class DynamicModel(Model):
    attrs = DynamicField(
        spec={
            'datetimey': datetime,
            'datey': date,
            'floaty': float,
            'inty': int,
            'stry': six.text_type,
            'timey': time,
            'nesty': {
                'level2': six.text_type
            }
        }
    )

    @classmethod
    def check(cls, **kwargs):
        # Disable the checks on MySQL so that checks tests don't fail
        if not (
            connection_is_mariadb(connection) and
            connection.mysql_version >= (10, 0, 1)
        ):
            return []
        return super(DynamicModel, cls).check(**kwargs)

    def __unicode__(self):
        return ",".join(
            '{}:{}'.format(key, value)
            for key, value in six.iteritems(self.attrs)
        )


class Author(Model):
    name = CharField(max_length=32, db_index=True)
    tutor = ForeignKey('self', null=True, related_name='tutees')
    bio = TextField()
    birthday = DateTimeField(null=True)
    deathday = DateTimeField(null=True)

    def __unicode__(self):
        return "{} {}".format(self.id, self.name)


class Book(Model):
    title = CharField(max_length=32, db_index=True)
    author = ForeignKey(Author, related_name='books')


class VanillaAuthor(VanillaModel):
    name = CharField(max_length=32)

    def __unicode__(self):
        return "{} {}".format(self.id, self.name)


class AuthorExtra(Model):
    author = OneToOneField(Author, primary_key=True)
    legs = IntegerField(default=2)


class NameAuthor(Model):
    name = CharField(max_length=32, primary_key=True)

    def __unicode__(self):
        return "{} {}".format(self.id, self.name)


class NameAuthorExtra(Model):
    name = OneToOneField(NameAuthor, primary_key=True)


class AuthorMultiIndex(Model):
    class Meta(object):
        index_together = ('name', 'country')

    name = CharField(max_length=32, db_index=True)
    country = CharField(max_length=32)

    def __unicode__(self):
        return "{} {} in {}".format(self.id, self.name, self.country)


class AuthorHugeName(Model):
    class Meta(object):
        db_table = 'this_is_an_author_with_an_incredibly_long_table_name_' \
                   'you_know_it'

    name = CharField(max_length=32)


class Alphabet(Model):
    a = IntegerField(default=1)
    b = IntegerField(default=2)
    c = IntegerField(default=3)
    d = CharField(max_length=32)
    e = CharField(max_length=32, null=True)
    f = IntegerField(null=True)
    g = DecimalField(default=0, decimal_places=2, max_digits=10)


class ProxyAlphabet(Alphabet):
    class Meta:
        proxy = True

    @property
    def a_times_b(self):
        return self.a * self.b


class Customer(Model):
    name = CharField(max_length=32)


class AgedCustomer(Customer):
    age = IntegerField(default=21)


class TitledAgedCustomer(AgedCustomer):
    class Meta:
        db_table = 'titled aged customer'  # Test name quoting
    title = CharField(max_length=16)


class SizeFieldModel(Model):
    binary1 = SizedBinaryField(size_class=1)
    binary2 = SizedBinaryField(size_class=2)
    binary3 = SizedBinaryField(size_class=3)
    binary4 = SizedBinaryField(size_class=4)
    text1 = SizedTextField(size_class=1)
    text2 = SizedTextField(size_class=2)
    text3 = SizedTextField(size_class=3)
    text4 = SizedTextField(size_class=4)


class Bit1Model(Model):
    flag_a = Bit1BooleanField(default=True)
    flag_b = Bit1BooleanField(default=False)


class NullBit1Model(Model):
    flag = NullBit1BooleanField()


class JSONModel(Model):
    if (
        not connection_is_mariadb(connection._nodb_connection) and
        connection._nodb_connection.mysql_version >= (5, 7)
    ):
        attrs = JSONField(null=True)

    def __unicode__(self):
        return six.text_type(json.dumps(self.attrs))


# For cache tests

def expensive_calculation():
    expensive_calculation.num_runs += 1
    return timezone.now()


class Poll(VanillaModel):
    question = CharField(max_length=200)
    answer = CharField(max_length=200)
    pub_date = DateTimeField(
        'date published',
        default=expensive_calculation
    )
