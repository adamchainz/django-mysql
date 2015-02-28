# -*- coding:utf-8 -*-
from copy import copy
import sys

from django.db import connections
from django.db import models
from django.db.transaction import atomic
from django.utils import six
from django.utils.functional import cached_property
from django.utils.translation import ugettext as _

from .status import GlobalStatus
from .utils import noop_context, StopWatch, WeightedAverageRate


class QuerySetMixin(object):

    def __init__(self, *args, **kwargs):
        super(QuerySetMixin, self).__init__(*args, **kwargs)
        self._count_tries_approx = False

    def _clone(self, *args, **kwargs):
        qs = super(QuerySetMixin, self)._clone(*args, **kwargs)
        qs._count_tries_approx = copy(self._count_tries_approx)
        return qs

    def count(self):
        if self._count_tries_approx:
            return self.approx_count(**self._count_tries_approx)
        return super(QuerySetMixin, self).count()

    def count_tries_approx(self, activate=True, fall_back=True,
                           return_approx_int=True, min_size=1000):
        qs = self._clone()

        if activate:
            qs._count_tries_approx = {
                'fall_back': fall_back,
                'return_approx_int': return_approx_int,
                'min_size': min_size,
            }
        else:
            qs._count_tries_approx = False

        return qs

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
            return self.count()

        connection = connections[self.db]
        with connection.cursor() as cursor:
            table_name = self.model._meta.db_table
            query = "EXPLAIN SELECT COUNT(*) FROM `{0}`".format(table_name)
            cursor.execute(query)
            approx_count = cursor.fetchone()[8]  # 'rows' is the 9th column

        if min_size and approx_count < min_size:
            return self.count()

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


class QuerySet(QuerySetMixin, models.QuerySet):
    pass


class Model(models.Model):
    class Meta(object):
        abstract = True

    objects = QuerySet.as_manager()


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
                 chunk_time=0.1, chunk_max=10000, report_progress=False,
                 total=None):
        self.queryset = self.sanitize_queryset(queryset)

        if atomically:
            self.maybe_atomic = atomic
        else:
            # Work around for `with` statement not supporting variable number
            # of contexts
            self.maybe_atomic = noop_context

        self.status_thresholds = status_thresholds

        self.rate = WeightedAverageRate(chunk_time)
        self.chunk_size = 2  # Small but will expand rapidly anyhow
        self.chunk_max = chunk_max

        self.report_progress = report_progress
        self.total = total

    def __iter__(self):
        min_pk, max_pk = self.get_min_and_max()
        current_pk = min_pk
        status = GlobalStatus(self.queryset.db)

        self.init_progress()

        while current_pk <= max_pk:
            status.wait_until_load_low(self.status_thresholds)

            start_pk = current_pk
            current_pk = current_pk + self.chunk_size
            # Don't process rows that didn't exist at start of iteration
            end_pk = min(current_pk, max_pk + 1)

            with StopWatch() as timer, self.maybe_atomic():
                chunk = self.queryset.filter(pk__gte=start_pk, pk__lt=end_pk)
                yield chunk
                self.update_progress(chunk=chunk, end_pk=end_pk)

            self.adjust_chunk_size(chunk, timer.total_time)

        self.end_progress()

    def sanitize_queryset(self, queryset):
        if queryset.ordered:
            raise ValueError(
                "You can't use %s on a queryset with an ordering.",
                self.__class__.__name__
            )

        if queryset.query.low_mark or queryset.query.high_mark:
            raise ValueError(
                "You can't use %s on a sliced queryset.",
                self.__class__.__name__
            )

        return queryset.order_by('pk')

    def get_min_and_max(self):
        min_qs = self.queryset.order_by('pk').values_list('pk', flat=True)
        max_qs = self.queryset.order_by('-pk').values_list('pk', flat=True)
        try:
            min_pk = min_qs[0]
        except IndexError:
            # We're working on an empty QuerySet, yield no chunks
            return (0, 0)
            max_pk = min_pk = 0
        else:
            max_pk = max_qs[0]

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
            try:
                self.total = self.queryset.approx_count(fall_back=False)
            except ValueError:
                self.total = self.queryset.count()

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
