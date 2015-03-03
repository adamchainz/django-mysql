# -*- coding:utf-8 -*-
from textwrap import dedent

from django.template import Context, Template
from django.test import TransactionTestCase

from django_mysql.models import SmartIterator

from django_mysql_tests.models import Author, NameAuthor, VanillaAuthor

from .utils import captured_stdout


class ApproximateCountTests(TransactionTestCase):

    def setUp(self):
        super(ApproximateCountTests, self).setUp()
        Author.objects.bulk_create([Author() for i in range(10)])

    def test_approx_count(self):
        # Theoretically this varies 30-50% of the table size
        # For a fresh table with 10 items we seem to always get back the actual
        # count, but to be sure we'll just assert it's within 55%
        approx_count = Author.objects.approx_count(min_size=1)
        self.assertGreaterEqual(approx_count, 4)
        self.assertLessEqual(approx_count, 16)

    def test_activation_deactivation(self):
        qs = Author.objects.all()
        self.assertFalse(qs._count_tries_approx)

        qs2 = qs.count_tries_approx(min_size=2)
        self.assertNotEqual(qs, qs2)
        self.assertTrue(qs2._count_tries_approx)

        qs3 = qs2.count_tries_approx(False)
        self.assertNotEqual(qs2, qs3)
        self.assertFalse(qs3._count_tries_approx)

    def test_output_in_templates(self):
        approx_count = Author.objects.approx_count(min_size=1)
        text = Template('{{ var }}').render(Context({'var': approx_count}))
        self.assertTrue(text.startswith('Approximately '))

        approx_count2 = Author.objects.approx_count(
            min_size=1,
            return_approx_int=False
        )
        text = Template('{{ var }}').render(Context({'var': approx_count2}))
        self.assertFalse(text.startswith('Approximately '))

    def test_fallback_with_filters(self):
        filtered = Author.objects.filter(name='')
        self.assertEqual(filtered.approx_count(fall_back=True), 10)
        with self.assertRaises(ValueError):
            filtered.approx_count(fall_back=False)

    def test_fallback_with_slice(self):
        self.assertEqual(Author.objects.all()[:100].approx_count(), 10)
        with self.assertRaises(ValueError):
            Author.objects.all()[:100].approx_count(fall_back=False)

    def test_fallback_with_distinct(self):
        self.assertEqual(Author.objects.distinct().approx_count(), 10)
        with self.assertRaises(ValueError):
            Author.objects.distinct().approx_count(fall_back=False)


class SmartIteratorTests(TransactionTestCase):

    def setUp(self):
        super(SmartIteratorTests, self).setUp()
        Author.objects.bulk_create([Author() for i in range(10)])

    def test_bad_querysets(self):
        with self.assertRaises(ValueError) as cm:
            Author.objects.all().order_by('name').iter_smart_chunks()
        self.assertIn("ordering", str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            Author.objects.all()[:5].iter_smart_chunks()
        self.assertIn("sliced QuerySet", str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            NameAuthor.objects.all().iter_smart_chunks()
        self.assertIn("non-integer primary key", str(cm.exception))

    def test_chunks(self):
        seen = []
        for authors in Author.objects.iter_smart_chunks():
            seen.extend(author.id for author in authors)

        all_ids = list(Author.objects.order_by('id')
                                     .values_list('id', flat=True))
        self.assertEqual(seen, all_ids)

    def test_objects(self):
        seen = [author.id for author in Author.objects.iter_smart()]
        all_ids = list(Author.objects.order_by('id')
                                     .values_list('id', flat=True))
        self.assertEqual(seen, all_ids)

    def test_no_matching_objects(self):
        seen = [author.id for author in
                Author.objects.filter(name="Waaa").iter_smart()]
        self.assertEqual(seen, [])

    def test_no_objects(self):
        Author.objects.all().delete()
        seen = [author.id for author in Author.objects.iter_smart()]
        self.assertEqual(seen, [])

    def test_reporting(self):
        with captured_stdout() as output:
            qs = Author.objects.all()
            for authors in qs.iter_smart_chunks(report_progress=True):
                list(authors)  # fetch them

        lines = output.getvalue().split('\n')

        reports = lines[0].split('\r')
        for report in reports:
            self.assertRegexpMatches(
                report,
                r"AuthorSmartChunkedIterator processed \d+/10 objects "
                r"\(\d+\.\d+%\) in \d+ chunks(; highest pk so far \d+)?"
            )

        self.assertEqual(lines[1], 'Finished!')

    def test_reporting_on_uncounted_qs(self):
        Author.objects.create(name="pants")

        with captured_stdout() as output:
            qs = Author.objects.filter(name="pants")
            for authors in qs.iter_smart_chunks(report_progress=True):
                authors.delete()

        lines = output.getvalue().split('\n')

        reports = lines[0].split('\r')
        for report in reports:
            self.assertRegexpMatches(
                report,
                # We should have ??? since the deletion means the objects
                # aren't fetched into python
                r"AuthorSmartChunkedIterator processed (0|\?\?\?)/1 objects "
                r"\(\d+\.\d+%\) in \d+ chunks(; highest pk so far \d+)?"
            )

        self.assertEqual(lines[1], 'Finished!')

    def test_running_on_non_mysql_model(self):
        VanillaAuthor.objects.create(name="Alpha")
        VanillaAuthor.objects.create(name="pants")
        VanillaAuthor.objects.create(name="Beta")
        VanillaAuthor.objects.create(name="pants")

        bad_authors = VanillaAuthor.objects.filter(name="pants")

        self.assertEqual(bad_authors.count(), 2)

        with captured_stdout():
            for author in SmartIterator(bad_authors, report_progress=True):
                author.delete()

        self.assertEqual(bad_authors.count(), 0)


class VisualExplainTests(TransactionTestCase):

    def test_basic(self):
        output = Author.objects.all().visual_explain()
        expected = dedent("""
        Table scan
        rows           1
        +- Table
           table          django_mysql_tests_author
        """).strip() + "\n"
        self.assertEqual(output, expected)

    def test_subquery(self):
        subq = Author.objects.all().values_list('id', flat=True)
        output = Author.objects.filter(id__in=subq).visual_explain()
        expected = dedent("""
        JOIN
        +- Unique index lookup
        |  key            U0->PRIMARY
        |  possible_keys  PRIMARY
        |  key_len        4
        |  ref            test_django_mysql.django_mysql_tests_author.id
        |  rows           1
        +- Table scan
           rows           1
           +- Table
              table          django_mysql_tests_author
              possible_keys  PRIMARY
        """).strip() + "\n"
        self.assertEqual(output, expected)
