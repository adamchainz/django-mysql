# -*- coding:utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals,
)

import imp
import os
import time
from decimal import Decimal
from unittest import skipUnless

import django
import pytest
from django.core.cache import CacheKeyWarning, cache, caches
from django.core.management import CommandError, call_command
from django.db import IntegrityError, OperationalError, connection
from django.db.migrations.state import ProjectState
from django.http import HttpResponse
from django.middleware.cache import (
    FetchFromCacheMiddleware, UpdateCacheMiddleware,
)
from django.test import RequestFactory, TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.utils import six
from django.utils.six.moves import StringIO
from parameterized import parameterized

from django_mysql.cache import BIGINT_SIGNED_MAX, BIGINT_SIGNED_MIN, MySQLCache
from testapp.models import Poll, expensive_calculation

try:    # Use the same idiom as in cache backends
    from django.utils.six.moves import cPickle as pickle
except ImportError:  # pragma: no cover
    import pickle


# functions/classes for complex data type tests
def f():
    return 42


class C:
    def m(n):
        return 24


class Unpickable(object):
    def __getstate__(self):
        raise pickle.PickleError()


class MyInt(int):
    def times2(self):
        return self * 2


def custom_key_func(key, key_prefix, version):
    "A customized cache key function"
    return 'CUSTOM-' + '-'.join([key_prefix, str(version), key])


def reverse_custom_key_func(full_key):
    "The reverse of custom_key_func"
    # Remove CUSTOM-
    full_key = full_key[len('CUSTOM-'):]

    first_dash = full_key.find('-')
    key_prefix = full_key[:first_dash]

    second_dash = full_key.find('-', first_dash + 1)
    version = int(full_key[first_dash + 1:second_dash])

    key = full_key[second_dash + 1:]

    return key, key_prefix, version


_caches_setting_base = {
    'default': {},
    'prefix': {'KEY_PREFIX': 'cacheprefix{}'.format(os.getpid())},
    'v2': {'VERSION': 2},
    'custom_key': {'KEY_FUNCTION': custom_key_func,
                   'REVERSE_KEY_FUNCTION': reverse_custom_key_func},
    'custom_key2': {
        'KEY_FUNCTION':
            'testapp.test_cache.custom_key_func',
        'REVERSE_KEY_FUNCTION':
            'testapp.test_cache.reverse_custom_key_func',
    },
    'cull': {'OPTIONS': {'CULL_PROBABILITY': 1,
                         'MAX_ENTRIES': 30}},
    'zero_cull': {'OPTIONS': {'CULL_FREQUENCY': 0,
                              'CULL_PROBABILITY': 1,
                              'MAX_ENTRIES': 30}},
    'no_cull': {'OPTIONS': {'CULL_FREQUENCY': 2,
                            'CULL_PROBABILITY': 0,
                            'MAX_ENTRIES': 30}},
}


def caches_setting_for_tests(options=None, **params):
    # `params` are test specific overrides and `_caches_settings_base` is the
    # base config for the tests.
    # This results in the following search order:
    # params -> _caches_setting_base -> base
    setting = {k: {} for k in _caches_setting_base.keys()}
    for key, cache_params in setting.items():
        cache_params.update(_caches_setting_base[key])
        cache_params.update(params)
        if options is not None:
            cache_params['OPTIONS'] = cache_params.get('OPTIONS', {}).copy()
            cache_params['OPTIONS'].update(**options)
    return setting


# Spaces are used in the table name to ensure quoting/escaping is working
def override_cache_settings(BACKEND='django_mysql.cache.MySQLCache',
                            LOCATION='test cache table',
                            **kwargs):
    return override_settings(
        CACHES=caches_setting_for_tests(
            BACKEND=BACKEND,
            LOCATION=LOCATION,
            **kwargs
        ),
    )


class MySQLCacheTableMixin(TransactionTestCase):

    table_name = 'test cache table'

    @classmethod
    def create_table(self):
        sql = MySQLCache.create_table_sql.format(table_name=self.table_name)
        with connection.cursor() as cursor:
            cursor.execute(sql)

    @classmethod
    def drop_table(self):
        with connection.cursor() as cursor:
            cursor.execute('DROP TABLE `%s`' % self.table_name)


