# -*- coding:utf-8 -*-
from django.db.models import CharField, ForeignKey, Model as VanillaModel

from django_mysql.fields import SetCharField
from django_mysql.models import Model


class Settee(Model):
    features = SetCharField(
        base_field=CharField(max_length=8),
        size=3,
        max_length=32,
    )

    def __unicode__(self):
        return "{} {}".format(self.id, ",".join(self.features))


class Author(Model):
    name = CharField(max_length=32, db_index=True)
    tutor = ForeignKey('self', null=True)

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
