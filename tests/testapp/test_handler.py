# -*- coding:utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import pytest
from django.db import connection
from django.db.models import F
from django.test import TestCase

from django_mysql.models.handler import Handler
from django_mysql.utils import index_name
from testapp.models import (
    Author, AuthorHugeName, AuthorMultiIndex, NameAuthor, VanillaAuthor
)


def get_index_names(model):
    # There's no easy way of getting index names in django so pull them from
    # INFORMATION_SCHEMA
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT DISTINCT INDEX_NAME
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = %s AND
                  TABLE_NAME = %s""",
            (connection.settings_dict['NAME'], model._meta.db_table)
        )

        index_names = [x[0] for x in cursor.fetchall()]
    return index_names


class HandlerCreationTests(TestCase):

    def test_bad_creation_joins_not_allowed(self):
        qs = Author.objects.filter(tutor__name='A')
        with pytest.raises(ValueError):
            qs.handler()

    def test_bad_creation_limit_not_allowed(self):
        qs = Author.objects.all()[:100]
        with pytest.raises(ValueError):
            qs.handler()

    def test_bad_creation_ordering_not_allowed(self):
        qs = Author.objects.order_by('name')
        with pytest.raises(ValueError):
            qs.handler()

    def test_can_open_close_with_huge_table_name(self):
        with AuthorHugeName.objects.handler():
            pass

    def test_cannot_open_twice(self):
        handler = Author.objects.handler()
        with handler:
            with pytest.raises(ValueError):
                with handler:
                    pass

    def test_cannot_close_unopened(self):
        handler = Author.objects.handler()
        with pytest.raises(ValueError):
            handler.__exit__(None, None, None)


class BaseAuthorTestCase(TestCase):

    def setUp(self):
        self.jk = Author.objects.create(name='JK Rowling')
        self.grisham = Author.objects.create(name='John Grisham')


class HandlerReadTests(BaseAuthorTestCase):

    def test_bad_read_unopened(self):
        handler = Author.objects.all().handler()
        with pytest.raises(RuntimeError):
            handler.read()

    def test_bad_read_mode(self):
        with Author.objects.handler() as handler:
            with pytest.raises(ValueError):
                handler.read(mode='non-existent')

    def test_read_does_single_by_default(self):
        with Author.objects.handler() as handler:
            handler_all = list(handler.read())
        assert handler_all == [self.jk]

    def test_read_limit_first(self):
        with Author.objects.handler() as handler:
            handler_first = handler.read(limit=1)[0]
        qs_first = Author.objects.earliest('id')

        assert handler_first == qs_first

    def test_read_limit_last(self):
        with Author.objects.handler() as handler:
            handler_last = handler.read(mode='last', limit=1)[0]
        qs_last = Author.objects.latest('id')

        assert handler_last == qs_last

    def test_read_limit_all(self):
        with Author.objects.handler() as handler:
            handler_all = list(handler.read(limit=2))
        qs_all = list(Author.objects.all())

        assert handler_all == qs_all

    def test_read_index_primary(self):
        with Author.objects.handler() as handler:
            handler_all = list(handler.read(index='PRIMARY', limit=2))
        qs_all = list(Author.objects.order_by('id'))

        assert handler_all == qs_all

    def test_read_index_different(self):
        index_name = [name for name in get_index_names(Author)
                      if name != "PRIMARY"][0]

        with Author.objects.handler() as handler:
            handler_all = list(handler.read(index=index_name, limit=2))
        qs_all = list(Author.objects.order_by('name').all())

        assert handler_all == qs_all

    def test_read_where_filter_read(self):
        qs = Author.objects.filter(name__startswith='John')

        with qs.handler() as handler:
            handler_all = list(handler.read())
        qs_all = list(qs)

        assert handler_all == qs_all

    def test_read_where_filter_f_expression(self):
        qs = Author.objects.filter(name=F('name'))

        with qs.handler() as handler:
            handler_all = list(handler.read(limit=100))

        assert len(handler_all) == 2

    def test_read_where_exclude(self):
        qs = Author.objects.filter(name__contains='JK')

        with qs.handler() as handler:
            handler_all = list(handler.read())
        qs_all = list(qs)

        assert handler_all == qs_all

    def test_read_where_filter_params_not_injected_or_modified(self):
        table_col = "`looks_like`.`table_column`"
        author = Author.objects.create(name=table_col)
        qs = Author.objects.filter(name=table_col)

        with qs.handler() as handler:
            handler_first = handler.read()[0]

        assert handler_first == author

    def test_read_where_passed_in(self):
        qs = Author.objects.filter(name__startswith='John')

        with Author.objects.handler() as handler:
            handler_author = handler.read(where=qs)[0]

        assert handler_author == qs[0]

    def test_read_where_passed_in_overrides_completely(self):
        qs = Author.objects.filter(name='JK Rowling')
        qs2 = Author.objects.filter(name='John Grisham')

        with qs.handler() as handler:
            handler_default = handler.read()[0]
            handler_where = handler.read(where=qs2)[0]

        assert handler_default == qs[0]
        assert handler_where == qs2[0]

    def test_read_bad_where_passed_in(self):
        with Author.objects.handler() as handler:
            with pytest.raises(ValueError):
                handler.read(where=Author.objects.filter(tutor__name='A'))

    def test_read_index_value_and_mode_invalid(self):
        with Author.objects.handler() as handler:
            with pytest.raises(ValueError):
                handler.read(value=1, mode='first')

    def test_read_index_equal(self):
        with Author.objects.handler() as handler:
            handler_result = handler.read(value=self.jk.id)[0]
        assert handler_result == self.jk

    def test_read_index_equal_exact(self):
        with Author.objects.handler() as handler:
            handler_result = handler.read(value__exact=self.jk.id)[0]
        assert handler_result == self.jk

    def test_read_index_less_than(self):
        with Author.objects.handler() as handler:
            handler_result = handler.read(value__lt=self.jk.id + 1)[0]
        assert handler_result == self.jk

    def test_read_index_less_than_equal(self):
        with Author.objects.handler() as handler:
            handler_result = handler.read(value__lte=self.jk.id)[0]
        assert handler_result == self.jk

    def test_read_index_greater_than_equal(self):
        with Author.objects.handler() as handler:
            handler_result = handler.read(value__gte=self.jk.id)[0]
        assert handler_result == self.jk

    def test_read_index_greater_than(self):
        with Author.objects.handler() as handler:
            handler_result = handler.read(value__gt=self.jk.id)[0]
        assert handler_result == self.grisham

    def test_read_index_too_many_filters(self):
        with Author.objects.handler() as handler:
            with pytest.raises(ValueError):
                handler.read(value__lte=1, value__gte=1)

    def test_read_index_bad_operator(self):
        with Author.objects.handler() as handler:
            with pytest.raises(ValueError):
                handler.read(value__flange=1)

    def test_read_bad_argument(self):
        with Author.objects.handler() as handler:
            with pytest.raises(ValueError):
                handler.read(pk=1)

    def test_read_bad_argument_underscores(self):
        with Author.objects.handler() as handler:
            with pytest.raises(ValueError):
                handler.read(value_exact=1)


class HandlerIterTests(BaseAuthorTestCase):

    def test_iter_all(self):
        with Author.objects.handler() as handler:
            seen_ids = [author.id for author in handler.iter()]

        assert seen_ids == [self.jk.id, self.grisham.id]

    def test_iter_chunk_size_1(self):
        with Author.objects.handler() as handler:
            seen_ids = [author.id for author in handler.iter(chunk_size=1)]

        assert seen_ids == [self.jk.id, self.grisham.id]

    def test_iter_reverse(self):
        with Author.objects.handler() as handler:
            seen_ids = [author.id for author in handler.iter(reverse=True)]

        assert seen_ids == [self.grisham.id, self.jk.id]

    def test_iter_reverse_chunk_size_1(self):
        with Author.objects.handler() as handler:
            seen_ids = [author.id for author in
                        handler.iter(chunk_size=1, reverse=True)]

        assert seen_ids == [self.grisham.id, self.jk.id]

    def test_bad_iter_unopened(self):
        handler = Author.objects.all().handler()
        with pytest.raises(RuntimeError):
            sum(1 for x in handler.iter())

    def test_iter_where_preset(self):
        where_qs = Author.objects.filter(name__startswith='John')

        with where_qs.handler() as handler:
            seen_ids = [author.id for author in handler.iter()]

        assert seen_ids == [self.grisham.id]

    def test_iter_where_passed_in(self):
        where_qs = Author.objects.filter(name__startswith='John')

        with Author.objects.handler() as handler:
            seen_ids = [author.id for author in handler.iter(where=where_qs)]

        assert seen_ids == [self.grisham.id]

    def test_iter_loses_its_place(self):
        portis = Author.objects.create(name='Charles Portis')

        with Author.objects.handler() as handler:
            iterator = handler.iter(chunk_size=1)
            assert next(iterator) == self.jk
            assert next(iterator) == self.grisham

            iterator2 = handler.iter(chunk_size=1, reverse=True)
            assert next(iterator2) == portis

            # This SHOULD be portis, but it thinks it's exhausted already
            # because iterator2 reset the iteration in reverse, and now for the
            # NEXT page after the LAST
            with pytest.raises(StopIteration):
                assert next(iterator) == portis


class HandlerMultipartIndexTests(TestCase):

    def setUp(self):
        super(HandlerMultipartIndexTests, self).setUp()
        self.smith1 = AuthorMultiIndex.objects.create(name='John Smith',
                                                      country='Scotland')
        self.smith2 = AuthorMultiIndex.objects.create(name='John Smith',
                                                      country='England')
        self.index_name = index_name(AuthorMultiIndex, 'name', 'country')

    def test_read_all(self):
        with AuthorMultiIndex.objects.handler() as handler:
            handler_all = list(handler.read(index=self.index_name, limit=2))
        qs_all = list(AuthorMultiIndex.objects.order_by('name', 'country'))
        assert handler_all == qs_all

    def test_read_index_multipart(self):
        with AuthorMultiIndex.objects.handler() as handler:
            value = ('John Smith', 'England')
            result = handler.read(index=self.index_name, value=value)[0]

        assert result == self.smith2


class HandlerNestingTests(BaseAuthorTestCase):

    def setUp(self):
        super(HandlerNestingTests, self).setUp()

        self.jk_name = NameAuthor.objects.create(name='JK Rowling')
        self.grisham_name = NameAuthor.objects.create(name='John Grisham')

    def test_can_nest(self):
        ahandler = Author.objects.handler()
        bhandler = NameAuthor.objects.handler()
        with ahandler, bhandler:
            handler_plain = ahandler.read()[0]
            handler_name = bhandler.read()[0]

        assert handler_plain == self.jk
        assert handler_name == self.jk_name

    def test_can_nest_two_for_same_table(self):
        ahandler = Author.objects.handler()
        bhandler = Author.objects.handler()

        with ahandler, bhandler:
            first = ahandler.read()[0]
            second = bhandler.read()[0]

        assert first == self.jk
        assert second == self.jk


class HandlerStandaloneTests(TestCase):

    def setUp(self):
        super(HandlerStandaloneTests, self).setUp()
        self.jk = VanillaAuthor.objects.create(name='JK Rowling')
        self.grisham = VanillaAuthor.objects.create(name='John Grisham')

    def test_vanilla_works(self):
        handler = Handler(VanillaAuthor.objects.all())
        with handler:
            first = handler.read()[0]

        assert first == self.jk

    def test_vanilla_filters(self):
        qs = VanillaAuthor.objects.filter(name__startswith='John')
        with Handler(qs) as handler:
            first = handler.read()[0]

        assert first == self.grisham


class HandlerMultiDBTests(TestCase):

    def setUp(self):
        super(HandlerMultiDBTests, self).setUp()
        self.jk = Author.objects.using('other').create(name='JK Rowling')
        self.grisham = Author.objects.create(name='John Grisham')

    def test_queryset_db_is_used(self):
        handler = Author.objects.using('other').handler()
        with handler:
            handler_result = handler.read()[0]

        assert handler_result == self.jk
