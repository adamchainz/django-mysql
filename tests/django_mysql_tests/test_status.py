# -*- coding:utf-8 -*-
from django.test import TestCase

from django_mysql.status import GlobalStatus, SessionStatus


class GlobalStatusTests(TestCase):

    def test_get(self):
        status = GlobalStatus()
        running = status.get('Threads_running')
        self.assertTrue(isinstance(running, int))
        self.assertGreaterEqual(running, 1)

        cost = status.get('Last_query_cost')
        self.assertTrue(isinstance(cost, float))
        self.assertGreaterEqual(cost, 0.00)

        with self.assertRaises(ValueError) as cm:
            status.get('foo%')
        self.assertIn('wildcards', str(cm.exception))

        with self.assertRaises(KeyError):
            status.get('Does_not_exist')

    def test_as_dict(self):
        status = GlobalStatus()
        status_dict = status.as_dict()

        self.assertIn('Aborted_clients', status_dict)  # Global-only variable

        self.assertTrue(isinstance(status_dict['Threads_running'], int))
        self.assertGreaterEqual(status_dict['Threads_running'], 1)

        self.assertTrue(isinstance(status_dict['Last_query_cost'], float))
        self.assertGreaterEqual(status_dict['Last_query_cost'], 0.0)

        self.assertTrue(isinstance(status_dict['Compression'], bool))

    def test_as_dict_prefix(self):
        status = GlobalStatus()
        status_dict = status.as_dict()

        status_dict_threads = status.as_dict('Threads_')
        self.assertLess(len(status_dict_threads), len(status_dict))
        for key in status_dict_threads:
            self.assertTrue(key.startswith('Threads_'))

        status_dict_foo = status.as_dict('Foo_Non_Existent')
        self.assertEqual(len(status_dict_foo), 0)


class SessionStatusTests(TestCase):

    def test_get(self):
        status = SessionStatus()

        bytes_received = status.get('Bytes_received')
        self.assertTrue(isinstance(bytes_received, int))
        self.assertGreaterEqual(bytes_received, 0)

        bytes_received_2 = status.get('Bytes_received')
        self.assertGreaterEqual(bytes_received_2, bytes_received)

        cost = status.get('Last_query_cost')
        self.assertTrue(isinstance(cost, float))
        self.assertGreaterEqual(cost, 0.00)

        with self.assertRaises(ValueError) as cm:
            status.get('foo%')
        self.assertIn('wildcards', str(cm.exception))

        with self.assertRaises(KeyError):
            status.get('Does_not_exist')

    def test_as_dict(self):
        status = SessionStatus()
        status_dict = status.as_dict()

        self.assertIn('Compression', status_dict)

        self.assertTrue(isinstance(status_dict['Threads_running'], int))
        self.assertGreaterEqual(status_dict['Threads_running'], 1)
