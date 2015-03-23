# -*- coding:utf-8 -*-
from django.test import TestCase

from django_mysql.exceptions import TimeoutError
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

    def test_get_many(self):
        status = GlobalStatus()

        myvars = status.get_many([])
        self.assertEqual(myvars, {})

        myvars = status.get_many(['Threads_running', 'Uptime'])
        self.assertTrue(isinstance(myvars, dict))
        self.assertIn('Threads_running', myvars)
        self.assertTrue(isinstance(myvars['Threads_running'], int))
        self.assertIn('Uptime', myvars)
        self.assertTrue(isinstance(myvars['Uptime'], int))

        with self.assertRaises(ValueError) as cm:
            status.get_many(['foo%'])
        self.assertIn('wildcards', str(cm.exception))

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

    def test_wait_until_load_low(self):
        status = GlobalStatus()

        # Assume tests are running on a non-busy server
        status.wait_until_load_low()
        status.wait_until_load_low({'Threads_running': 50,
                                    'Threads_connected': 100})

        with self.assertRaises(TimeoutError) as cm:
            status.wait_until_load_low(
                {'Threads_running': -1},  # obviously impossible
                timeout=0.001,
                sleep=0.0005
            )
        message = str(cm.exception)
        self.assertIn('Threads_running', message)
        self.assertIn('-1', message)

        with self.assertRaises(TimeoutError) as cm:
            status.wait_until_load_low(
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
