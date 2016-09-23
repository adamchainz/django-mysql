# -*- coding:utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from django.db import connection
from django.test import TestCase
from django.test.utils import override_settings

from django_mysql.monkey_patches import patch_CursorWrapper_execute
from django_mysql.rewrite_query import rewrite_query
from testapp.utils import CaptureLastQuery


class RewriteQueryTests(TestCase):

    def test_it_doesnt_touch_normal_queries(self):
        self.check_identity("SELECT 1")
        self.check_identity("SELECT col_a, col_b FROM sometable WHERE 1")

    def test_bad_rewrites_ignored(self):
        assert (
            rewrite_query(
                "SELECT col_a FROM sometable "
                "WHERE (/*QueryRewrite':STRAY_JOIN*/1)"
            ) ==
            "SELECT col_a FROM sometable WHERE (1)"
        )
        assert (
            rewrite_query(
                "SELECT col_a FROM sometable "
                "WHERE (/*QueryRewrite':*/1)"
            ) ==
            "SELECT col_a FROM sometable WHERE (1)"
        )
        assert (
            rewrite_query(
                "UPDATE col_a SET pants='onfire' "
                "WHERE (/*QueryRewrite':STRAIGHT_JOIN*/1)"
            ) ==
            "UPDATE col_a SET pants='onfire' WHERE (1)"
        )

    def test_non_select_update_deletes_ignored(self):
        assert (
            rewrite_query("SHOW TABLES /*QueryRewrite':STRAIGHT_JOIN*/") ==
            "SHOW TABLES "
        )

    def check_identity(self, query):
        assert rewrite_query(query) == query

    def test_straight_join(self):
        assert (
            rewrite_query(
                "SELECT col_a, col_b FROM sometable "
                "WHERE nothing() AND (/*QueryRewrite':STRAIGHT_JOIN*/1)"
            ) ==
            "SELECT STRAIGHT_JOIN col_a, col_b FROM sometable "
            "WHERE nothing() AND (1)"
        )

    def test_straight_join_preceeding_whitespace(self):
        assert (
            rewrite_query(
                "  SELECT col_a, col_b FROM sometable "
                "WHERE nothing() AND (/*QueryRewrite':STRAIGHT_JOIN*/1)"
            ) ==
            "SELECT STRAIGHT_JOIN col_a, col_b FROM sometable "
            "WHERE nothing() AND (1)"
        )

    def test_straight_join_with_comment(self):
        assert (
            rewrite_query(
                "SELECT /* HI MUM */ col_a FROM sometable "
                "WHERE (/*QueryRewrite':STRAIGHT_JOIN*/1)"
            ) ==
            "SELECT /* HI MUM */ STRAIGHT_JOIN col_a FROM sometable "
            "WHERE (1)"
        )

    def test_straight_join_with_comments(self):
        assert (
            rewrite_query(
                "SELECT /* GOODBYE */ col_a FROM sometable "
                "WHERE (/*QueryRewrite':STRAIGHT_JOIN*/1)"
            ) ==
            "SELECT /* GOODBYE */ STRAIGHT_JOIN col_a FROM "
            "sometable WHERE (1)"
        )

    def test_straight_join_with_repeat_comments(self):
        assert (
            rewrite_query(
                "SELECT /* A */ /* B */ /* C */ col_a FROM sometable "
                "WHERE (/*QueryRewrite':STRAIGHT_JOIN*/1)"
            ) ==
            "SELECT /* A */ /* B */ /* C */ STRAIGHT_JOIN col_a FROM "
            "sometable WHERE (1)"
        )

    def test_straight_join_with_spaceless_comment(self):
        assert (
            rewrite_query(
                "SELECT/* this*/col_a FROM sometable "
                "WHERE (/*QueryRewrite':STRAIGHT_JOIN*/1)"
            ) ==
            "SELECT /* this*/ STRAIGHT_JOIN col_a FROM sometable WHERE (1)"
        )

    def test_straight_join_idempotent(self):
        assert (
            rewrite_query(
                "SELECT col_a, col_b FROM sometable "
                "WHERE nothing() AND (/*QueryRewrite':STRAIGHT_JOIN*/1) "
                "AND (/*QueryRewrite':STRAIGHT_JOIN*/1)"
            ) ==
            "SELECT STRAIGHT_JOIN col_a, col_b FROM sometable "
            "WHERE nothing() AND (1) AND (1)"
        )

    def test_straight_join_doesnt_affect_distinct(self):
        assert (
            rewrite_query(
                "SELECT DISTINCT col_a FROM sometable "
                "WHERE (/*QueryRewrite':STRAIGHT_JOIN*/1)"
            ) ==
            "SELECT DISTINCT STRAIGHT_JOIN col_a FROM sometable WHERE (1)"
        )

    def test_straight_join_doesnt_affect_all_and_highpriority(self):
        assert (
            rewrite_query(
                "SELECT ALL HIGH_PRIORITY col_a FROM sometable "
                "WHERE (/*QueryRewrite':STRAIGHT_JOIN*/1)"
            ) ==
            "SELECT ALL HIGH_PRIORITY STRAIGHT_JOIN col_a FROM sometable "
            "WHERE (1)"
        )

    def test_2_straight_joins_dont_affect_all_and_highpriority(self):
        assert (
            rewrite_query(
                "SELECT ALL HIGH_PRIORITY col_a FROM sometable "
                "WHERE (/*QueryRewrite':STRAIGHT_JOIN*/1) AND "
                "(/*QueryRewrite':STRAIGHT_JOIN*/1)"
            ) ==
            "SELECT ALL HIGH_PRIORITY STRAIGHT_JOIN col_a FROM sometable "
            "WHERE (1) AND (1)"
        )

    def test_multiple_hints(self):
        assert (
            rewrite_query(
                "SELECT col_a FROM sometable "
                "WHERE (/*QueryRewrite':STRAIGHT_JOIN*/1) AND "
                "(/*QueryRewrite':SQL_NO_CACHE*/1)"
            ) ==
            "SELECT STRAIGHT_JOIN SQL_NO_CACHE col_a FROM sometable "
            "WHERE (1) AND (1)"
        )

    def test_mutually_exclusive_latest_wins(self):
        assert (
            rewrite_query(
                "SELECT col_a FROM sometable "
                "WHERE (/*QueryRewrite':SQL_CACHE*/1) AND "
                "(/*QueryRewrite':SQL_NO_CACHE*/1)"
            ) ==
            "SELECT SQL_NO_CACHE col_a FROM sometable WHERE (1) AND (1)"
        )

    def test_labelling(self):
        assert (
            rewrite_query(
                "SELECT col_a FROM sometable "
                "WHERE (/*QueryRewrite':label=himum*/1)"
            ) ==
            "SELECT /*himum*/ col_a FROM sometable WHERE (1)"
        )

    def test_labelling_mysql_57_hint(self):
        assert (
            rewrite_query(
                "SELECT col_a FROM t1 "
                "WHERE (/*QueryRewrite':label=+ NO_RANGE_OPTIMIZATION(t1 "
                "PRIMARY) */1)"
            ) ==
            "SELECT /*+ NO_RANGE_OPTIMIZATION(t1 PRIMARY) */ col_a FROM t1 "
            "WHERE (1)"
        )

    def test_not_case_sensitive(self):
        assert (
            rewrite_query(
                "select col_a from sometable "
                "where (/*QueryRewrite':label=himum*/1)"
            ) ==
            "select /*himum*/ col_a from sometable "
            "where (1)"
        )

    def test_bad_query_not_rewritten(self):
        assert (
            rewrite_query(
                "SELECTSTRAIGHT_JOIN col_a FROM sometable"
                "WHERE (/*QueryRewrite':label=hi*/1)"
            ) ==
            "SELECTSTRAIGHT_JOIN col_a FROM sometable"
            "WHERE (1)"
        )

    def test_index_hint_use(self):
        assert (
            rewrite_query(
                "SELECT col_a FROM `sometable` WHERE "
                "(/*QueryRewrite':index=`sometable` USE `col_a_idx`*/1)"
            ) ==
            "SELECT col_a FROM `sometable` USE INDEX (`col_a_idx`) WHERE (1)"
        )

    def test_index_ignore(self):
        assert (
            rewrite_query(
                "SELECT col_a FROM `sometable` WHERE "
                "(/*QueryRewrite':index=`sometable` IGNORE `col_a_idx`*/1)"
            ) ==
            "SELECT col_a FROM `sometable` IGNORE INDEX (`col_a_idx`) "
            "WHERE (1)"
        )

    def test_index_force(self):
        assert (
            rewrite_query(
                "SELECT col_a FROM `sometable` WHERE "
                "(/*QueryRewrite':index=`sometable` FORCE `col_a_idx`*/1)"
            ) ==
            "SELECT col_a FROM `sometable` FORCE INDEX (`col_a_idx`) "
            "WHERE (1)"
        )

    def test_index_nonsense_does_nothing(self):
        assert (
            rewrite_query(
                "SELECT col_a FROM `sometable` WHERE "
                "(/*QueryRewrite':index=`sometable` MAHOGANY `col_a_idx`*/1)"
            ) ==
            "SELECT col_a FROM `sometable` WHERE (1)"
        )

    def test_index_hint_use_secondary(self):
        assert (
            rewrite_query(
                "SELECT col_a, col_b FROM `sometable` INNER JOIN `othertable` "
                " WHERE (/*QueryRewrite':index=`othertable` USE `myindex`*/1)"
            ) ==
            "SELECT col_a, col_b FROM `sometable` INNER JOIN `othertable` "
            "USE INDEX (`myindex`) WHERE (1)"
        )

    def test_index_hint_multiple_indexes(self):
        assert (
            rewrite_query(
                "SELECT col_a FROM `tabl` WHERE "
                "(/*QueryRewrite':index=`tabl` IGNORE `idx1`,`idx2`*/1)"
            ) ==
            "SELECT col_a FROM `tabl` IGNORE INDEX (`idx1`,`idx2`) WHERE (1)"
        )

    def test_index_hint_multiple_hints(self):
        assert (
            rewrite_query(
                "SELECT col_a FROM `sometable` "
                "WHERE (/*QueryRewrite':index=`sometable` IGNORE `idx1`*/1) "
                "AND (/*QueryRewrite':index=`sometable` IGNORE `idx2`*/1)"
            ) ==
            "SELECT col_a FROM `sometable` IGNORE INDEX (`idx2`) "
            "IGNORE INDEX (`idx1`) WHERE (1) AND (1)"
        )

    def test_index_hint_for_join(self):
        assert (
            rewrite_query(
                "SELECT `sometable`.col_a, `sometable2`.col_b "
                "FROM `sometable` NATURAL JOIN `sometable2` "
                "WHERE (/*QueryRewrite':index=`sometable` IGNORE FOR JOIN "
                "`idx`*/1)"
            ) ==
            "SELECT `sometable`.col_a, `sometable2`.col_b FROM `sometable` "
            "IGNORE INDEX FOR JOIN (`idx`) "
            "NATURAL JOIN `sometable2` WHERE (1)"
        )

    def test_index_hint_for_group_by(self):
        assert (
            rewrite_query(
                "SELECT col_a, SUM(col_b) FROM `sometable` "
                "WHERE (/*QueryRewrite':index=`sometable` FORCE FOR GROUP BY "
                "`idx`*/1) GROUP BY col_a"
            ) ==
            "SELECT col_a, SUM(col_b) FROM `sometable` FORCE INDEX FOR GROUP "
            "BY (`idx`) WHERE (1) GROUP BY col_a"
        )

    def test_index_hint_for_order_by(self):
        assert (
            rewrite_query(
                "SELECT col_a FROM `sometable` "
                "WHERE (/*QueryRewrite':index=`sometable` USE FOR ORDER BY "
                "`idx` */1) ORDER BY col_a"
            ) ==
            "SELECT col_a FROM `sometable` USE INDEX FOR ORDER BY (`idx`) "
            "WHERE (1) ORDER BY col_a"
        )

    def test_it_is_monkey_patched(self):
        with CaptureLastQuery() as cap, connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM DUAL "
                           "WHERE (/*QueryRewrite':STRAIGHT_JOIN*/1)")
        assert cap.query == "SELECT STRAIGHT_JOIN 1 FROM DUAL WHERE (1)"

    @override_settings(DJANGO_MYSQL_REWRITE_QUERIES=False)
    def test_monkey_patch_can_be_disabled(self):
        query = "SELECT 1 FROM DUAL WHERE (/*QueryRewrite':STRAIGHT_JOIN*/1)"
        with CaptureLastQuery() as cap, connection.cursor() as cursor:
            cursor.execute(query)
        cap.query == query

    def test_can_monkey_patch_is_idempotent(self):
        patch_CursorWrapper_execute()

        with CaptureLastQuery() as cap, connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM DUAL WHERE (/*QueryRewrite':label=hi*/1)")
        assert cap.query == "SELECT /*hi*/ 1 FROM DUAL WHERE (1)"
