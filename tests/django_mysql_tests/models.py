# -*- coding:utf-8 -*-
from django.utils import timezone

from django.db.models import (
    CharField, DateTimeField, DecimalField, ForeignKey, IntegerField,
    Model as VanillaModel
)

from django_mysql.models import (
    ListCharField, ListTextField, Model, SetCharField, SetTextField
)


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


class Author(Model):
    name = CharField(max_length=32, db_index=True)
    tutor = ForeignKey('self', null=True, related_name='tutees')

    def __unicode__(self):
        return "{} {}".format(self.id, self.name)


class VanillaAuthor(VanillaModel):
    name = CharField(max_length=32)

    def __unicode__(self):
        return "{} {}".format(self.id, self.name)


class NameAuthor(Model):
    name = CharField(max_length=32, primary_key=True)

    def __unicode__(self):
        return "{} {}".format(self.id, self.name)


class AuthorMultiIndex(Model):
    class Meta(object):
        index_together = ('name', 'country')

    name = CharField(max_length=32)
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
