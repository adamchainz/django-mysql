# -*- coding:utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals,
)

import pytest
from django.test import TestCase

from django_mysql.exceptions import TimeoutError
from django_mysql.status import (
    GlobalStatus, SessionStatus, global_status, session_status,
)


class BaseStatusTests(TestCase):

    def test_cast_int(self):
        val = global_status._cast('1')
        assert val == 1 and isinstance(val, int)

    def test_cast_float(self):
        val = global_status._cast('1.0')
        assert val == 1.0 and isinstance(val, float)

    def test_cast_on(self):
        val = global_status._cast('ON')
        assert val and isinstance(val, bool)

    def test_cast_off(self):
        val = global_status._cast('OFF')
        assert not val and isinstance(val, bool)

    def test_cast_string(self):
        val = global_status._cast('something')
        assert val == 'something'


class GlobalStatusTests(TestCase):

    multi_db = True

    def test_get(self):
        running = global_status.get('Threads_running')
        assert running >= 1 and isinstance(running, int)

    def test_get_bad_name(self):
        with pytest.raises(ValueError) as excinfo:
            global_status.get('foo%')
        assert 'wildcards' in str(excinfo.value)

    def test_get_non_existent(self):
        with pytest.raises(KeyError):
            global_status.get('Does_not_exist')

    def test_get_many_empty(self):
        myvars = global_status.get_many([])
        assert myvars == {}

    def test_get_many_existent(self):
        myvars = global_status.get_many(['Threads_running', 'Uptime'])
        assert isinstance(myvars, dict)
        assert 'Threads_running' in myvars
        assert isinstance(myvars['Threads_running'], int)
        assert 'Uptime' in myvars
        assert isinstance(myvars['Uptime'], int)

    def test_get_many_bad_name(self):
        with pytest.raises(ValueError) as excinfo:
            global_status.get_many(['foo%'])
        assert 'wildcards' in str(excinfo.value)

    def test_as_dict(self):
        status_dict = global_status.as_dict()

        assert 'Aborted_clients' in status_dict  # Global-only variable

        assert isinstance(status_dict['Threads_running'], int)
        assert status_dict['Threads_running'] >= 1

    def test_as_dict_prefix(self):
        status_dict = global_status.as_dict()

        status_dict_threads = global_status.as_dict('Threads_')
        assert len(status_dict_threads) < len(status_dict)
        for key in status_dict_threads:
            assert key.startswith('Threads_')

        status_dict_foo = global_status.as_dict('Foo_Non_Existent')
        assert len(status_dict_foo) == 0

    def test_wait_until_load_low(self):
        # Assume tests are running on a non-busy server
        global_status.wait_until_load_low()
        global_status.wait_until_load_low({'Threads_running': 50,
                                           'Threads_connected': 100})

        with pytest.raises(TimeoutError) as excinfo:
            global_status.wait_until_load_low(
                {'Threads_running': -1},  # obviously impossible
                timeout=0.001,
                sleep=0.0005,
            )
        message = str(excinfo.value)
        assert 'Threads_running' in message
        assert '-1' in message

        with pytest.raises(TimeoutError) as excinfo:
            global_status.wait_until_load_low(
                {'Threads_running': 1000000,
                 'Uptime': -1},  # obviously impossible
                timeout=0.001,
                sleep=0.0005,
            )
        message = str(excinfo.value)
        assert 'Uptime' in message
        assert '-1' in message
        assert 'Threads_running' not in message
        assert '1000000' not in message

    def test_other_databases(self):
        status = GlobalStatus(using='other')

        running = status.get('Threads_running')
        assert isinstance(running, int)
        assert running >= 1


class SessionStatusTests(TestCase):

    def test_get_bytes_received(self):
        bytes_received = session_status.get('Bytes_received')
        assert bytes_received >= 0 and isinstance(bytes_received, int)

        bytes_received_2 = session_status.get('Bytes_received')
        assert bytes_received_2 >= bytes_received

    def test_get_last_query_cost(self):
        cost = session_status.get('Last_query_cost')
        assert cost >= 0.0 and isinstance(cost, float)

    def test_get_bad_name(self):
        with pytest.raises(ValueError) as excinfo:
            session_status.get('foo%')
        assert 'wildcards' in str(excinfo.value)

    def test_get_non_existent(self):
        with pytest.raises(KeyError):
            session_status.get('Does_not_exist')

    def test_as_dict(self):
        status_dict = session_status.as_dict()

        assert 'Compression' in status_dict  # status only variable (on 5.7+)

        assert isinstance(status_dict['Threads_running'], int)
        assert status_dict['Threads_running'] >= 1

    def test_other_databases(self):
        status = SessionStatus(using='other')
        running = status.get('Threads_running')
        assert isinstance(running, int)
        assert running >= 1
