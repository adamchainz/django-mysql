# -*- coding:utf-8 -*-
from copy import copy

from django.db import connections
from django.db import models
from django.utils import six
from django.utils.translation import ugettext as _


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
