import pickle
import re
from unittest import mock, skipUnless

import pytest
from django.contrib.contenttypes.models import ContentType
from django.db import DEFAULT_DB_ALIAS, connections
from django.db.models.query import QuerySet
from django.template import Context, Template
from django.test import TestCase
from django.test.utils import captured_stdout, override_settings

from django_mysql.models import ApproximateInt, SmartIterator, add_QuerySetMixin
from django_mysql.utils import have_program, index_name
from tests.testapp.models import (
    Author,
    AuthorExtra,
    AuthorMultiIndex,
    Book,
    NameAuthor,
    NameAuthorExtra,
    VanillaAuthor,
)
from tests.testapp.utils import CaptureLastQuery, skip_if_mysql_8_plus, used_indexes


class MixinQuerysetTests(TestCase):
    def test_ContentType(self):
        qs = ContentType.objects.all()
        assert not hasattr(qs, "approx_count")
        qs2 = add_QuerySetMixin(qs)

        assert hasattr(qs2, "approx_count")
        assert qs.__class__ != qs2.__class__
        assert qs.__class__ in qs2.__class__.__mro__


class ApproximateCountTests(TestCase):
    def setUp(self):
        super().setUp()
        Author.objects.bulk_create([Author() for i in range(10)])

    def test_activation_deactivation(self):
        qs = Author.objects.all()
        assert not qs._count_tries_approx

        qs2 = qs.count_tries_approx(min_size=2)
        assert qs != qs2
        assert qs2._count_tries_approx
        count = qs2.count()
        assert isinstance(count, ApproximateInt)

        qs3 = qs2.count_tries_approx(False)
        assert qs2 != qs3
        assert not qs3._count_tries_approx

    def test_activation_but_fallback(self):
        qs = Author.objects.exclude(name="TEST").count_tries_approx()
        count = qs.count()
        assert count == 10
        assert not isinstance(count, ApproximateInt)

    def test_activation_but_fallback_due_to_min_size(self):
        qs = Author.objects.count_tries_approx()
        count = qs.count()
        assert count == 10
        assert not isinstance(count, ApproximateInt)

    def test_output_in_templates(self):
        approx_count = Author.objects.approx_count(min_size=1)
        text = Template("{{ var }}").render(Context({"var": approx_count}))
        assert text.startswith("Approximately ")

        approx_count2 = Author.objects.approx_count(min_size=1, return_approx_int=False)
        text = Template("{{ var }}").render(Context({"var": approx_count2}))
        assert not text.startswith("Approximately ")

    def test_fallback_with_filters(self):
        filtered = Author.objects.filter(name="")
        assert filtered.approx_count(fall_back=True) == 10
        with pytest.raises(ValueError):
            filtered.approx_count(fall_back=False)

    def test_fallback_with_slice(self):
        assert Author.objects.all()[:100].approx_count() == 10
        with pytest.raises(ValueError):
            Author.objects.all()[:100].approx_count(fall_back=False)

    def test_fallback_with_distinct(self):
        assert Author.objects.distinct().approx_count() == 10
        with pytest.raises(ValueError):
            Author.objects.distinct().approx_count(fall_back=False)

    def test_fallback_with_arbitrary_extra(self):
        assert Author.objects.extra(where=["1=1"]).approx_count() == 10
        with pytest.raises(ValueError):
            Author.objects.extra(where=["1=1"]).approx_count(fall_back=False)

    def test_approx_count_with_label(self):
        # It should be possible to approx count a query set with a query hint
        # as none of them affect the result
        assert Author.objects.label("bla").approx_count(fall_back=False) == 10

    def test_approx_count_with_straight_join(self):
        # It should be possible to approx count a query set with a query hint
        # as none of them affect the result
        assert Author.objects.straight_join().approx_count(fall_back=False) == 10


