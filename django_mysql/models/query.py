# -*- coding:utf-8 -*-
from __future__ import print_function, unicode_literals

import operator
import sys
import time
from copy import copy
from subprocess import PIPE, Popen

from django.db import connections, models
from django.db.models.sql.where import ExtraWhere
from django.db.transaction import atomic
from django.test.utils import CaptureQueriesContext
from django.utils import six
from django.utils.functional import cached_property
from django.utils.translation import ugettext as _

from django_mysql.models.handler import Handler
from django_mysql.rewrite_query import REWRITE_MARKER
from django_mysql.status import GlobalStatus
from django_mysql.utils import (
    StopWatch, WeightedAverageRate, format_duration, have_program,
    noop_context, settings_to_cmd_args
)


class QuerySetMixin(object):

    def __init__(self, *args, **kwargs):
        super(QuerySetMixin, self).__init__(*args, **kwargs)
        self._count_tries_approx = False

    def _clone(self, *args, **kwargs):
        clone = super(QuerySetMixin, self)._clone(*args, **kwargs)

        clone._count_tries_approx = copy(
            getattr(self, '_count_tries_approx', False)
        )

        if hasattr(self, '_found_rows'):
            # If it's a number, don't copy it - the clone has a fresh result
            # cache
            clone._found_rows = None
        return clone

    # approx_count features

    def count(self):
        if self._count_tries_approx:
            return self.approx_count(**self._count_tries_approx)
        return super(QuerySetMixin, self).count()

    def count_tries_approx(self, activate=True, fall_back=True,
                           return_approx_int=True, min_size=1000):
        clone = self._clone()

        if activate:
            clone._count_tries_approx = {
                'fall_back': fall_back,
                'return_approx_int': return_approx_int,
                'min_size': min_size,
            }
        else:
            clone._count_tries_approx = False

        return clone

    def approx_count(self, fall_back=True, return_approx_int=True,
                     min_size=1000):
        try:
            num = approx_count(self)
        except ValueError:  # Cannot be approx-counted
            if not fall_back:
                raise ValueError("Cannot use approx_count on this queryset.")
            # Always fall through to super class
            return super(QuerySetMixin, self).count()

        if min_size and num < min_size:
            # Always fall through to super class
            return super(QuerySetMixin, self).count()

        if return_approx_int:
            return ApproximateInt(num)
        else:
            return num

    # Query rewrite/hint API
    # These specially constructed comments will be rewritten by rewrite_query
    # into actual hints

    def label(self, string):
        """
        Adds an arbitrary user-defined comment that will appear after
        SELECT/UPDATE/DELETE which can be used to identify where the query was
        generated, etc.
        """
        if '*/' in string:
            raise ValueError("Bad label - cannot be embedded in SQL comment")
        return self.extra(where=["/*QueryRewrite':label={}*/1".format(string)])

    def straight_join(self):
        return self.extra(where=["/*QueryRewrite':STRAIGHT_JOIN*/1"])

    def sql_small_result(self):
        return self.extra(where=["/*QueryRewrite':SQL_SMALL_RESULT*/1"])

    def sql_big_result(self):
        return self.extra(where=["/*QueryRewrite':SQL_BIG_RESULT*/1"])

    def sql_buffer_result(self):
        return self.extra(where=["/*QueryRewrite':SQL_BUFFER_RESULT*/1"])

    def sql_cache(self):
        return self.extra(where=["/*QueryRewrite':SQL_CACHE*/1"])

    def sql_no_cache(self):
        return self.extra(where=["/*QueryRewrite':SQL_NO_CACHE*/1"])

    def sql_calc_found_rows(self):
        qs = self.extra(where=["/*QueryRewrite':SQL_CALC_FOUND_ROWS*/1"])
        qs._found_rows = None
        return qs

    @property
    def found_rows(self):
        if not hasattr(self, '_found_rows'):
            raise ValueError(
                "found_rows can only be used if you call sql_calc_found_rows()"
            )
        if self._found_rows is None:
            raise RuntimeError(
                "A QuerySet with sql_calc_found_rows must be iterated before "
                "found_rows can be accessed"
            )
        return self._found_rows

    def iterator(self):
        for row in super(QuerySetMixin, self).iterator():
            yield row
        if getattr(self, '_found_rows', 0) is None:
            with connections[self.db].cursor() as cursor:
                cursor.execute("SELECT FOUND_ROWS()")
                self._found_rows = cursor.fetchone()[0]

    def use_index(self, *index_names, **kwargs):
        kwargs['hint'] = 'USE'
        return self._index_hint(*index_names, **kwargs)

    def force_index(self, *index_names, **kwargs):
        kwargs['hint'] = 'FORCE'
        return self._index_hint(*index_names, **kwargs)

    def ignore_index(self, *index_names, **kwargs):
        kwargs['hint'] = 'IGNORE'
        return self._index_hint(*index_names, **kwargs)

    def _index_hint(self, *index_names, **kwargs):
        hint = kwargs.pop('hint')
        table_name = kwargs.pop('table_name', None)
        for_ = kwargs.pop('for_', None)
        if kwargs:
            raise ValueError(
                "{}_index accepts only 'for_' and 'table_name' as keyword "
                "arguments"
                .format(hint.lower())
            )

        if hint != 'USE' and not len(index_names):
            raise ValueError(
                "{}_index requires at least one index name"
                .format(hint.lower())
            )

        if table_name is None:
            table_name = self.model._meta.db_table

        if for_ in ('JOIN', 'ORDER BY', 'GROUP BY'):
            for_bit = 'FOR {} '.format(for_)
        elif for_ is None:
            for_bit = ''
        else:
            raise ValueError("for_ must be one of: None, 'JOIN', 'ORDER BY', "
                             "'GROUP BY'")

        if len(index_names) == 0:
            indexes = "NONE"
        else:
            indexes = "`" + "`,`".join(index_names) + "`"

        hint = (
            "/*QueryRewrite':index=`{table_name}` {hint} {for_bit}{indexes}*/1"
            .format(table_name=table_name, hint=hint, for_bit=for_bit,
                    indexes=indexes)
        )
        return self.extra(where=[hint])

    # Features handled by extra classes/functions

    def iter_smart(self, **kwargs):
        assert 'queryset' not in kwargs, \
            "You can't pass another queryset in through iter_smart!"
        return SmartIterator(queryset=self, **kwargs)

    def iter_smart_chunks(self, **kwargs):
        assert 'queryset' not in kwargs, \
            "You can't pass another queryset in through iter_smart_chunks!"
        return SmartChunkedIterator(queryset=self, **kwargs)

    def iter_smart_pk_ranges(self, **kwargs):
        assert 'queryset' not in kwargs, \
            "You can't pass another queryset in through iter_smart_pk_ranges!"
        return SmartPKRangeIterator(queryset=self, **kwargs)

    def pt_visual_explain(self, display=True):
        return pt_visual_explain(self, display)

    def handler(self):
        return Handler(self)


