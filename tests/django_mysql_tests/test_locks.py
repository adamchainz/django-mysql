# -*- coding:utf-8 -*-
from threading import Thread

from django.db import connection
from django.test import TestCase
from django.utils.six.moves import queue

from django_mysql.locks import Lock, TimeoutError


class LockTests(TestCase):

    def test_simple(self):
        mylock = Lock("mylock")
        self.assertFalse(mylock.is_held())

        with mylock:
            self.assertTrue(mylock.is_held())
            self.assertTrue(Lock("mylock").is_held())

            cursor = connection.cursor()
            cursor.execute("SELECT CONNECTION_ID();")
            own_connection_id = cursor.fetchone()[0]
            self.assertEqual(mylock.holding_connection_id(),
                             own_connection_id)

        self.assertFalse(mylock.is_held())
        self.assertFalse(Lock("mylock").is_held())

    import_time_lock = Lock('defined_at_import_time')

    def test_defined_at_import_time(self):
        import_time_lock = self.import_time_lock

        self.assertFalse(import_time_lock.is_held())

        with import_time_lock:
            self.assertTrue(import_time_lock.is_held())

            cursor = connection.cursor()
            cursor.execute("SELECT CONNECTION_ID();")
            own_connection_id = cursor.fetchone()[0]
            self.assertEqual(import_time_lock.holding_connection_id(),
                             own_connection_id)

        self.assertFalse(import_time_lock.is_held())

    def test_timeout_with_threads(self):
        to_me = queue.Queue()
        to_you = queue.Queue()

        def lock_until_told():
            with Lock('threading_test'):
                to_me.put("Locked")
                to_you.get(True)

        threading_test = Lock('threading_test', 0.05)
        self.assertTrue(not threading_test.is_held())

        other_thread = Thread(target=lock_until_told)
        other_thread.start()
        try:
            item = to_me.get(True)
            self.assertEqual(item, "Locked")

            cursor = connection.cursor()
            cursor.execute("SELECT CONNECTION_ID();")
            own_connection_id = cursor.fetchone()[0]

            self.assertTrue(threading_test.is_held())
            self.assertNotEqual(threading_test.holding_connection_id(),
                                own_connection_id)

            with self.assertRaises(TimeoutError):
                with threading_test:
                        pass

            to_you.put("Stop")
        finally:
            other_thread.join()

        self.assertFalse(threading_test.is_held())
        with threading_test:
            pass