class QueryHintTests(TestCase):
    def test_label(self):
        with CaptureLastQuery() as cap:
            list(Author.objects.label("QueryHintTests.test_label").all())
        assert cap.query.startswith("SELECT /*QueryHintTests.test_label*/ ")

    def test_label_twice(self):
        with CaptureLastQuery() as cap:
            list(Author.objects.label("QueryHintTests").label("test_label_twice").all())
        assert cap.query.startswith("SELECT /*QueryHintTests*/ /*test_label_twice*/ ")

    def test_label_star(self):
        with CaptureLastQuery() as cap:
            list(Author.objects.label("I'ma*").label("*").all())
        assert cap.query.startswith("SELECT /*I'ma**/ /***/ ")

    def test_label_update(self):
        Author.objects.create(name="UPDATEME")
        with CaptureLastQuery() as cap:
            Author.objects.label("QueryHintTests").update(name="UPDATED")
        assert cap.query.startswith("UPDATE /*QueryHintTests*/ ")

    def test_label_bad(self):
        with self.assertRaises(ValueError):
            Author.objects.label("badlabel*/")

    def test_label_and_straight_join(self):
        with CaptureLastQuery() as cap:
            list(
                Author.objects.label("QueryHintTests.test_label_and")
                .straight_join()
                .all()
            )
        assert cap.query.startswith(
            "SELECT /*QueryHintTests.test_label_and*/ STRAIGHT_JOIN "
        )

    def test_straight_join(self):
        with CaptureLastQuery() as cap:
            list(Author.objects.filter(books__title__startswith="A").straight_join())

        assert cap.query.startswith("SELECT STRAIGHT_JOIN ")

    def test_straight_join_with_distinct(self):
        with CaptureLastQuery() as cap:
            list(
                Author.objects.filter(tutor=None)
                .distinct()
                .values("books__title")
                .straight_join()
            )

        assert cap.query.startswith("SELECT DISTINCT STRAIGHT_JOIN ")

    @override_settings(DJANGO_MYSQL_REWRITE_QUERIES=False)
    def test_disabled_setting_errors_on_usage(self):
        with pytest.raises(RuntimeError) as excinfo:
            Author.objects.all().straight_join()

        assert "DJANGO_MYSQL_REWRITE_QUERIES" in str(excinfo.value)

    @skip_if_mysql_8_plus()
    def test_sql_cache(self):
        with CaptureLastQuery() as cap:
            list(Author.objects.sql_cache().all())
        assert cap.query.startswith("SELECT SQL_CACHE ")

    @skip_if_mysql_8_plus()
    def test_sql_no_cache(self):
        with CaptureLastQuery() as cap:
            list(Author.objects.sql_no_cache().all())
        assert cap.query.startswith("SELECT SQL_NO_CACHE ")

    def test_sql_small_result(self):
        with CaptureLastQuery() as cap:
            list(Author.objects.sql_small_result().all())
        assert cap.query.startswith("SELECT SQL_SMALL_RESULT ")

    def test_sql_big_result(self):
        with CaptureLastQuery() as cap:
            list(Author.objects.sql_big_result().all())
        assert cap.query.startswith("SELECT SQL_BIG_RESULT ")

    def test_sql_buffer_result(self):
        with CaptureLastQuery() as cap:
            list(Author.objects.sql_buffer_result().all())
        assert cap.query.startswith("SELECT SQL_BUFFER_RESULT ")

    def test_adding_many(self):
        with CaptureLastQuery() as cap:
            list(Author.objects.straight_join().sql_big_result().sql_buffer_result())
        assert cap.query.startswith(
            "SELECT STRAIGHT_JOIN SQL_BIG_RESULT SQL_BUFFER_RESULT "
        )

    def test_complex_query_1(self):
        with CaptureLastQuery() as cap:
            list(
                Author.objects.distinct()
                .straight_join()
                .filter(books__title__startswith="A")
                .exclude(books__id__lte=1)
                .prefetch_related("tutees")
                .filter(bio__gt="")
                .exclude(bio__startswith="Once upon")
            )
        assert cap.query.startswith("SELECT DISTINCT STRAIGHT_JOIN ")

    def test_complex_query_2(self):
        subq = Book.objects.straight_join().filter(title__startswith="A")
        with CaptureLastQuery() as cap:
            list(Author.objects.straight_join().filter(books__in=subq))
        assert cap.query.startswith("SELECT STRAIGHT_JOIN ")

    def test_use_index(self):
        name_idx = index_name(Author, "name")
        with CaptureLastQuery() as cap:
            list(Author.objects.filter(name__gt="").use_index(name_idx))
        assert ("USE INDEX (`" + name_idx + "`)") in cap.query
        used = used_indexes(cap.query)
        assert len(used) == 0 or name_idx in used

    def test_use_index_primary(self):
        with CaptureLastQuery() as cap:
            list(Author.objects.use_index("PRIMARY"))
        assert ("USE INDEX (`PRIMARY`)") in cap.query
        used = used_indexes(cap.query)
        assert len(used) == 0 or "PRIMARY" in used

    def test_force_index(self):
        name_idx = index_name(Author, "name")
        with CaptureLastQuery() as cap:
            list(Author.objects.filter(name__gt="").force_index(name_idx))
        assert ("FORCE INDEX (`" + name_idx + "`)") in cap.query
        assert name_idx in used_indexes(cap.query)

    def test_force_index_primary(self):
        with CaptureLastQuery() as cap:
            list(Author.objects.force_index("PRIMARY"))
        assert ("FORCE INDEX (`PRIMARY`)") in cap.query
        used = used_indexes(cap.query)
        assert len(used) == 0 or "PRIMARY" in used

    def test_ignore_index(self):
        name_idx = index_name(Author, "name")
        with CaptureLastQuery() as cap:
            list(Author.objects.filter(name__gt="").ignore_index(name_idx))
        assert ("IGNORE INDEX (`" + name_idx + "`)") in cap.query
        assert name_idx not in used_indexes(cap.query)

    def test_ignore_index_multiple(self):
        name_idx = index_name(AuthorMultiIndex, "name")
        name_country_idx = index_name(AuthorMultiIndex, "name", "country")
        with CaptureLastQuery() as cap:
            list(
                AuthorMultiIndex.objects.filter(name__gt="").ignore_index(
                    name_idx, name_country_idx
                )
            )
        assert (
            "IGNORE INDEX (`" + name_idx + "`,`" + name_country_idx + "`)"
        ) in cap.query
        used = used_indexes(cap.query)
        assert name_idx not in used
        assert name_country_idx not in used

    def test_ignore_index_primary(self):
        with CaptureLastQuery() as cap:
            list(Author.objects.filter(name__gt="").ignore_index("PRIMARY"))
        assert "IGNORE INDEX (`PRIMARY`)" in cap.query
        assert "PRIMARY" not in used_indexes(cap.query)

    def test_force_index_at_least_one(self):
        with pytest.raises(ValueError) as excinfo:
            Author.objects.force_index()
        assert str(excinfo.value) == "force_index requires at least one index name"

    def test_force_index_invalid_for(self):
        with pytest.raises(ValueError) as excinfo:
            Author.objects.force_index("a", for_="INVALID")
        assert "for_ must be one of" in str(excinfo.value)

    def test_force_index_invalid_kwarg(self):
        with pytest.raises(ValueError) as excinfo:
            Author.objects.force_index("a", nonexistent=True)
        assert (
            "force_index accepts only 'for_' and 'table_name' as keyword arguments"
            in str(excinfo.value)
        )

    def test_index_hint_force_order_by(self):
        name_idx = index_name(Author, "name")
        with CaptureLastQuery() as cap:
            list(Author.objects.force_index(name_idx, for_="ORDER BY").order_by("name"))

        assert ("FORCE INDEX FOR ORDER BY (`" + name_idx + "`)") in cap.query
        assert name_idx in used_indexes(cap.query)

    def test_use_index_none(self):
        with CaptureLastQuery() as cap:
            list(Author.objects.values_list("name").distinct().use_index())
        assert "USE INDEX () " in cap.query
        assert used_indexes(cap.query) == set()

    def test_use_index_table_name(self):
        extra_table = "testapp_authorextra"
        with CaptureLastQuery() as cap:
            list(
                Author.objects.select_related("authorextra").use_index(
                    "PRIMARY", table_name=extra_table
                )
            )
        assert ("`" + extra_table + "` USE INDEX (`PRIMARY`) ") in cap.query

    def test_force_index_table_name_doesnt_exist_ignored(self):
        with CaptureLastQuery() as cap:
            list(
                Author.objects.select_related("authorextra").force_index(
                    "PRIMARY", table_name="nonexistent"
                )
            )
        assert " FORCE INDEX " not in cap.query