class QuerySet(QuerySetMixin, models.QuerySet):
    pass


def add_QuerySetMixin(queryset):
    queryset2 = queryset._clone()
    queryset2.__class__ = _make_mixin_class(queryset.__class__)
    return queryset2


_mixin_classes = {}


def _make_mixin_class(klass):
    global _mixin_classes

    if klass not in _mixin_classes:
        class MixedInQuerySet(QuerySetMixin, klass):
            pass

        if six.PY2:
            MixedInQuerySet.__name__ = b'MySQL' + klass.__name__
        else:
            MixedInQuerySet.__name__ = 'MySQL' + klass.__name__
        _mixin_classes[klass] = MixedInQuerySet
    return _mixin_classes[klass]


@six.python_2_unicode_compatible
class ApproximateInt(int):
    """
    An int subclass purely for displaying the fact that this represents an
    approximate value, for in e.g. the admin
    """
    def __str__(self):
        return _("Approximately %(number)s") % {
            'number': super(ApproximateInt, self).__str__()
        }


class SmartChunkedIterator(object):
    def __init__(self, queryset, atomically=True, status_thresholds=None,
                 pk_range=None, chunk_time=0.5, chunk_size=2, chunk_min=1,
                 chunk_max=10000, report_progress=False, total=None):
        self.queryset = self.sanitize_queryset(queryset)

        if atomically:
            self.maybe_atomic = atomic
        else:
            # Work around for `with` statement not supporting variable number
            # of contexts
            self.maybe_atomic = noop_context

        self.status_thresholds = status_thresholds
        self.pk_range = pk_range

        self.rate = WeightedAverageRate(chunk_time)
        assert 0 < chunk_min <= chunk_max, \
            "Minimum chunk size should not be greater than maximum chunk size."
        self.chunk_min = chunk_min
        self.chunk_max = chunk_max
        self.chunk_size = self.constrain_size(chunk_size)

        self.report_progress = report_progress
        self.total = total

    def __iter__(self):
        first_pk, last_pk = self.get_first_and_last()
        if first_pk <= last_pk:
            comp = operator.le  # <=
            direction = 1
        else:
            comp = operator.ge  # >=
            direction = -1
        current_pk = first_pk
        db_alias = self.queryset.db
        status = GlobalStatus(db_alias)

        self.init_progress(direction)

        while comp(current_pk, last_pk):
            status.wait_until_load_low(self.status_thresholds)

            start_pk = current_pk
            current_pk = current_pk + self.chunk_size * direction
            # Don't process rows that didn't exist at start of iteration
            if direction == 1:
                end_pk = min(current_pk, last_pk + 1)
            else:
                end_pk = max(current_pk, last_pk - 1)

            with StopWatch() as timer, self.maybe_atomic(using=db_alias):
                if direction == 1:
                    chunk = self.queryset.filter(pk__gte=start_pk,
                                                 pk__lt=end_pk)
                else:
                    chunk = self.queryset.filter(pk__lte=start_pk,
                                                 pk__gt=end_pk)
                # Attach the start_pk, end_pk onto the chunk queryset so they
                # can be read by SmartRangeIterator or other client code
                chunk._smart_iterator_pks = (start_pk, end_pk)
                yield chunk
                self.update_progress(direction, chunk, end_pk)

            self.adjust_chunk_size(chunk, timer.total_time)

        self.end_progress()

    def sanitize_queryset(self, queryset):
        if queryset.ordered:
            raise ValueError(
                "You can't use %s on a QuerySet with an ordering." %
                self.__class__.__name__
            )

        if queryset.query.low_mark or queryset.query.high_mark:
            raise ValueError(
                "You can't use %s on a sliced QuerySet." %
                self.__class__.__name__
            )

        pk = queryset.model._meta.pk
        if not isinstance(pk, self.ALLOWED_PK_FIELD_CLASSES):
            # If your custom field class should be allowed, just add it to
            # ALLOWED_PK_FIELD_CLASSES
            raise ValueError(
                "You can't use %s on a model with a non-integer primary key." %
                self.__class__.__name__
            )

        return queryset.order_by('pk')

    ALLOWED_PK_FIELD_CLASSES = (
        models.IntegerField,  # Also covers e.g. PositiveIntegerField
        models.AutoField,  # Is an integer field but doesn't subclass it :(
        models.ForeignKey  # Should always point to an integer
    )

    def get_first_and_last(self):
        if isinstance(self.pk_range, tuple) and len(self.pk_range) == 2:
            should_be_reversed = (
                self.pk_range[1] < self.pk_range[0] and
                self.queryset.query.standard_ordering
            )
            if should_be_reversed:
                self.queryset = self.queryset.reverse()
            return self.pk_range
        elif self.pk_range == 'all':
            base_qs = self.queryset.model.objects.using(self.queryset.db).all()
        elif self.pk_range is None:
            base_qs = self.queryset
        else:
            raise ValueError("Unrecognized value for pk_range: {}"
                             .format(self.pk_range))

        if not base_qs.query.standard_ordering:  # It's reverse()d
            base_qs = base_qs.reverse()

        min_qs = base_qs.order_by('pk').values_list('pk', flat=True)
        max_qs = base_qs.order_by('-pk').values_list('pk', flat=True)
        try:
            min_pk = min_qs[0]
        except IndexError:
            # We're working on an empty QuerySet, yield no chunks
            max_pk = min_pk = 0
        else:
            try:
                max_pk = max_qs[0]
            except IndexError:
                # Fix possible race condition - max_qs could find nothing if
                # all rows (including that with id min_pk) were processed
                # between finding min_pk and the above [0]
                max_pk = min_pk

        if self.queryset.query.standard_ordering:
            return (min_pk, max_pk)
        else:
            return (max_pk, min_pk)

    def constrain_size(self, chunk_size):
        return max(min(chunk_size, self.chunk_max), self.chunk_min)

    def adjust_chunk_size(self, chunk, chunk_time):
        # If the queryset is not being fetched as-is, e.g. its .delete() is
        # called, we can't know how many objects were affected, so we just
        # assume they all exist/existed
        if chunk._result_cache is None:
            num_processed = self.chunk_size
        else:
            num_processed = len(chunk)

        if num_processed > 0:
            new_chunk_size = self.rate.update(num_processed, chunk_time)
        else:
            new_chunk_size = self.chunk_size

        if new_chunk_size < 1:  # pragma: no cover
            new_chunk_size = 1

        self.chunk_size = self.constrain_size(new_chunk_size)

    def init_progress(self, direction):
        if not self.report_progress:
            return

        self.start_time = time.time()
        self.old_report = ""
        self.objects_done = 0
        self.chunks_done = 0
        if self.total is None:  # User didn't pass in a total
            try:
                self.total = approx_count(self.queryset)
                if self.total < 1000:
                    self.total = self.queryset.count()
            except ValueError:  # Cannot be approximately counted
                self.total = self.queryset.count()  # Fallback - will be slow

        self.update_progress(direction)

    def update_progress(self, direction, chunk=None, end_pk=None):
        if not self.report_progress:
            return

        if chunk is not None:
            self.chunks_done += 1
            if self.objects_done != "???":
                # If the queryset is not being fetched as-is, e.g. its
                # .delete() is called, we can't know how many objects were
                # affected, so we just bum out and write "???".
                if chunk._result_cache is None:
                    self.objects_done = "???"
                else:
                    self.objects_done += len(chunk)

        try:
            percent_complete = 100 * (float(self.objects_done) / self.total)
        except (ZeroDivisionError, ValueError):
            percent_complete = 0.0

        report = "{} {} processed {}/{} objects ({:.2f}%) in {} chunks".format(
            self.model_name,
            self.__class__.__name__,
            self.objects_done,
            self.total,
            percent_complete,
            self.chunks_done,
        )

        if end_pk is not None:
            report += "; {dir} pk so far {end_pk}".format(
                dir="highest" if direction == 1 else "lowest",
                end_pk=end_pk,
            )

            if self.objects_done != '???' and self.rate.avg_rate:
                n_remaining = self.total - self.objects_done
                s_remaining = max(0, int(n_remaining // self.rate.avg_rate))
                report += ', {} remaining'.format(
                    format_duration(s_remaining)
                )

        # Add spaces to avoid problem with reverse iteration, see #177.
        spacing = " " * max(0, len(self.old_report) - len(report))

        if self.old_report:
            # Reset line on successive outputs
            sys.stdout.write("\r")

        sys.stdout.write(report)
        sys.stdout.write(spacing)
        sys.stdout.flush()

        self.old_report = report

    def end_progress(self):
        if not self.report_progress:
            return

        total_time = time.time() - self.start_time
        sys.stdout.write(
            "\nFinished! Iterated over {n} object{s} in {duration}.\n".format(
                n=self.objects_done,
                s='s' if self.objects_done != 1 else '',
                duration=format_duration(total_time)
            )
        )

    @cached_property
    def model_name(self):
        return self.queryset.model.__name__


class SmartIterator(SmartChunkedIterator):
    """
    Subclass of SmartChunkedIterator that unpacks the chunks
    """
    def __iter__(self):
        for chunk in super(SmartIterator, self).__iter__():
            for obj in chunk:
                yield obj


class SmartPKRangeIterator(SmartChunkedIterator):
    def __iter__(self):
        for chunk in super(SmartPKRangeIterator, self).__iter__():
            start_pk, end_pk = chunk._smart_iterator_pks
            yield start_pk, end_pk


def approx_count(queryset):
    # Returns the approximate count or raises a ValueError if this queryset
    # cannot be approximately counted
    if not can_approx_count(queryset):
        raise ValueError("This QuerySet cannot be approximately counted")

    connection = connections[queryset.db]
    with connection.cursor() as cursor:
        table_name = queryset.model._meta.db_table
        sql = "EXPLAIN SELECT COUNT(*) FROM `{0}`".format(table_name)
        cursor.execute(sql)
        approx_count = cursor.fetchone()[8]  # 'rows' is the 9th column
        return approx_count


def can_approx_count(queryset):
    query = queryset.query

    if query.select or query.group_by or query.distinct:
        return False
    elif query.high_mark is not None or query.low_mark != 0:
        return False

    # Visit parts of the where clause - if any is not a query hint, fail
    for child in query.where.children:
        if not isinstance(child, ExtraWhere):
            return False
        elif not all((REWRITE_MARKER in sql) for sql in child.sqls):
            return False

    if hasattr(query, 'having') and query.having:  # Django < 1.9
        return False  # pragma: no cover

    return True


def pt_visual_explain(queryset, display=True):
    if not have_program('pt-visual-explain'):  # pragma: no cover
        raise OSError("pt-visual-explain doesn't appear to be installed")

    connection = connections[queryset.db]
    capturer = CaptureQueriesContext(connection)
    with capturer, connection.cursor() as cursor:
        sql, params = queryset.query.sql_with_params()
        cursor.execute('EXPLAIN ' + sql, params)

    queries = [q['sql'] for q in capturer.captured_queries]
    # Take the last - django may have just opened up a connection in which
    # case it would have run initialization command[s]
    explain_query = queries[-1]

    # Now do the explain and pass through pt-visual-explain
    mysql_command = (
        settings_to_cmd_args(connection.settings_dict) +
        ['-e', explain_query]
    )
    mysql = Popen(mysql_command, stdout=PIPE)
    visual_explain = Popen(
        ['pt-visual-explain', '-'],
        stdin=mysql.stdout,
        stdout=PIPE
    )
    mysql.stdout.close()
    explanation = visual_explain.communicate()[0].decode(encoding="utf-8")
    if display:
        print(explanation)
    else:
        return explanation
