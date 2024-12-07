from __future__ import annotations

import datetime as dt
import json
from typing import Any

from django.core import checks
from django.db import connection
from django.db.models import CASCADE
from django.db.models import CharField
from django.db.models import DateTimeField
from django.db.models import DecimalField
from django.db.models import ForeignKey
from django.db.models import Index
from django.db.models import IntegerField
from django.db.models import JSONField
from django.db.models import Model as VanillaModel
from django.db.models import OneToOneField
from django.db.models import TextField
from django.utils import timezone

from django_mysql.models import Bit1BooleanField
from django_mysql.models import DynamicField
from django_mysql.models import EnumField
from django_mysql.models import FixedCharField
from django_mysql.models import ListCharField
from django_mysql.models import ListTextField
from django_mysql.models import Model
from django_mysql.models import PositiveTinyIntegerField
from django_mysql.models import SetCharField
from django_mysql.models import SetTextField
from django_mysql.models import SizedBinaryField
from django_mysql.models import SizedTextField
from django_mysql.models import TinyIntegerField
from tests.testapp.utils import conn_is_mysql


class EnumModel(Model):
    field = EnumField(
        choices=[
            ("red", "Red"),
            ("bloodred", "Blood Red"),
            "green",
            ("blue", "Navy Blue"),
            ("coralblue", "Coral Blue"),
        ]
    )


class NullableEnumModel(Model):
    field = EnumField(
        choices=["goat", ("deer", "Deer"), "bull", "dog's"],  # Test if escaping works
        null=True,
    )


class CharSetModel(Model):
    field = SetCharField(base_field=CharField(max_length=8), size=3, max_length=32)
    field2 = SetCharField(base_field=CharField(max_length=8), max_length=255)


class CharListModel(Model):
    field = ListCharField(base_field=CharField(max_length=8), size=3, max_length=32)


class IntSetModel(Model):
    field = SetCharField(base_field=IntegerField(), size=5, max_length=32)


class IntListModel(Model):
    field = ListCharField(base_field=IntegerField(), size=5, max_length=32)


class CharSetDefaultModel(Model):
    field = SetCharField(
        base_field=CharField(max_length=5),
        size=5,
        max_length=32,
        default=lambda: {"a", "d"},
    )


class CharListDefaultModel(Model):
    field = ListCharField(
        base_field=CharField(max_length=5),
        size=5,
        max_length=32,
        default=lambda: ["a", "d"],
    )


class BigCharSetModel(Model):
    field = SetTextField(base_field=CharField(max_length=8), max_length=32)


class BigCharListModel(Model):
    field = ListTextField(base_field=CharField(max_length=8))


class BigIntSetModel(Model):
    field = SetTextField(base_field=IntegerField())


class BigIntListModel(Model):
    field = ListTextField(base_field=IntegerField())


class DynamicModel(Model):
    attrs = DynamicField(
        spec={
            "datetimey": dt.datetime,
            "datey": dt.date,
            "floaty": float,
            "inty": int,
            "stry": str,
            "timey": dt.time,
            "nesty": {"level2": str},
        }
    )

    @classmethod
    def check(cls, **kwargs: Any) -> list[checks.CheckMessage]:
        # Disable the checks on MySQL so that checks tests don't fail
        if conn_is_mysql(connection) and not connection.mysql_is_mariadb:
            return []
        return super().check(**kwargs)

    def __str__(self):  # pragma: no cover
        return ",".join(f"{key}:{value}" for key, value in self.attrs.items())


class SpeclessDynamicModel(Model):
    attrs = DynamicField()

    @classmethod
    def check(cls, **kwargs):
        # Disable the checks on MySQL so that checks tests don't fail
        if conn_is_mysql(connection) and not connection.mysql_is_mariadb:
            return []
        return super().check(**kwargs)

    def __str__(self):  # pragma: no cover
        return ",".join(f"{key}:{value}" for key, value in self.attrs.items())


class FixedCharModel(Model):
    zip_code = FixedCharField(max_length=10)


class TinyIntegerModel(Model):
    tiny_signed = TinyIntegerField(null=True)
    tiny_unsigned = PositiveTinyIntegerField(null=True)


class Author(Model):
    name = CharField(max_length=32, db_index=True)
    tutor = ForeignKey("self", on_delete=CASCADE, null=True, related_name="tutees")
    bio = TextField()
    birthday = DateTimeField(null=True)
    deathday = DateTimeField(null=True)


class Book(Model):
    title = CharField(max_length=32, db_index=True)
    author = ForeignKey(Author, on_delete=CASCADE, related_name="books")


class VanillaAuthor(VanillaModel):
    name = CharField(max_length=32)


class AuthorExtra(Model):
    author = OneToOneField(Author, on_delete=CASCADE, primary_key=True)
    legs = IntegerField(default=2)


class NameAuthor(Model):
    name = CharField(max_length=32, primary_key=True)


class NameAuthorExtra(Model):
    name = OneToOneField(NameAuthor, on_delete=CASCADE, primary_key=True)


class AuthorMultiIndex(Model):
    class Meta:
        indexes = [
            Index(fields=("name", "country"), name="testapp_authormultiindex_uniq")
        ]

    name = CharField(max_length=32, db_index=True)
    country = CharField(max_length=32)


class AuthorHugeName(Model):
    class Meta:
        db_table = "this_is_an_author_with_an_incredibly_long_table_name_" "you_know_it"

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
        db_table = "titled aged customer"  # Test name quoting

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
    flag_a: Any = Bit1BooleanField(default=True)
    flag_b: Any = Bit1BooleanField(default=False)


class JSONModel(Model):
    attrs = JSONField(null=True)

    name = CharField(max_length=3)

    def __str__(self):  # pragma: no cover
        return str(json.dumps(self.attrs))


# For cache tests


class ExpensiveCalculation:
    def __init__(self) -> None:
        self.num_calls = 0

    def __call__(self) -> dt.datetime:
        self.num_calls += 1
        return timezone.now()

    def reset(self) -> None:
        self.num_calls = 0

    def call_count(self) -> int:
        return self.num_calls


expensive_calculation = ExpensiveCalculation()


class Poll(VanillaModel):
    question = CharField(max_length=200)
    answer = CharField(max_length=200)
    pub_date = DateTimeField("date published", default=expensive_calculation)