class QueryHintNewConnectionTests(TestCase):
    @classmethod
    def setUpClass(cls):
        # Force a new connection to be created, in order to check that the
        # rewrite hook is installed on it.
        del connections[DEFAULT_DB_ALIAS]
        super().setUpClass()

    def test_label_forced_new_connection(self):
        with CaptureLastQuery() as cap:
            list(Author.objects.label("QueryHintTests.test_label").all())
        assert cap.query.startswith("SELECT /*QueryHintTests.test_label*/ ")


class FoundRowsTests(TestCase):
    def setUp(self):
        super().setUp()
        Author.objects.bulk_create([Author() for i in range(10)])

    def test_found_rows_requires_sql_calc_found_rows(self):
        authors = Author.objects.all()
        with pytest.raises(ValueError) as excinfo:
            authors.found_rows
        assert "can only be used if" in str(excinfo.value)

    def test_found_rows_requires_iteration(self):
        authors = Author.objects.sql_calc_found_rows()[:5]
        with self.assertRaises(RuntimeError):
            authors.found_rows

    def test_it_doesnt_work_with_iterator(self):
        authors = Author.objects.sql_calc_found_rows()[:5]
        match_re = r"doesn't work with iterator\(\)"
        with pytest.raises(ValueError, match=match_re):
            authors.iterator()

    def test_iterator_without_it_works(self):
        authors = Author.objects.all()[:5]
        authors.iterator()

    def test_it_working(self):
        with self.assertNumQueries(2):
            authors = Author.objects.sql_calc_found_rows()[:5]
            list(authors)
            assert authors.found_rows == 10

    def test_no_repeats(self):
        with self.assertNumQueries(2):
            authors = Author.objects.sql_calc_found_rows().sql_calc_found_rows()[:5]
            list(authors)
            assert authors.found_rows == 10

    def test_it_working_prefetching(self):
        with self.assertNumQueries(3):
            authors = Author.objects.sql_calc_found_rows().prefetch_related("tutor")[:5]
            list(authors)
            assert authors.found_rows == 10

    def test_pickleability(self):
        authors = Author.objects.sql_calc_found_rows()
        pickle.dumps(authors)

    def test_cloning_doesnt_copy_found_rows_number(self):
        authors = Author.objects.sql_calc_found_rows()
        list(authors)
        assert authors.found_rows == 10

        authors2 = authors.filter(id__gte=1)
        with pytest.raises(RuntimeError):
            authors2.found_rows

        with self.assertNumQueries(2):
            list(authors2)
            assert authors2.found_rows == 10


