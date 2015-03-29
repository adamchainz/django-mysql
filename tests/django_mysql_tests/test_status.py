# -*- coding:utf-8 -*-
from django.test import TestCase

from django_mysql.exceptions import TimeoutError
from django_mysql.status import (
    global_status, GlobalStatus, session_status, SessionStatus
)


class GlobalStatusTests(TestCase):

    def test_get(self):
        running = global_status.get('Threads_running')
        self.assertTrue(isinstance(running, int))
        self.assertGreaterEqual(running, 1)

        cost = global_status.get('Last_query_cost')
        self.assertTrue(isinstance(cost, float))
        self.assertGreaterEqual(cost, 0.00)

        with self.assertRaises(ValueError) as cm:
            global_status.get('foo%')
        self.assertIn('wildcards', str(cm.exception))

        with self.assertRaises(KeyError):
            global_status.get('Does_not_exist')

    def test_get_many(self):
        myvars = global_status.get_many([])
        self.assertEqual(myvars, {})

        myvars = global_status.get_many(['Threads_running', 'Uptime'])
        self.assertTrue(isinstance(myvars, dict))
        self.assertIn('Threads_running', myvars)
        self.assertTrue(isinstance(myvars['Threads_running'], int))
        self.assertIn('Uptime', myvars)
        self.assertTrue(isinstance(myvars['Uptime'], int))

        with self.assertRaises(ValueError) as cm:
            global_status.get_many(['foo%'])
        self.assertIn('wildcards', str(cm.exception))

    def test_as_dict(self):
        status_dict = global_status.as_dict()

        self.assertIn('Aborted_clients', status_dict)  # Global-only variable

        self.assertTrue(isinstance(status_dict['Threads_running'], int))
        self.assertGreaterEqual(status_dict['Threads_running'], 1)

        self.assertTrue(isinstance(status_dict['Last_query_cost'], float))
        self.assertGreaterEqual(status_dict['Last_query_cost'], 0.0)

        self.assertTrue(isinstance(status_dict['Compression'], bool))

    def test_as_dict_prefix(self):
        status_dict = global_status.as_dict()

        status_dict_threads = global_status.as_dict('Threads_')
        self.assertLess(len(status_dict_threads), len(status_dict))
        for key in status_dict_threads:
            self.assertTrue(key.startswith('Threads_'))

        status_dict_foo = global_status.as_dict('Foo_Non_Existent')
        self.assertEqual(len(status_dict_foo), 0)

    def test_wait_until_load_low(self):
        # Assume tests are running on a non-busy server
        global_status.wait_until_load_low()
        global_status.wait_until_load_low({'Threads_running': 50,
                                           'Threads_connected': 100})

        with self.assertRaises(TimeoutError) as cm:
            global_status.wait_until_load_low(
                {'Threads_running': -1},  # obviously impossible
                timeout=0.001,
                sleep=0.0005
            )
        message = str(cm.exception)
        self.assertIn('Threads_running', message)
        self.assertIn('-1', message)

        with self.assertRaises(TimeoutError) as cm:
            global_status.wait_until_load_low(
                {'Threads_running': 1000000,
                 'Uptime': -1},  # obviously impossible
                timeout=0.001,
                sleep=0.0005
            )
        message = str(cm.exception)
        self.assertIn('Uptime', message)
        self.assertIn('-1', message)
        self.assertNotIn('Threads_running', message)
        self.assertNotIn('1000000', message)

    def test_other_databases(self):
        status = GlobalStatus(using='secondary')

        running = status.get('Threads_running')
        self.assertTrue(isinstance(running, int))
        self.assertGreaterEqual(running, 1)


class SessionStatusTests(TestCase):

    def test_get(self):
        bytes_received = session_status.get('Bytes_received')
        self.assertTrue(isinstance(bytes_received, int))
        self.assertGreaterEqual(bytes_received, 0)

        bytes_received_2 = session_status.get('Bytes_received')
        self.assertGreaterEqual(bytes_received_2, bytes_received)

        cost = session_status.get('Last_query_cost')
        self.assertTrue(isinstance(cost, float))
        self.assertGreaterEqual(cost, 0.00)

        with self.assertRaises(ValueError) as cm:
            session_status.get('foo%')
        self.assertIn('wildcards', str(cm.exception))

        with self.assertRaises(KeyError):
            session_status.get('Does_not_exist')

    def test_as_dict(self):
        status_dict = session_status.as_dict()

        self.assertIn('Compression', status_dict)

        self.assertTrue(isinstance(status_dict['Threads_running'], int))
        self.assertGreaterEqual(status_dict['Threads_running'], 1)

    def test_other_databases(self):
        status = SessionStatus(using='secondary')
        running = status.get('Threads_running')
        self.assertTrue(isinstance(running, int))
        self.assertGreaterEqual(running, 1)