@override_cache_settings()
class MySQLCacheTests(MySQLCacheTableMixin, TestCase):

    @classmethod
    def setUpClass(cls):
        cls.create_table()
        super(MySQLCacheTests, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(MySQLCacheTests, cls).tearDownClass()
        cls.drop_table()

    def table_count(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM `%s`" % self.table_name)
            return cursor.fetchone()[0]

    # These tests were copied from django's tests/cache/tests.py file

    def test_simple(self):
        # Simple cache set/get works
        cache.set("key", "value")
        assert cache.get("key") == "value"

    def test_add(self):
        # A key can be added to a cache
        result = cache.add("addkey1", "value")
        assert result
        result = cache.add("addkey1", "newvalue")
        assert not result
        assert cache.get("addkey1") == "value"

    def test_prefix(self):
        # Test for same cache key conflicts between shared backend
        cache.set('somekey', 'value')

        # should not be set in the prefixed cache
        assert not caches['prefix'].has_key('somekey')  # noqa

        caches['prefix'].set('somekey', 'value2')

        assert cache.get('somekey') == 'value'
        assert caches['prefix'].get('somekey') == 'value2'

    def test_non_existent(self):
        # Non-existent cache keys return as None/default
        # get with non-existent keys
        assert cache.get("does_not_exist") is None
        assert cache.get("does_not_exist", "bang!") == "bang!"

    def test_delete(self):
        # Cache keys can be deleted
        cache.set("key1", "spam")
        cache.set("key2", "eggs")
        assert cache.get("key1") == "spam"
        cache.delete("key1")
        assert cache.get("key1") is None
        assert cache.get("key2") == "eggs"

    def test_has_key(self):
        # The cache can be inspected for cache keys
        cache.set("hello1", "goodbye1")
        assert cache.has_key("hello1")  # noqa
        assert not cache.has_key("goodbye1")  # noqa
        cache.set("no_expiry", "here", None)
        assert cache.has_key("no_expiry")  # noqa

    def test_in(self):
        # The in operator can be used to inspect cache contents
        cache.set("hello2", "goodbye2")
        assert "hello2" in cache
        assert "goodbye2" not in cache

    def test_incr(self):
        # Cache values can be incremented
        cache.set('answer', 41)
        assert cache.incr('answer') == 42
        assert cache.get('answer') == 42
        assert cache.incr('answer', 10) == 52
        assert cache.get('answer') == 52
        assert cache.incr('answer', -10) == 42
        with pytest.raises(ValueError):
            cache.incr('does_not_exist')

    def test_decr(self):
        # Cache values can be decremented
        cache.set('answer', 43)
        assert cache.decr('answer') == 42
        assert cache.get('answer') == 42
        assert cache.decr('answer', 10) == 32
        assert cache.get('answer') == 32
        assert cache.decr('answer', -10) == 42
        with pytest.raises(ValueError):
            cache.decr('does_not_exist')

    def test_close(self):
        assert hasattr(cache, 'close')
        cache.close()

    def test_data_types(self):
        # Many different data types can be cached
        stuff = {
            'string': 'this is a string',
            'int': 42,
            'list': [1, 2, 3, 4],
            'tuple': (1, 2, 3, 4),
            'dict': {'A': 1, 'B': 2},
            'function': f,
            'class': C,
        }
        cache.set("stuff", stuff)
        assert cache.get("stuff") == stuff

    def test_cache_read_for_model_instance(self):
        # Don't want fields with callable as default to be called on cache read
        expensive_calculation.num_runs = 0
        Poll.objects.all().delete()
        my_poll = Poll.objects.create(question="Well?")
        assert Poll.objects.count() == 1
        pub_date = my_poll.pub_date
        cache.set('question', my_poll)
        cached_poll = cache.get('question')
        assert cached_poll.pub_date == pub_date
        # We only want the default expensive calculation run once
        assert expensive_calculation.num_runs == 1

    def test_cache_write_for_model_instance_with_deferred(self):
        # Don't want fields with callable as default to be called on cache
        # write
        expensive_calculation.num_runs = 0
        Poll.objects.all().delete()
        Poll.objects.create(question="What?")
        assert expensive_calculation.num_runs == 1
        defer_qs = Poll.objects.all().defer('question')
        assert defer_qs.count() == 1
        assert expensive_calculation.num_runs == 1
        cache.set('deferred_queryset', defer_qs)
        # cache set should not re-evaluate default functions
        assert expensive_calculation.num_runs == 1

    def test_cache_read_for_model_instance_with_deferred(self):
        # Don't want fields with callable as default to be called on cache read
        expensive_calculation.num_runs = 0
        Poll.objects.all().delete()
        Poll.objects.create(question="What?")
        assert expensive_calculation.num_runs == 1
        defer_qs = Poll.objects.all().defer('question')
        assert defer_qs.count() == 1
        cache.set('deferred_queryset', defer_qs)
        assert expensive_calculation.num_runs == 1
        runs_before_cache_read = expensive_calculation.num_runs
        cache.get('deferred_queryset')
        # We only want the default expensive calculation run on creation and
        # set
        assert expensive_calculation.num_runs == runs_before_cache_read

    def test_unicode(self):
        # Unicode values can be cached
        stuff = {
            'ascii': 'ascii_value',
            'unicode_ascii': 'Iñtërnâtiônàlizætiøn1',
            'Iñtërnâtiônàlizætiøn': 'Iñtërnâtiônàlizætiøn2',
            'ascii2': {'x': 1},
        }
        # Test `set`
        for (key, value) in stuff.items():
            cache.set(key, value)
            assert cache.get(key) == value

        # Test `add`
        for (key, value) in stuff.items():
            cache.delete(key)
            cache.add(key, value)
            assert cache.get(key) == value

        # Test `set_many`
        for (key, value) in stuff.items():
            cache.delete(key)
        cache.set_many(stuff)
        for (key, value) in stuff.items():
            assert cache.get(key) == value

    def test_binary_string(self):
        # Binary strings should be cacheable
        from zlib import compress, decompress
        value = 'value_to_be_compressed'
        compressed_value = compress(value.encode())

        # Test set
        cache.set('binary1', compressed_value)
        compressed_result = cache.get('binary1')
        assert compressed_value == compressed_result
        assert value == decompress(compressed_result).decode()

        # Test add
        cache.add('binary1-add', compressed_value)
        compressed_result = cache.get('binary1-add')
        assert compressed_value == compressed_result
        assert value == decompress(compressed_result).decode()

        # Test set_many
        cache.set_many({'binary1-set_many': compressed_value})
        compressed_result = cache.get('binary1-set_many')
        assert compressed_value == compressed_result
        assert value == decompress(compressed_result).decode()

    def test_clear(self):
        # The cache can be emptied using clear
        cache.set("key1", "spam")
        cache.set("key2", "eggs")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_touch_without_timeout(self):
        cache.set("key1", "spam", timeout=0.1)
        cache.touch("key1", timeout=0.4)
        time.sleep(0.2)
        assert "key1" in cache

    def test_touch_with_timeout(self):
        cache.set("key1", "spam", timeout=0.1)
        cache.touch("key1")
        time.sleep(0.2)
        assert "key1" in cache

    def test_touch_already_expired(self):
        cache.set("key1", "spam", timeout=0.1)
        time.sleep(0.2)
        cache.touch("key1", timeout=0.4)
        assert "key1" not in cache

    def test_long_timeout(self):
        '''
        Using a timeout greater than 30 days makes memcached think
        it is an absolute expiration timestamp instead of a relative
        offset. Test that we honour this convention. Refs #12399.
        '''
        cache.set('key1', 'eggs', 60 * 60 * 24 * 30 + 1)  # 30 days + 1 second
        assert cache.get('key1') == 'eggs'

        cache.add('key2', 'ham', 60 * 60 * 24 * 30 + 1)
        assert cache.get('key2') == 'ham'

        cache.set_many(
            {'key3': 'sausage', 'key4': 'lobster bisque'},
            60 * 60 * 24 * 30 + 1
        )
        assert cache.get('key3') == 'sausage'
        assert cache.get('key4') == 'lobster bisque'

    def test_forever_timeout(self):
        '''
        Passing in None into timeout results in a value that is cached forever
        '''
        cache.set('key1', 'eggs', None)
        assert cache.get('key1') == 'eggs'

        cache.add('key2', 'ham', None)
        assert cache.get('key2') == 'ham'
        added = cache.add('key1', 'new eggs', None)
        assert not added
        assert cache.get('key1') == 'eggs'

        cache.set_many({'key3': 'sausage', 'key4': 'lobster bisque'}, None)
        assert cache.get('key3') == 'sausage'
        assert cache.get('key4') == 'lobster bisque'

    def test_zero_timeout(self):
        '''
        Passing in zero into timeout results in a value that is not cached
        '''
        cache.set('key1', 'eggs', 0)
        assert cache.get('key1') is None

        cache.add('key2', 'ham', 0)
        assert cache.get('key2') is None

        cache.set_many({'key3': 'sausage', 'key4': 'lobster bisque'}, 0)
        assert cache.get('key3') is None
        assert cache.get('key4') is None

    def test_float_timeout(self):
        # Make sure a timeout given as a float doesn't crash anything.
        cache.set("key1", "spam", 100.2)
        assert cache.get("key1") == "spam"

    def test_cache_versioning_get_set(self):
        # set, using default version = 1
        cache.set('answer1', 42)
        assert cache.get('answer1') == 42
        assert cache.get('answer1', version=1) == 42
        assert cache.get('answer1', version=2) is None

        assert caches['v2'].get('answer1') is None
        assert caches['v2'].get('answer1', version=1) == 42
        assert caches['v2'].get('answer1', version=2) is None

        # set, default version = 1, but manually override version = 2
        cache.set('answer2', 42, version=2)
        assert cache.get('answer2') is None
        assert cache.get('answer2', version=1) is None
        assert cache.get('answer2', version=2) == 42

        assert caches['v2'].get('answer2') == 42
        assert caches['v2'].get('answer2', version=1) is None
        assert caches['v2'].get('answer2', version=2) == 42

        # v2 set, using default version = 2
        caches['v2'].set('answer3', 42)
        assert cache.get('answer3') is None
        assert cache.get('answer3', version=1) is None
        assert cache.get('answer3', version=2) == 42

        assert caches['v2'].get('answer3') == 42
        assert caches['v2'].get('answer3', version=1) is None
        assert caches['v2'].get('answer3', version=2) == 42

        # v2 set, default version = 2, but manually override version = 1
        caches['v2'].set('answer4', 42, version=1)
        assert cache.get('answer4') == 42
        assert cache.get('answer4', version=1) == 42
        assert cache.get('answer4', version=2) is None

        assert caches['v2'].get('answer4') is None
        assert caches['v2'].get('answer4', version=1) == 42
        assert caches['v2'].get('answer4', version=2) is None

    def test_cache_versioning_add(self):

        # add, default version = 1, but manually override version = 2
        cache.add('answer1', 42, version=2)
        assert cache.get('answer1', version=1) is None
        assert cache.get('answer1', version=2) == 42

        cache.add('answer1', 37, version=2)
        assert cache.get('answer1', version=1) is None
        assert cache.get('answer1', version=2) == 42

        cache.add('answer1', 37, version=1)
        assert cache.get('answer1', version=1) == 37
        assert cache.get('answer1', version=2) == 42

        # v2 add, using default version = 2
        caches['v2'].add('answer2', 42)
        assert cache.get('answer2', version=1) is None
        assert cache.get('answer2', version=2) == 42

        caches['v2'].add('answer2', 37)
        assert cache.get('answer2', version=1) is None
        assert cache.get('answer2', version=2) == 42

        caches['v2'].add('answer2', 37, version=1)
        assert cache.get('answer2', version=1) == 37
        assert cache.get('answer2', version=2) == 42

        # v2 add, default version = 2, but manually override version = 1
        caches['v2'].add('answer3', 42, version=1)
        assert cache.get('answer3', version=1) == 42
        assert cache.get('answer3', version=2) is None

        caches['v2'].add('answer3', 37, version=1)
        assert cache.get('answer3', version=1) == 42
        assert cache.get('answer3', version=2) is None

        caches['v2'].add('answer3', 37)
        assert cache.get('answer3', version=1) == 42
        assert cache.get('answer3', version=2) == 37

    def test_cache_versioning_has_key(self):
        cache.set('answer1', 42)

        # has_key
        assert cache.has_key('answer1')  # noqa
        assert cache.has_key('answer1', version=1)  # noqa
        assert not cache.has_key('answer1', version=2)  # noqa

        assert not caches['v2'].has_key('answer1')  # noqa
        assert caches['v2'].has_key('answer1', version=1)  # noqa
        assert not caches['v2'].has_key('answer1', version=2)  # noqa

    def test_cache_versioning_delete(self):
        cache.set('answer1', 37, version=1)
        cache.set('answer1', 42, version=2)
        cache.delete('answer1')
        assert cache.get('answer1', version=1) is None
        assert cache.get('answer1', version=2) == 42

        cache.set('answer2', 37, version=1)
        cache.set('answer2', 42, version=2)
        cache.delete('answer2', version=2)
        assert cache.get('answer2', version=1) == 37
        assert cache.get('answer2', version=2) is None

        cache.set('answer3', 37, version=1)
        cache.set('answer3', 42, version=2)
        caches['v2'].delete('answer3')
        assert cache.get('answer3', version=1) == 37
        assert cache.get('answer3', version=2) is None

        cache.set('answer4', 37, version=1)
        cache.set('answer4', 42, version=2)
        caches['v2'].delete('answer4', version=1)
        assert cache.get('answer4', version=1) is None
        assert cache.get('answer4', version=2) == 42

    def test_cache_versioning_incr_decr(self):
        cache.set('answer1', 37, version=1)
        cache.set('answer1', 42, version=2)
        cache.incr('answer1')
        assert cache.get('answer1', version=1) == 38
        assert cache.get('answer1', version=2) == 42
        cache.decr('answer1')
        assert cache.get('answer1', version=1) == 37
        assert cache.get('answer1', version=2) == 42

        cache.set('answer2', 37, version=1)
        cache.set('answer2', 42, version=2)
        cache.incr('answer2', version=2)
        assert cache.get('answer2', version=1) == 37
        assert cache.get('answer2', version=2) == 43
        cache.decr('answer2', version=2)
        assert cache.get('answer2', version=1) == 37
        assert cache.get('answer2', version=2) == 42

        cache.set('answer3', 37, version=1)
        cache.set('answer3', 42, version=2)
        caches['v2'].incr('answer3')
        assert cache.get('answer3', version=1) == 37
        assert cache.get('answer3', version=2) == 43
        caches['v2'].decr('answer3')
        assert cache.get('answer3', version=1) == 37
        assert cache.get('answer3', version=2) == 42

        cache.set('answer4', 37, version=1)
        cache.set('answer4', 42, version=2)
        caches['v2'].incr('answer4', version=1)
        assert cache.get('answer4', version=1) == 38
        assert cache.get('answer4', version=2) == 42
        caches['v2'].decr('answer4', version=1)
        assert cache.get('answer4', version=1) == 37
        assert cache.get('answer4', version=2) == 42

    def test_cache_versioning_get_set_many(self):
        # set, using default version = 1
        cache.set_many({'ford1': 37, 'arthur1': 42})
        assert (
            cache.get_many(['ford1', 'arthur1']) ==
            {'ford1': 37, 'arthur1': 42}
        )
        assert (
            cache.get_many(['ford1', 'arthur1'], version=1) ==
            {'ford1': 37, 'arthur1': 42}
        )
        assert cache.get_many(['ford1', 'arthur1'], version=2) == {}

        assert caches['v2'].get_many(['ford1', 'arthur1']) == {}
        assert (
            caches['v2'].get_many(['ford1', 'arthur1'], version=1) ==
            {'ford1': 37, 'arthur1': 42}
        )
        assert caches['v2'].get_many(['ford1', 'arthur1'], version=2) == {}

        # set, default version = 1, but manually override version = 2
        cache.set_many({'ford2': 37, 'arthur2': 42}, version=2)
        assert cache.get_many(['ford2', 'arthur2']) == {}
        assert cache.get_many(['ford2', 'arthur2'], version=1) == {}
        assert (
            cache.get_many(['ford2', 'arthur2'], version=2) ==
            {'ford2': 37, 'arthur2': 42}
        )

        assert (
            caches['v2'].get_many(['ford2', 'arthur2']) ==
            {'ford2': 37, 'arthur2': 42}
        )
        assert caches['v2'].get_many(['ford2', 'arthur2'], version=1) == {}
        assert (
            caches['v2'].get_many(['ford2', 'arthur2'], version=2) ==
            {'ford2': 37, 'arthur2': 42}
        )

        # v2 set, using default version = 2
        caches['v2'].set_many({'ford3': 37, 'arthur3': 42})
        assert cache.get_many(['ford3', 'arthur3']) == {}
        assert cache.get_many(['ford3', 'arthur3'], version=1) == {}
        assert (
            cache.get_many(['ford3', 'arthur3'], version=2) ==
            {'ford3': 37, 'arthur3': 42}
        )

        assert (
            caches['v2'].get_many(['ford3', 'arthur3']) ==
            {'ford3': 37, 'arthur3': 42}
        )
        assert (
            caches['v2'].get_many(['ford3', 'arthur3'], version=1) ==
            {}
        )
        assert (
            caches['v2'].get_many(['ford3', 'arthur3'], version=2) ==
            {'ford3': 37, 'arthur3': 42}
        )

        # v2 set, default version = 2, but manually override version = 1
        caches['v2'].set_many({'ford4': 37, 'arthur4': 42}, version=1)
        assert (
            cache.get_many(['ford4', 'arthur4']) ==
            {'ford4': 37, 'arthur4': 42}
        )
        assert (
            cache.get_many(['ford4', 'arthur4'], version=1) ==
            {'ford4': 37, 'arthur4': 42}
        )
        assert cache.get_many(['ford4', 'arthur4'], version=2) == {}

        assert caches['v2'].get_many(['ford4', 'arthur4']) == {}
        assert (
            caches['v2'].get_many(['ford4', 'arthur4'], version=1) ==
            {'ford4': 37, 'arthur4': 42}
        )
        assert caches['v2'].get_many(['ford4', 'arthur4'], version=2) == {}

    def test_incr_version(self):
        cache.set('answer', 42, version=2)
        assert cache.get('answer') is None
        assert cache.get('answer', version=1) is None
        assert cache.get('answer', version=2) == 42
        assert cache.get('answer', version=3) is None

        assert cache.incr_version('answer', version=2) == 3
        assert cache.get('answer') is None
        assert cache.get('answer', version=1) is None
        assert cache.get('answer', version=2) is None
        assert cache.get('answer', version=3) == 42

        caches['v2'].set('answer2', 42)
        assert caches['v2'].get('answer2') == 42
        assert caches['v2'].get('answer2', version=1) is None
        assert caches['v2'].get('answer2', version=2) == 42
        assert caches['v2'].get('answer2', version=3) is None

        assert caches['v2'].incr_version('answer2') == 3
        assert caches['v2'].get('answer2') is None
        assert caches['v2'].get('answer2', version=1) is None
        assert caches['v2'].get('answer2', version=2) is None
        assert caches['v2'].get('answer2', version=3) == 42

        with pytest.raises(ValueError):
            cache.incr_version('does_not_exist')

    def test_decr_version(self):
        cache.set('answer', 42, version=2)
        assert cache.get('answer') is None
        assert cache.get('answer', version=1) is None
        assert cache.get('answer', version=2) == 42

        assert cache.decr_version('answer', version=2) == 1
        assert cache.get('answer') == 42
        assert cache.get('answer', version=1) == 42
        assert cache.get('answer', version=2) is None

        caches['v2'].set('answer2', 42)
        assert caches['v2'].get('answer2') == 42
        assert caches['v2'].get('answer2', version=1) is None
        assert caches['v2'].get('answer2', version=2) == 42

        assert caches['v2'].decr_version('answer2') == 1
        assert caches['v2'].get('answer2') is None
        assert caches['v2'].get('answer2', version=1) == 42
        assert caches['v2'].get('answer2', version=2) is None

        with pytest.raises(ValueError):
            cache.decr_version('does_not_exist', version=2)

    def test_custom_key_func(self):
        # Two caches with different key functions aren't visible to each other
        cache.set('answer1', 42)
        assert cache.get('answer1') == 42
        assert caches['custom_key'].get('answer1') is None
        assert caches['custom_key2'].get('answer1') is None

        caches['custom_key'].set('answer2', 42)
        assert cache.get('answer2') is None
        assert caches['custom_key'].get('answer2') == 42
        assert caches['custom_key2'].get('answer2') == 42

    def test_cache_write_unpickable_object(self):
        update_middleware = UpdateCacheMiddleware()
        update_middleware.cache = cache

        fetch_middleware = FetchFromCacheMiddleware()
        fetch_middleware.cache = cache

        factory = RequestFactory()
        request = factory.get('/cache/test')
        request._cache_update_cache = True
        get_cache_data = FetchFromCacheMiddleware().process_request(request)
        assert get_cache_data is None

        response = HttpResponse()
        content = 'Testing cookie serialization.'
        response.content = content
        response.set_cookie('foo', 'bar')

        update_middleware.process_response(request, response)

        get_cache_data = fetch_middleware.process_request(request)
        assert get_cache_data is not None
        assert get_cache_data.content == content.encode('utf-8')
        assert get_cache_data.cookies == response.cookies

        update_middleware.process_response(request, get_cache_data)
        get_cache_data = fetch_middleware.process_request(request)
        assert get_cache_data is not None
        assert get_cache_data.content == content.encode('utf-8')
        assert get_cache_data.cookies == response.cookies

    def test_add_fail_on_pickleerror(self):
        "See https://code.djangoproject.com/ticket/21200"
        with pytest.raises(pickle.PickleError):
            cache.add('unpickable', Unpickable())

    def test_set_fail_on_pickleerror(self):
        "See https://code.djangoproject.com/ticket/21200"
        with pytest.raises(pickle.PickleError):
            cache.set('unpickable', Unpickable())

    @skipUnless(django.VERSION[:2] >= (1, 9),
                "Requires Django 1.9+ for cache.get_or_set")
    def test_get_or_set(self):
        assert cache.get('projector') is None
        assert cache.get_or_set('projector', 42) == 42
        assert cache.get('projector') == 42

    @skipUnless(django.VERSION[:2] >= (1, 9),
                "Requires Django 1.9+ for cache.get_or_set")
    def test_get_or_set_callable(self):
        def my_callable():
            return 'value'

        assert cache.get_or_set('mykey', my_callable) == 'value'

    @skipUnless(django.VERSION[:2] >= (1, 9),
                "Requires Django 1.9+ for cache.get_or_set")
    def test_get_or_set_version(self):
        msg = "get_or_set() missing 1 required positional argument: 'default'"
        cache.get_or_set('brian', 1979, version=2)

        if django.VERSION[:2] >= (1, 11):
            exc_class = TypeError
        else:
            exc_class = ValueError

        with pytest.raises(exc_class, message=msg):
            cache.get_or_set('brian')

        with pytest.raises(exc_class, message=msg):
            cache.get_or_set('brian', version=1)

        assert cache.get('brian', version=1) is None
        assert cache.get_or_set('brian', 42, version=1) == 42
        assert cache.get_or_set('brian', 1979, version=2) == 1979
        assert cache.get('brian', version=3) is None

    # Modified Django tests

    def test_expiration(self):
        # Cache values can be set to expire
        cache.set('expire1', 'very quickly', 0.1)
        cache.set('expire2', 'very quickly', 0.1)
        cache.set('expire3', 'very quickly', 0.1)

        time.sleep(0.2)
        assert cache.get("expire1") is None

        cache.add("expire2", "newvalue")
        assert cache.get("expire2") == "newvalue"
        assert not cache.has_key("expire3")  # noqa

    def test_get_many(self):
        # Multiple cache keys can be returned using get_many
        cache.set('a', 'a')
        cache.set('b', 'b')
        cache.set('c', 'c')
        cache.set('d', 'd')

        with self.assertNumQueries(1):
            value = cache.get_many(['a', 'c', 'd'])
        assert value == {'a': 'a', 'c': 'c', 'd': 'd'}

        with self.assertNumQueries(1):
            value = cache.get_many(['a', 'b', 'e'])

        assert value == {'a': 'a', 'b': 'b'}

    def test_get_many_with_one_expired(self):
        # Multiple cache keys can be returned using get_many
        the_cache = caches['no_cull']
        the_cache.set('a', 'a', 0.1)
        time.sleep(0.2)

        the_cache.set('b', 'b')
        the_cache.set('c', 'c')
        the_cache.set('d', 'd')

        with self.assertNumQueries(1):
            value = the_cache.get_many(['a', 'c', 'd'])
        assert value == {'c': 'c', 'd': 'd'}

        with self.assertNumQueries(1):
            value = the_cache.get_many(['a', 'b', 'e'])

        assert value == {'b': 'b'}

    def test_set_many(self):
        # Single keys can be set using set_many
        # Perform a single query first to avoid spurious on-connect queries
        caches['no_cull'].get('nonexistent')

        with self.assertNumQueries(1):
            result = caches['no_cull'].set_many({"key1": "spam"})
        assert result == []

        # Multiple keys can be set using set_many
        with self.assertNumQueries(1):
            result = caches['no_cull'].set_many({
                'key1': 'spam',
                'key2': 'eggs',
            })
        assert result == []
        assert cache.get("key1") == "spam"
        assert cache.get("key2") == "eggs"

    def test_set_many_expiration(self):
        # set_many takes a second ``timeout`` parameter
        # Perform a single query first to avoid spurious on-connect queries
        caches['no_cull'].get('nonexistent')
        with self.assertNumQueries(1):
            caches['no_cull'].set_many({"key1": "spam", "key2": "eggs"}, 0.1)
        cache.set("key3", "ham")
        time.sleep(0.2)

        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") == "ham"

        # set_many expired values can be replaced
        with self.assertNumQueries(1):
            caches['no_cull'].set_many(
                {"key1": "spam", "key2": "egg", "key3": "spam", "key4": "ham"},
                1,
            )
        v = cache.get("key1")
        assert v == "spam"
        assert cache.get("key2") == "egg"
        assert cache.get("key3") == "spam"
        assert cache.get("key4") == "ham"

    def test_delete_many(self):
        # Multiple keys can be deleted using delete_many
        cache.set("key1", "spam")
        cache.set("key2", "eggs")
        cache.set("key3", "ham")
        with self.assertNumQueries(1):
            cache.delete_many(["key1", "key2"])
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") == "ham"

    def test_invalid_keys(self):
        # mimic custom ``make_key`` method being defined since the default will
        # never show the below warnings
        def func(key, *args):
            return key

        old_func = cache.key_func
        cache.key_func = func

        try:
            with pytest.warns(CacheKeyWarning):
                # memcached does not allow whitespace or control characters in
                # keys
                cache.set('space key', 'value')

            with pytest.raises(ValueError):
                # memcached limits key length to 250
                # We have a 250 character max length on our table
                cache.set('a' * 251, 'value')
        finally:
            cache.key_func = old_func

    # Original tests

    def test_base_set_bad_value(self):
        with pytest.raises(ValueError) as excinfo:
            cache._base_set('foo', 'key', 'value')
        assert "'mode' should be" in str(excinfo.value)

    def test_add_with_expired(self):
        cache.add("mykey", "value", 0.3)
        assert cache.get("mykey") == "value"

        result = cache.add("mykey", "newvalue", 0.3)
        assert not result
        assert cache.get("mykey") == "value"

        time.sleep(0.4)

        result = cache.add("mykey", "newvalue", 60)
        assert result
        assert cache.get("mykey") == "newvalue"

    @override_cache_settings(options={'COMPRESS_MIN_LENGTH': 10})
    def test_compressed(self):
        cache.set("key", "a" * 11)
        assert cache.get("key") == "a" * 11

    @override_cache_settings(options={'COMPRESS_MIN_LENGTH': 10,
                                      'COMPRESS_LEVEL': 9})
    def test_compress_level(self):
        cache.set("key", "a" * 11)
        assert cache.get("key") == "a" * 11

        # Check a bad compression level = zlib error
        with override_cache_settings(options={'COMPRESS_MIN_LENGTH': 10,
                                              'COMPRESS_LEVEL': 123}):
            with pytest.raises(Exception) as excinfo:
                cache.set("key", "a" * 11)
            assert "Bad compression level" in str(excinfo.value)

    @override_cache_settings(options={'COMPRESS_MIN_LENGTH': 10})
    def test_changing_compressed_option_leaves_compressed_data_readable(self):
        a11 = "a" * 11
        cache.set("key", a11)

        # Turn it off - remains readable and settable
        with override_cache_settings(options={'COMPRESS_MIN_LENGTH': 0}):
            assert cache.get("key") == a11
            cache.set("key", a11)
            assert cache.get("key") == a11

        # Back on, still readable
        assert cache.get("key") == a11
        cache.set("key", a11)
        assert cache.get("key") == a11

    def test_our_options_quacks_like_djangos(self):
        from django.core.cache.backends.db import Options
        from django_mysql.cache import Options as OurOptions
        theirs = Options('something')
        ours = OurOptions('something')
        assert set(ours.__dict__.keys()) == set(theirs.__dict__.keys())

    def test_cull(self):
        self._perform_cull_test(caches['cull'], 50, 30)

    def test_zero_cull(self):
        self._perform_cull_test(caches['zero_cull'], 50, 20)

    def test_no_cull_only_deletes_when_told(self):
        self._perform_cull_test(caches['no_cull'], 50, 50)
        caches['no_cull'].cull()
        assert self.table_count() == 25

    def test_cull_deletes_expired_first(self):
        cull_cache = caches['cull']
        cull_cache.set("key", "value", 0.3)
        time.sleep(0.4)

        # Add 30 more entries. The expired key should get deleted, leaving the
        # 30 new keys
        self._perform_cull_test(cull_cache, 30, 30)
        assert cull_cache.get('key') is None

    def _perform_cull_test(self, cull_cache, initial_count, final_count):
        # Create initial cache key entries. This will overflow the cache,
        # causing a cull.
        for i in range(1, initial_count + 1):
            cull_cache.set('cull%d' % i, 'value', 1000)
        count = 0
        # Count how many keys are left in the cache.
        for i in range(1, initial_count + 1):
            if cull_cache.has_key('cull%d' % i):  # noqa
                count = count + 1
        assert count == final_count

    def test_incr_range(self):
        cache.set('overwhelm', BIGINT_SIGNED_MAX - 1)
        cache.incr('overwhelm')
        if django.VERSION >= (2, 0):
            expected = IntegrityError
        else:
            expected = OperationalError
        with pytest.raises(expected):
            cache.incr('overwhelm')

    def test_decr_range(self):
        cache.set('underwhelm', BIGINT_SIGNED_MIN + 1)
        cache.decr('underwhelm')
        if django.VERSION >= (2, 0):
            # IntegrityError on MySQL 5.7+ and MariaDB,
            # OperationalError on MySQL 5.6...
            expected = (IntegrityError, OperationalError)
        else:
            expected = OperationalError
        with pytest.raises(expected):
            cache.decr('underwhelm')

    def test_cant_incr_decimals(self):
        # Cached values that aren't ints can't be incremented
        cache.set('answer', Decimal('1.1'))
        with pytest.raises(ValueError):
            cache.incr('answer')

    def test_cant_decr_decimals(self):
        # Cached values that aren't ints can't be decremented
        cache.set('answer', Decimal('9.9'))
        with pytest.raises(ValueError):
            cache.decr('answer')

    def test_set_int_subclass(self):
        # Storing an int subclass should return that int subclass
        cache.set('myint', MyInt(2))
        val = cache.get('myint')
        assert val.times2() == 4

        # Can't increment it since it's a pickle object on the table, not an
        # integer
        with pytest.raises(ValueError):
            cache.incr('myint')

    def test_unknown_value_type_errors(self):
        # Unknown value_type values should be errors, since we don't know how
        # to deserialize them. New value_types will probably be introduced by
        # later versions or subclasses of MySQLCache

        cache.set('mykey', 123)
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE `%s` SET value_type = '?'" % self.table_name,
            )

        with pytest.raises(ValueError):
            cache.get('mykey')

    def test_key_case_sensitivity(self):
        """
        Check that we can store both upper and lowercase keys separately

        At first MySQLCache did not use a binary collation for cache_key, which
        meant it was not case sensitive.
        """
        cache.set('akey', 123)
        cache.set('Akey', 456)
        assert cache.get('akey') == 123
        assert cache.get('Akey') == 456

    def test_value_type_case_sensitivity(self):
        cache.set('akey', 123)
        with connection.cursor() as cursor:
            # Check that value_type is 'i' for integer
            cursor.execute("SELECT value_type FROM `%s`" % self.table_name)
            t = cursor.fetchone()[0]
            assert t == 'i'

            # Should be case-sensitive, so i != I
            cursor.execute(
                """SELECT COUNT(*) FROM `%s`
                   WHERE value_type = 'I'""" % self.table_name)
            n = cursor.fetchone()[0]
            assert n == 0

    def test_bad_key_prefix_for_reverse_function(self):
        override = override_cache_settings(KEY_PREFIX='a:bad:prefix')
        with override, pytest.raises(ValueError) as excinfo:
            caches['default']
        assert str(excinfo.value).startswith(
            "Cannot use the default KEY_FUNCTION")

    @parameterized.expand(['default', 'prefix', 'custom_key', 'custom_key2'])
    def test_keys_with_prefix(self, cache_name):
        cache = caches[cache_name]
        assert cache.keys_with_prefix('') == set()
        assert cache.keys_with_prefix('K') == set()

        cache.set('A2', True)
        cache.set('K1', True)
        cache.set('K23', True, 1000)
        cache.set('K99', True, 0.1)
        time.sleep(0.2)
        assert cache.keys_with_prefix('') == {'A2', 'K1', 'K23'}
        assert cache.keys_with_prefix('K') == {'K1', 'K23'}

        cache.delete('K1')
        assert cache.keys_with_prefix('K') == {'K23'}

        cache.clear()
        assert cache.keys_with_prefix('') == set()
        assert cache.keys_with_prefix('K') == set()

    @parameterized.expand(['default', 'prefix', 'custom_key', 'custom_key2'])
    def test_keys_with_prefix_version(self, cache_name):
        cache = caches[cache_name]

        cache.set('V12', True, version=1)
        cache.set('V12', True, version=2)
        cache.set('V2', True, version=2)
        cache.set('V3', True, version=3)
        assert cache.keys_with_prefix('V', version=1) == {'V12'}
        assert cache.keys_with_prefix('V', version=2) == {'V12', 'V2'}
        assert cache.keys_with_prefix('V', version=3) == {'V3'}

    @override_cache_settings(KEY_FUNCTION=custom_key_func)
    def test_keys_with_prefix_with_bad_cache(self):
        with pytest.raises(ValueError) as excinfo:
            cache.keys_with_prefix('')
        assert str(excinfo.value).startswith(
            "To use the _with_prefix commands")

    @parameterized.expand(['default', 'prefix', 'custom_key', 'custom_key2'])
    def test_get_with_prefix(self, cache_name):
        cache = caches[cache_name]
        assert cache.get_with_prefix('') == {}
        assert cache.get_with_prefix('K') == {}

        cache.set('A2', [True])
        cache.set('K1', "Value1")
        cache.set('K23', 2, 1000)
        cache.set('K99', ["Value", 99], 0.1)
        time.sleep(0.2)
        assert (
            cache.get_with_prefix('') ==
            {'A2': [True], 'K1': "Value1", 'K23': 2}
        )
        assert (
            cache.get_with_prefix('K') ==
            {'K1': "Value1", 'K23': 2}
        )

        cache.delete('K1')
        assert cache.get_with_prefix('K') == {'K23': 2}

        cache.clear()
        assert cache.get_with_prefix('') == {}
        assert cache.get_with_prefix('K') == {}

    @parameterized.expand(['default', 'prefix', 'custom_key', 'custom_key2'])
    def test_get_with_prefix_version(self, cache_name):
        cache = caches[cache_name]

        cache.set('V12', ('version1',), version=1)
        cache.set('V12', "str", version=2)
        cache.set('V2', 2, version=2)
        cache.set('V3', object, version=3)
        assert cache.get_with_prefix('V', version=1) == {'V12': ('version1',)}
        assert cache.get_with_prefix('V', version=2) == {'V12': "str", 'V2': 2}
        assert cache.get_with_prefix('V', version=3) == {'V3': object}

    @override_cache_settings(KEY_FUNCTION=custom_key_func)
    def test_get_with_prefix_with_bad_cache(self):
        with pytest.raises(ValueError) as excinfo:
            cache.get_with_prefix('')
        assert str(excinfo.value).startswith(
            "To use the _with_prefix commands")

    @parameterized.expand(['default', 'prefix', 'custom_key', 'custom_key2'])
    def test_delete_with_prefix(self, cache_name):
        cache = caches[cache_name]

        # Check it runs on an empty cache
        assert cache.delete_with_prefix('') == 0
        assert cache.delete_with_prefix('K') == 0

        cache.set('A1', True)
        cache.set('A2', True)
        cache.set('K2', True)
        cache.set('K44', True)

        assert cache.keys_with_prefix('') == {'A1', 'A2', 'K2', 'K44'}
        assert cache.delete_with_prefix('A') == 2
        assert cache.keys_with_prefix('') == {'K2', 'K44'}
        assert cache.delete_with_prefix('A') == 0
        assert cache.keys_with_prefix('') == {'K2', 'K44'}
        assert cache.delete_with_prefix('K') == 2
        assert cache.keys_with_prefix('K') == set()
        assert cache.keys_with_prefix('') == set()

    @parameterized.expand(['default', 'prefix', 'custom_key', 'custom_key2'])
    def test_delete_with_prefix_version(self, cache_name):
        cache = caches[cache_name]

        cache.set('V12', True, version=1)
        cache.set('V12', True, version=2)
        cache.set('V2', True, version=2)
        cache.set('V3', True, version=3)

        has_key = cache.has_key  # avoid lint error

        assert cache.delete_with_prefix('V', version=1) == 1
        assert not has_key('V12', version=1)
        assert has_key('V12', version=2)
        assert has_key('V2', version=2)
        assert has_key('V3', version=3)

        assert cache.delete_with_prefix('V', version=2) == 2
        assert not has_key('V12', version=1)
        assert not has_key('V12', version=2)
        assert not has_key('V2', version=2)
        assert has_key('V3', version=3)

        assert cache.delete_with_prefix('V', version=3) == 1
        assert not has_key('V12', version=1)
        assert not has_key('V12', version=2)
        assert not has_key('V2', version=2)
        assert not has_key('V3', version=3)

    @override_cache_settings(KEY_FUNCTION=custom_key_func)
    def test_delete_with_prefix_with_no_reverse_works(self):
        cache.set_many({'K1': 'value', 'K2': 'value2', 'B2': 'Anothervalue'})
        assert cache.delete_with_prefix('K') == 2
        assert cache.get_many(['K1', 'K2', 'B2']) == {'B2': 'Anothervalue'}

    def test_mysql_cache_migration_alias(self):
        out = StringIO()
        call_command('mysql_cache_migration', 'default', stdout=out)
        output = out.getvalue()

        num_run_sqls = (len(output.split('RunSQL')) - 1)
        assert num_run_sqls == 1

    def test_mysql_cache_migration_non_existent(self):
        out = StringIO()
        with pytest.raises(CommandError):
            call_command('mysql_cache_migration', 'nonexistent', stdout=out)

    @override_cache_settings(
        BACKEND='django.core.cache.backends.dummy.DummyCache',
    )
    def test_mysql_cache_migration_no_mysql_caches(self):
        err = StringIO()
        call_command('mysql_cache_migration', stderr=err)
        assert "No MySQLCache instances in CACHES" in err.getvalue()

    # cull_mysql_caches tests

    @override_cache_settings(options={'MAX_ENTRIES': -1})
    def test_cull_max_entries_minus_one(self):
        # cull with MAX_ENTRIES = -1 should never clear anything that is not
        # expired

        # one expired key
        cache.set('key', 'value', 0.1)
        time.sleep(0.2)

        # 90 non-expired keys
        for n in six.moves.range(9):
            cache.set_many({
                str(n * 10 + i): True
                for i in six.moves.range(10)
            })

        cache.cull()
        assert self.table_count() == 90

    def test_cull_mysql_caches_basic(self):
        cache.set('key', 'value', 0.1)
        time.sleep(0.2)
        assert self.table_count() == 1
        call_command('cull_mysql_caches', verbosity=0)
        assert self.table_count() == 0

    def test_cull_mysql_caches_named_cache(self):
        cache.set('key', 'value', 0.1)
        time.sleep(0.2)
        assert self.table_count() == 1

        out = StringIO()
        call_command('cull_mysql_caches', 'default', verbosity=1, stdout=out)
        output = out.getvalue()
        assert (
            output.strip() ==
            "Deleting from cache 'default'... 1 entries deleted."
        )
        assert self.table_count() == 0

    def test_cull_mysql_caches_bad_cache_name(self):
        with pytest.raises(CommandError) as excinfo:
            call_command('cull_mysql_caches', "NOTACACHE", verbosity=0)
        assert "Cache 'NOTACACHE' does not exist" == str(excinfo.value)


@override_cache_settings()
class MySQLCacheMigrationTests(MySQLCacheTableMixin, TransactionTestCase):

    @pytest.fixture(autouse=True)
    def flake8dir(self, flake8dir):
        self.flake8dir = flake8dir

    def test_mysql_cache_migration(self):
        out = StringIO()
        call_command('mysql_cache_migration', stdout=out)
        output = out.getvalue()

        # Lint it
        self.flake8dir.make_example_py(output)
        result = self.flake8dir.run_flake8()
        assert result.out_lines == []

        # Dynamic import and check
        migration_mod = imp.new_module('0001_add_cache_tables')
        six.exec_(output, migration_mod.__dict__)
        assert hasattr(migration_mod, 'Migration')
        migration = migration_mod.Migration
        assert hasattr(migration, 'dependencies')
        assert hasattr(migration, 'operations')

        # Since they all have the same table name, there should only be one
        # operation
        assert len(migration.operations) == 1

        # Now run the migration forwards and backwards to check it works
        operation = migration.operations[0]
        assert not self.table_exists(self.table_name)

        state = ProjectState()
        new_state = state.clone()
        with connection.schema_editor() as editor:
            operation.database_forwards("testapp", editor,
                                        state, new_state)
        assert self.table_exists(self.table_name)

        new_state = state.clone()
        with connection.schema_editor() as editor:
            operation.database_backwards("testapp", editor,
                                         new_state, state)
        assert not self.table_exists(self.table_name)

    def table_exists(self, table_name):
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
                   WHERE TABLE_SCHEMA = DATABASE() AND
                         TABLE_NAME = %s""",
                (table_name,),
            )
            return bool(cursor.fetchone()[0])