class SmartIteratorTests(TestCase):
    def setUp(self):
        super().setUp()
        Author.objects.bulk_create([Author(id=i + 1) for i in range(10)])

    def test_bad_querysets(self):
        with pytest.raises(ValueError) as excinfo:
            Author.objects.all().order_by("name").iter_smart_chunks()
        assert "ordering" in str(excinfo.value)

        with pytest.raises(ValueError) as excinfo:
            Author.objects.all()[:5].iter_smart_chunks()
        assert "sliced QuerySet" in str(excinfo.value)

        with pytest.raises(ValueError) as excinfo:
            NameAuthor.objects.all().iter_smart_chunks()
        assert "non-integer primary key" in str(excinfo.value)

    def test_chunks(self):
        seen = []
        for authors in Author.objects.iter_smart_chunks():
            seen.extend(author.id for author in authors)

        all_ids = list(Author.objects.order_by("id").values_list("id", flat=True))
        assert seen == all_ids

    def test_objects(self):
        seen = [author.id for author in Author.objects.iter_smart()]
        all_ids = list(Author.objects.order_by("id").values_list("id", flat=True))
        assert seen == all_ids

    def test_objects_non_atomic(self):
        seen = [a.id for a in Author.objects.iter_smart(atomically=False)]
        all_ids = list(Author.objects.order_by("id").values_list("id", flat=True))
        assert seen == all_ids

    def test_objects_reverse(self):
        seen = [a.id for a in Author.objects.reverse().iter_smart()]
        all_ids = list(Author.objects.order_by("-id").values_list("id", flat=True))
        assert seen == all_ids

    def test_objects_pk_range_all(self):
        seen = [a.id for a in Author.objects.iter_smart(pk_range="all")]
        all_ids = list(Author.objects.order_by("id").values_list("id", flat=True))
        assert seen == all_ids

    def test_objects_pk_range_tuple(self):
        min_id = Author.objects.earliest("id").id
        max_id = Author.objects.order_by("id")[5].id

        seen = [a.id for a in Author.objects.iter_smart(pk_range=(min_id, max_id))]
        cut_ids = list(
            Author.objects.order_by("id")
            .filter(id__gte=min_id, id__lte=max_id)
            .values_list("id", flat=True)
        )
        assert seen == cut_ids

    def test_objects_pk_range_tuple_0_0(self):
        seen = [a.id for a in Author.objects.iter_smart(pk_range=(0, 0))]
        assert seen == []

    def test_objects_pk_range_reversed(self):
        min_id = Author.objects.earliest("id").id
        max_id = Author.objects.latest("id").id

        seen = [
            author.id for author in Author.objects.iter_smart(pk_range=(max_id, min_id))
        ]
        all_ids = list(Author.objects.order_by("-id").values_list("id", flat=True))
        assert seen == all_ids

    def test_objects_pk_range_bad(self):
        with pytest.raises(ValueError) as excinfo:
            list(Author.objects.iter_smart(pk_range="My Bad Value"))
        assert "Unrecognized value for pk_range" in str(excinfo.value)

    def test_pk_range_race_condition(self):
        getitem = QuerySet.__getitem__

        def fail_second_slice(*args, **kwargs):
            # Simulate race condition by deleting all objects between first
            # call (min_qs[0]) and second call (max_qs[0]) to
            # QuerySet.__getitem__
            fail_second_slice.calls += 1
            if fail_second_slice.calls == 2:
                Author.objects.all().delete()
            return getitem(*args, **kwargs)

        fail_second_slice.calls = 0

        path = "django.db.models.query.QuerySet.__getitem__"

        with mock.patch(path, fail_second_slice):
            seen = [author.id for author in Author.objects.iter_smart()]
        assert seen == []

    def test_objects_chunk_size(self):
        smart = iter(Author.objects.iter_smart_chunks(chunk_size=3))
        chunk = next(smart)
        assert len(list(chunk)) == 3

    def test_objects_chunk_size_1(self):
        smart = iter(Author.objects.iter_smart_chunks(chunk_size=1))
        chunk = next(smart)
        assert len(list(chunk)) == 1

    def test_objects_max_size(self):
        seen = []
        for chunk in Author.objects.iter_smart_chunks(chunk_max=3):
            ids = [author.id for author in chunk]
            assert len(ids) <= 3
            seen.extend(ids)
        all_ids = list(Author.objects.order_by("id").values_list("id", flat=True))
        assert seen == all_ids

    def test_objects_max_size_1(self):
        seen = []
        for chunk in Author.objects.iter_smart_chunks(chunk_max=1):
            ids = [author.id for author in chunk]
            assert len(ids) == 1
            seen.extend(ids)
        all_ids = list(Author.objects.order_by("id").values_list("id", flat=True))
        assert seen == all_ids

    def test_objects_max_size_bounds_chunk_size(self):
        smart = iter(Author.objects.iter_smart_chunks(chunk_max=5, chunk_size=1000))

        seen = []
        for chunk in smart:
            ids = [author.id for author in chunk]
            assert len(ids) <= 5
            seen.extend(ids)
        all_ids = list(Author.objects.order_by("id").values_list("id", flat=True))
        assert seen == all_ids

    def test_objects_min_size_bounds_chunk_size(self):
        smart = iter(Author.objects.iter_smart_chunks(chunk_min=5, chunk_size=1))
        seen = []
        for chunk in smart:
            ids = [author.id for author in chunk]
            assert len(ids) >= 5
            seen.extend(ids)
        all_ids = list(Author.objects.order_by("id").values_list("id", flat=True))
        assert seen == all_ids

    def test_min_size_greater_than_max(self):
        with pytest.raises(AssertionError):
            Author.objects.iter_smart_chunks(chunk_min=2, chunk_max=1)

    def test_no_matching_objects(self):
        seen = [author.id for author in Author.objects.filter(name="Waaa").iter_smart()]
        assert seen == []

    def test_no_objects(self):
        Author.objects.all().delete()
        seen = [author.id for author in Author.objects.iter_smart()]
        assert seen == []

    def test_pk_hole(self):
        first = Author.objects.earliest("id")
        last = Author.objects.latest("id")
        Author.objects.filter(id__gt=first.id, id__lt=last.id).delete()
        seen = [author.id for author in Author.objects.iter_smart()]
        assert seen == [first.id, last.id]

    def test_iter_smart_pk_range(self):
        seen = []
        for start_pk, end_pk in Author.objects.iter_smart_pk_ranges():
            seen.extend(
                Author.objects.filter(id__gte=start_pk, id__lt=end_pk).values_list(
                    "id", flat=True
                )
            )
        all_ids = list(Author.objects.order_by("id").values_list("id", flat=True))
        assert seen == all_ids

    def test_iter_smart_pk_range_with_raw(self):
        seen = []
        for start_pk, end_pk in Author.objects.iter_smart_pk_ranges():
            authors = Author.objects.raw(
                """
                SELECT id FROM {}
                WHERE id >= %s AND id < %s
            """.format(
                    Author._meta.db_table
                ),
                (start_pk, end_pk),
            )
            seen.extend(author.id for author in authors)

        all_ids = list(Author.objects.order_by("id").values_list("id", flat=True))
        assert seen == all_ids

    def test_iter_smart_fk_primary_key(self):
        author, author2 = Author.objects.all()[:2]
        AuthorExtra.objects.create(author=author, legs=2)
        AuthorExtra.objects.create(author=author2, legs=1)

        seen_author_ids = []
        for extra in AuthorExtra.objects.iter_smart():
            seen_author_ids.append(extra.author_id)
        assert seen_author_ids == [author.id, author2.id]

    def test_iter_smart_fk_string_primary_key_fails(self):
        with pytest.raises(ValueError) as excinfo:
            NameAuthorExtra.objects.iter_smart()
        assert "non-integer primary key" in str(excinfo.value)

    def test_reporting(self):
        with captured_stdout() as output:
            qs = Author.objects.all()
            for authors in qs.iter_smart_chunks(report_progress=True):
                list(authors)  # fetch them

        lines = output.getvalue().split("\n")

        reports = lines[0].split("\r")
        for report in reports:
            assert re.match(
                r"^Author SmartChunkedIterator processed \d+/10 objects "
                r"\(\d+\.\d+%\) in \d+ chunks"
                r"(; highest pk so far \d+(, [\dhms]+ remaining)?)?$",
                report,
            )

        assert re.match(r"Finished! Iterated over \d+ objects? in [\dhms]+.", lines[1])

    def test_reporting_reverse(self):
        Author.objects.create(id=10000)

        with captured_stdout() as output:
            qs = Author.objects.reverse()
            for authors in qs.iter_smart_chunks(report_progress=True, chunk_min=100):
                list(authors)  # fetch them

        lines = output.getvalue().split("\n")

        reports = lines[0].split("\r")
        assert len(reports) > 0
        for report in reports:
            assert re.match(
                r"^Author SmartChunkedIterator processed \d+/11 objects "
                r"\(\d+\.\d+%\) in \d+ chunks"
                r"(; lowest pk so far \d+(, [\dhms]+ remaining)?)?( )*$",
                report,
            )

        assert re.match(r"Finished! Iterated over \d+ objects? in [\dhms]+.", lines[1])

    def test_reporting_with_total(self):
        with captured_stdout() as output:
            qs = Author.objects.all()
            for authors in qs.iter_smart_chunks(report_progress=True, total=4):
                list(authors)  # fetch them

        lines = output.getvalue().split("\n")

        reports = lines[0].split("\r")
        for report in reports:
            assert re.match(
                r"^Author SmartChunkedIterator processed \d+/4 objects "
                r"\(\d+\.\d+%\) in \d+ chunks"
                r"(; highest pk so far \d+(, [\dhms]+ remaining)?)?$",
                report,
            )

        assert re.match(r"Finished! Iterated over \d+ objects? in [\dhms]+.", lines[1])

    def test_reporting_on_uncounted_qs(self):
        Author.objects.create(name="pants")

        with captured_stdout() as output:
            qs = Author.objects.filter(name="pants")
            for authors in qs.iter_smart_chunks(report_progress=True):
                authors.delete()

        lines = output.getvalue().split("\n")

        reports = lines[0].split("\r")
        for report in reports:
            assert re.match(
                # We should have ??? since the deletion means the objects
                # aren't fetched into python
                r"Author SmartChunkedIterator processed (0|\?\?\?)/1 objects "
                r"\(\d+\.\d+%\) in \d+ chunks(; highest pk so far \d+)?",
                report,
            )

        assert re.match(
            r"Finished! Iterated over \?\?\? objects? in [\dhms]+.", lines[1]
        )

    def test_filter_and_delete(self):
        VanillaAuthor.objects.create(name="Alpha")
        VanillaAuthor.objects.create(name="pants")
        VanillaAuthor.objects.create(name="Beta")
        VanillaAuthor.objects.create(name="pants")

        bad_authors = VanillaAuthor.objects.filter(name="pants")

        assert bad_authors.count() == 2

        with captured_stdout():
            for author in SmartIterator(bad_authors, report_progress=True):
                author.delete()

        assert bad_authors.count() == 0


@skipUnless(have_program("pt-visual-explain"), "pt-visual-explain must be installed")
class VisualExplainTests(TestCase):
    def test_basic(self):
        with captured_stdout() as capture:
            Author.objects.all().pt_visual_explain()
        output = capture.getvalue()
        # Can't be too strict about the output since different database and pt-
        # visual-explain versions give different output
        assert "testapp_author" in output
        assert "rows" in output
        assert "Table" in output

    def test_basic_no_display(self):
        output = Author.objects.all().pt_visual_explain(display=False)
        assert "testapp_author" in output
        assert "rows" in output
        assert "Table" in output

    def test_subquery(self):
        subq = Author.objects.all().values_list("id", flat=True)
        output = Author.objects.filter(id__in=subq).pt_visual_explain(display=False)
        assert "possible_keys" in output
        assert "testapp_author" in output
        assert "rows" in output
        assert "Table" in output
