# -*- coding:utf-8 -*-
from __future__ import print_function, unicode_literals

import sys
from copy import copy
from subprocess import PIPE, Popen

from django.db import connections, models
from django.db.transaction import atomic
from django.test.utils import CaptureQueriesContext
from django.utils import six
from django.utils.functional import cached_property
from django.utils.translation import ugettext as _

from django_mysql.models.handler import Handler
from django_mysql.status import GlobalStatus
from django_mysql.utils import (
    StopWatch, WeightedAverageRate, have_program, noop_context,
    settings_to_cmd_args
)


class QuerySetMixin(object):

    # Stop complaints about access to qs._count_tries_approx and model._meta
    # pylint: disable=protected-access

    def __init__(self, *args, **kwargs):
        super(QuerySetMixin, self).__init__(*args, **kwargs)
        self._count_tries_approx = False

    def _clone(self, *args, **kwargs):
        clone = super(QuerySetMixin, self)._clone(*args, **kwargs)
        clone._count_tries_approx = copy(self._count_tries_approx)
        return clone

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
        query = self.query

        can_approx_count = (
            not query.where and
            query.high_mark is None and
            query.low_mark == 0 and
            not query.select and
            not query.group_by and
            not query.having and
            not query.distinct
        )

        if not can_approx_count:
            if not fall_back:
                raise ValueError("Cannot use approx_count on this queryset.")
            # Always fall through to super class
            return super(QuerySetMixin, self).count()

        connection = connections[self.db]
        with connection.cursor() as cursor:
            table_name = self.model._meta.db_table
            query = "EXPLAIN SELECT COUNT(*) FROM `{0}`".format(table_name)
            cursor.execute(query)
            approx_count = cursor.fetchone()[8]  # 'rows' is the 9th column

        if min_size and approx_count < min_size:
            # Always fall through to super class
            return super(QuerySetMixin, self).count()

        if return_approx_int:
            return ApproximateInt(approx_count)
        else:
            return approx_count

    def iter_smart(self, **kwargs):
        assert 'queryset' not in kwargs, \
            "You can't pass another queryset in through iter_smart!"
        return SmartIterator(queryset=self, **kwargs)

    def iter_smart_chunks(self, **kwargs):
        assert 'queryset' not in kwargs, \
            "You can't pass another queryset in through iter_smart_chunks!"
        return SmartChunkedIterator(queryset=self, **kwargs)

    def pt_visual_explain(self, display=True):
        return pt_visual_explain(self, display)

    def handler(self):
        return Handler(self)


class QuerySet(QuerySetMixin, models.QuerySet):
    pass


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
                 pk_range=None, chunk_time=0.5, chunk_max=10000,
                 report_progress=False, total=None):
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
        self.chunk_size = 2  # Small but will expand rapidly anyhow
        self.chunk_max = chunk_max

        self.report_progress = report_progress
        self.total = total

    def __iter__(self):
        min_pk, max_pk = self.get_min_and_max()
        current_pk = min_pk
        db_alias = self.queryset.db
        status = GlobalStatus(db_alias)

        self.init_progress()

        while current_pk <= max_pk:
            status.wait_until_load_low(self.status_thresholds)

            start_pk = current_pk
            current_pk = current_pk + self.chunk_size
            # Don't process rows that didn't exist at start of iteration
            end_pk = min(current_pk, max_pk + 1)

            with StopWatch() as timer, self.maybe_atomic(using=db_alias):
                chunk = self.queryset.filter(pk__gte=start_pk, pk__lt=end_pk)
                yield chunk
                self.update_progress(chunk=chunk, end_pk=end_pk)

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
        if not isinstance(pk, (models.IntegerField, models.AutoField)):
            raise ValueError(
                "You can't use %s on a model with a non-integer primary key." %
                self.__class__.__name__
            )

        return queryset.order_by('pk')

    def get_min_and_max(self):
        if isinstance(self.pk_range, tuple) and len(self.pk_range) == 2:
            return self.pk_range
        elif self.pk_range == 'all':
            base_qs = self.queryset.model.objects.using(self.queryset.db).all()
        elif self.pk_range is None:
            base_qs = self.queryset
        else:
            raise ValueError("Unrecognized value for pk_range: {}"
                             .format(self.pk_range))

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

        return (min_pk, max_pk)

    def adjust_chunk_size(self, chunk, chunk_time):
        # If the queryset is not being fetched as-is, e.g. its .delete() is
        # called, we can't know how many objects were affected, so we just
        # assume they all exist/existed
        if chunk._result_cache is None:
            num_processed = self.chunk_size
        else:
            num_processed = len(chunk)

        new_chunk_size = self.rate.update(num_processed, chunk_time)

        if new_chunk_size < 1:
            new_chunk_size = 1

        if new_chunk_size > self.chunk_max:
            new_chunk_size = self.chunk_max

        self.chunk_size = new_chunk_size

    def init_progress(self):
        if not self.report_progress:
            return

        self.have_reported = False
        self.objects_done = 0
        self.chunks_done = 0
        if self.total is None:  # User didn't pass in a total
            count_qs = self.queryset._clone(klass=QuerySet)
            self.total = count_qs.approx_count(fall_back=True)

        self.update_progress()

    def update_progress(self, chunk=None, end_pk=None):
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

        if not self.have_reported:
            self.have_reported = True
        else:
            # Reset line on successive outputs
            sys.stdout.write("\r")

        sys.stdout.write(
            "{} processed {}/{} objects ({:.2f}%) in {} chunks".format(
                self.model_name + self.__class__.__name__,
                self.objects_done,
                self.total,
                percent_complete,
                self.chunks_done,
            )
        )
        if end_pk is not None:
            sys.stdout.write("; highest pk so far {}".format(end_pk))
        sys.stdout.flush()

    def end_progress(self):
        if not self.report_progress:
            return

        sys.stdout.write("\nFinished!\n")

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
