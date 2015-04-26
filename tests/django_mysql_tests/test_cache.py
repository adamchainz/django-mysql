# -*- coding:utf-8 -*-
from __future__ import unicode_literals

import os
import time
import warnings
from decimal import Decimal

from flake8.run import check_code

from django.core.cache import cache, caches, CacheKeyWarning
from django.core.management import call_command, CommandError
from django.db import connection, transaction, OperationalError
from django.http import HttpResponse
from django.middleware.cache import (
    FetchFromCacheMiddleware, UpdateCacheMiddleware
)
from django.test import RequestFactory, TransactionTestCase
from django.test.utils import override_settings
from django.utils.six.moves import StringIO

from django_mysql.cache import BIGINT_SIGNED_MIN, BIGINT_SIGNED_MAX, MySQLCache
from django_mysql_tests.models import expensive_calculation, Poll
from django_mysql_tests.utils import captured_stdout

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


_caches_setting_base = {
    'default': {},
    'prefix': {'KEY_PREFIX': 'cacheprefix{}'.format(os.getpid())},
    'v2': {'VERSION': 2},
    'custom_key': {'KEY_FUNCTION': custom_key_func},
    'custom_key2': {
        'KEY_FUNCTION': 'django_mysql_tests.test_cache.custom_key_func'
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
    setting = dict((k, {}) for k in _caches_setting_base.keys())
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
        )
    )


@override_cache_settings()
class MySQLCacheTests(TransactionTestCase):

    def setUp(self):
        # The super calls needs to happen first for the settings override.
        super(MySQLCacheTests, self).setUp()
        self.table_name = 'test cache table'
        self.create_table()
        self.factory = RequestFactory()

    def tearDown(self):
        # The super call needs to happen first because it uses the database.
        super(MySQLCacheTests, self).tearDown()
        self.drop_table()

    def create_table(self):
        sql = MySQLCache.create_table_sql.format(table_name=self.table_name)
        with connection.cursor() as cursor:
            cursor.execute(sql)

    def drop_table(self):
        with connection.cursor() as cursor:
            cursor.execute('DROP TABLE `%s`' % self.table_name)

    def table_count(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM `%s`" % self.table_name)
            return cursor.fetchone()[0]

    # These tests were copied from django's tests/cache/tests.py file

    def test_simple(self):
        # Simple cache set/get works
        cache.set("key", "value")
        self.assertEqual(cache.get("key"), "value")

    def test_add(self):
        # A key can be added to a cache
        result = cache.add("addkey1", "value")
        self.assertEqual(result, True)
        result = cache.add("addkey1", "newvalue")
        self.assertEqual(result, False)
        self.assertEqual(cache.get("addkey1"), "value")

    def test_prefix(self):
        # Test for same cache key conflicts between shared backend
        cache.set('somekey', 'value')

        # should not be set in the prefixed cache
        self.assertFalse(caches['prefix'].has_key('somekey'))  # noqa

        caches['prefix'].set('somekey', 'value2')

        self.assertEqual(cache.get('somekey'), 'value')
        self.assertEqual(caches['prefix'].get('somekey'), 'value2')

    def test_non_existent(self):
        # Non-existent cache keys return as None/default
        # get with non-existent keys
        self.assertIsNone(cache.get("does_not_exist"))
        self.assertEqual(cache.get("does_not_exist", "bang!"), "bang!")

    def test_delete(self):
        # Cache keys can be deleted
        cache.set("key1", "spam")
        cache.set("key2", "eggs")
        self.assertEqual(cache.get("key1"), "spam")
        cache.delete("key1")
        self.assertIsNone(cache.get("key1"))
        self.assertEqual(cache.get("key2"), "eggs")

    def test_has_key(self):
        # The cache can be inspected for cache keys
        cache.set("hello1", "goodbye1")
        self.assertTrue(cache.has_key("hello1"))  # noqa
        self.assertFalse(cache.has_key("goodbye1"))  # noqa
        cache.set("no_expiry", "here", None)
        self.assertTrue(cache.has_key("no_expiry"))  # noqa

    def test_in(self):
        # The in operator can be used to inspect cache contents
        cache.set("hello2", "goodbye2")
        self.assertIn("hello2", cache)
        self.assertNotIn("goodbye2", cache)

    def test_incr(self):
        # Cache values can be incremented
        cache.set('answer', 41)
        self.assertEqual(cache.incr('answer'), 42)
        self.assertEqual(cache.get('answer'), 42)
        self.assertEqual(cache.incr('answer', 10), 52)
        self.assertEqual(cache.get('answer'), 52)
        self.assertEqual(cache.incr('answer', -10), 42)
        self.assertRaises(ValueError, cache.incr, 'does_not_exist')

    def test_decr(self):
        # Cache values can be decremented
        cache.set('answer', 43)
        self.assertEqual(cache.decr('answer'), 42)
        self.assertEqual(cache.get('answer'), 42)
        self.assertEqual(cache.decr('answer', 10), 32)
        self.assertEqual(cache.get('answer'), 32)
        self.assertEqual(cache.decr('answer', -10), 42)
        self.assertRaises(ValueError, cache.decr, 'does_not_exist')

    def test_close(self):
        self.assertTrue(hasattr(cache, 'close'))
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
        self.assertEqual(cache.get("stuff"), stuff)

    def test_cache_read_for_model_instance(self):
        # Don't want fields with callable as default to be called on cache read
        expensive_calculation.num_runs = 0
        Poll.objects.all().delete()
        my_poll = Poll.objects.create(question="Well?")
        self.assertEqual(Poll.objects.count(), 1)
        pub_date = my_poll.pub_date
        cache.set('question', my_poll)
        cached_poll = cache.get('question')
        self.assertEqual(cached_poll.pub_date, pub_date)
        # We only want the default expensive calculation run once
        self.assertEqual(expensive_calculation.num_runs, 1)

    def test_cache_write_for_model_instance_with_deferred(self):
        # Don't want fields with callable as default to be called on cache
        # write
        expensive_calculation.num_runs = 0
        Poll.objects.all().delete()
        Poll.objects.create(question="What?")
        self.assertEqual(expensive_calculation.num_runs, 1)
        defer_qs = Poll.objects.all().defer('question')
        self.assertEqual(defer_qs.count(), 1)
        self.assertEqual(expensive_calculation.num_runs, 1)
        cache.set('deferred_queryset', defer_qs)
        # cache set should not re-evaluate default functions
        self.assertEqual(expensive_calculation.num_runs, 1)

    def test_cache_read_for_model_instance_with_deferred(self):
        # Don't want fields with callable as default to be called on cache read
        expensive_calculation.num_runs = 0
        Poll.objects.all().delete()
        Poll.objects.create(question="What?")
        self.assertEqual(expensive_calculation.num_runs, 1)
        defer_qs = Poll.objects.all().defer('question')
        self.assertEqual(defer_qs.count(), 1)
        cache.set('deferred_queryset', defer_qs)
        self.assertEqual(expensive_calculation.num_runs, 1)
        runs_before_cache_read = expensive_calculation.num_runs
        cache.get('deferred_queryset')
        # We only want the default expensive calculation run on creation and
        # set
        self.assertEqual(expensive_calculation.num_runs,
                         runs_before_cache_read)

    def test_unicode(self):
        # Unicode values can be cached
        stuff = {
            'ascii': 'ascii_value',
            'unicode_ascii': 'Iñtërnâtiônàlizætiøn1',
            'Iñtërnâtiônàlizætiøn': 'Iñtërnâtiônàlizætiøn2',
            'ascii2': {'x': 1}
        }
        # Test `set`
        for (key, value) in stuff.items():
            cache.set(key, value)
            self.assertEqual(cache.get(key), value)

        # Test `add`
        for (key, value) in stuff.items():
            cache.delete(key)
            cache.add(key, value)
            self.assertEqual(cache.get(key), value)

        # Test `set_many`
        for (key, value) in stuff.items():
            cache.delete(key)
        cache.set_many(stuff)
        for (key, value) in stuff.items():
            self.assertEqual(cache.get(key), value)

    def test_binary_string(self):
        # Binary strings should be cacheable
        from zlib import compress, decompress
        value = 'value_to_be_compressed'
        compressed_value = compress(value.encode())

        # Test set
        cache.set('binary1', compressed_value)
        compressed_result = cache.get('binary1')
        self.assertEqual(compressed_value, compressed_result)
        self.assertEqual(value, decompress(compressed_result).decode())

        # Test add
        cache.add('binary1-add', compressed_value)
        compressed_result = cache.get('binary1-add')
        self.assertEqual(compressed_value, compressed_result)
        self.assertEqual(value, decompress(compressed_result).decode())

        # Test set_many
        cache.set_many({'binary1-set_many': compressed_value})
        compressed_result = cache.get('binary1-set_many')
        self.assertEqual(compressed_value, compressed_result)
        self.assertEqual(value, decompress(compressed_result).decode())

    def test_clear(self):
        # The cache can be emptied using clear
        cache.set("key1", "spam")
        cache.set("key2", "eggs")
        cache.clear()
        self.assertIsNone(cache.get("key1"))
        self.assertIsNone(cache.get("key2"))

    def test_long_timeout(self):
        '''
        Using a timeout greater than 30 days makes memcached think
        it is an absolute expiration timestamp instead of a relative
        offset. Test that we honour this convention. Refs #12399.
        '''
        cache.set('key1', 'eggs', 60 * 60 * 24 * 30 + 1)  # 30 days + 1 second
        self.assertEqual(cache.get('key1'), 'eggs')

        cache.add('key2', 'ham', 60 * 60 * 24 * 30 + 1)
        self.assertEqual(cache.get('key2'), 'ham')

        cache.set_many(
            {'key3': 'sausage', 'key4': 'lobster bisque'},
            60 * 60 * 24 * 30 + 1
        )
        self.assertEqual(cache.get('key3'), 'sausage')
        self.assertEqual(cache.get('key4'), 'lobster bisque')

    def test_forever_timeout(self):
        '''
        Passing in None into timeout results in a value that is cached forever
        '''
        cache.set('key1', 'eggs', None)
        self.assertEqual(cache.get('key1'), 'eggs')

        cache.add('key2', 'ham', None)
        self.assertEqual(cache.get('key2'), 'ham')
        added = cache.add('key1', 'new eggs', None)
        self.assertEqual(added, False)
        self.assertEqual(cache.get('key1'), 'eggs')

        cache.set_many({'key3': 'sausage', 'key4': 'lobster bisque'}, None)
        self.assertEqual(cache.get('key3'), 'sausage')
        self.assertEqual(cache.get('key4'), 'lobster bisque')

    def test_zero_timeout(self):
        '''
        Passing in zero into timeout results in a value that is not cached
        '''
        cache.set('key1', 'eggs', 0)
        self.assertIsNone(cache.get('key1'))

        cache.add('key2', 'ham', 0)
        self.assertIsNone(cache.get('key2'))

        cache.set_many({'key3': 'sausage', 'key4': 'lobster bisque'}, 0)
        self.assertIsNone(cache.get('key3'))
        self.assertIsNone(cache.get('key4'))

    def test_float_timeout(self):
        # Make sure a timeout given as a float doesn't crash anything.
        cache.set("key1", "spam", 100.2)
        self.assertEqual(cache.get("key1"), "spam")

    def test_cache_versioning_get_set(self):
        # set, using default version = 1
        cache.set('answer1', 42)
        self.assertEqual(cache.get('answer1'), 42)
        self.assertEqual(cache.get('answer1', version=1), 42)
        self.assertIsNone(cache.get('answer1', version=2))

        self.assertIsNone(caches['v2'].get('answer1'))
        self.assertEqual(caches['v2'].get('answer1', version=1), 42)
        self.assertIsNone(caches['v2'].get('answer1', version=2))

        # set, default version = 1, but manually override version = 2
        cache.set('answer2', 42, version=2)
        self.assertIsNone(cache.get('answer2'))
        self.assertIsNone(cache.get('answer2', version=1))
        self.assertEqual(cache.get('answer2', version=2), 42)

        self.assertEqual(caches['v2'].get('answer2'), 42)
        self.assertIsNone(caches['v2'].get('answer2', version=1))
        self.assertEqual(caches['v2'].get('answer2', version=2), 42)

        # v2 set, using default version = 2
        caches['v2'].set('answer3', 42)
        self.assertIsNone(cache.get('answer3'))
        self.assertIsNone(cache.get('answer3', version=1))
        self.assertEqual(cache.get('answer3', version=2), 42)

        self.assertEqual(caches['v2'].get('answer3'), 42)
        self.assertIsNone(caches['v2'].get('answer3', version=1))
        self.assertEqual(caches['v2'].get('answer3', version=2), 42)

        # v2 set, default version = 2, but manually override version = 1
        caches['v2'].set('answer4', 42, version=1)
        self.assertEqual(cache.get('answer4'), 42)
        self.assertEqual(cache.get('answer4', version=1), 42)
        self.assertIsNone(cache.get('answer4', version=2))

        self.assertIsNone(caches['v2'].get('answer4'))
        self.assertEqual(caches['v2'].get('answer4', version=1), 42)
        self.assertIsNone(caches['v2'].get('answer4', version=2))

    def test_cache_versioning_add(self):

        # add, default version = 1, but manually override version = 2
        cache.add('answer1', 42, version=2)
        self.assertIsNone(cache.get('answer1', version=1))
        self.assertEqual(cache.get('answer1', version=2), 42)

        cache.add('answer1', 37, version=2)
        self.assertIsNone(cache.get('answer1', version=1))
        self.assertEqual(cache.get('answer1', version=2), 42)

        cache.add('answer1', 37, version=1)
        self.assertEqual(cache.get('answer1', version=1), 37)
        self.assertEqual(cache.get('answer1', version=2), 42)

        # v2 add, using default version = 2
        caches['v2'].add('answer2', 42)
        self.assertIsNone(cache.get('answer2', version=1))
        self.assertEqual(cache.get('answer2', version=2), 42)

        caches['v2'].add('answer2', 37)
        self.assertIsNone(cache.get('answer2', version=1))
        self.assertEqual(cache.get('answer2', version=2), 42)

        caches['v2'].add('answer2', 37, version=1)
        self.assertEqual(cache.get('answer2', version=1), 37)
        self.assertEqual(cache.get('answer2', version=2), 42)

        # v2 add, default version = 2, but manually override version = 1
        caches['v2'].add('answer3', 42, version=1)
        self.assertEqual(cache.get('answer3', version=1), 42)
        self.assertIsNone(cache.get('answer3', version=2))

        caches['v2'].add('answer3', 37, version=1)
        self.assertEqual(cache.get('answer3', version=1), 42)
        self.assertIsNone(cache.get('answer3', version=2))

        caches['v2'].add('answer3', 37)
        self.assertEqual(cache.get('answer3', version=1), 42)
        self.assertEqual(cache.get('answer3', version=2), 37)

    def test_cache_versioning_has_key(self):
        cache.set('answer1', 42)

        # has_key
        self.assertTrue(cache.has_key('answer1'))  # noqa
        self.assertTrue(cache.has_key('answer1', version=1))  # noqa
        self.assertFalse(cache.has_key('answer1', version=2))  # noqa

        self.assertFalse(caches['v2'].has_key('answer1'))  # noqa
        self.assertTrue(caches['v2'].has_key('answer1', version=1))  # noqa
        self.assertFalse(caches['v2'].has_key('answer1', version=2))  # noqa

    def test_cache_versioning_delete(self):
        cache.set('answer1', 37, version=1)
        cache.set('answer1', 42, version=2)
        cache.delete('answer1')
        self.assertIsNone(cache.get('answer1', version=1))
        self.assertEqual(cache.get('answer1', version=2), 42)

        cache.set('answer2', 37, version=1)
        cache.set('answer2', 42, version=2)
        cache.delete('answer2', version=2)
        self.assertEqual(cache.get('answer2', version=1), 37)
        self.assertIsNone(cache.get('answer2', version=2))

        cache.set('answer3', 37, version=1)
        cache.set('answer3', 42, version=2)
        caches['v2'].delete('answer3')
        self.assertEqual(cache.get('answer3', version=1), 37)
        self.assertIsNone(cache.get('answer3', version=2))

        cache.set('answer4', 37, version=1)
        cache.set('answer4', 42, version=2)
        caches['v2'].delete('answer4', version=1)
        self.assertIsNone(cache.get('answer4', version=1))
        self.assertEqual(cache.get('answer4', version=2), 42)

    def test_cache_versioning_incr_decr(self):
        cache.set('answer1', 37, version=1)
        cache.set('answer1', 42, version=2)
        cache.incr('answer1')
        self.assertEqual(cache.get('answer1', version=1), 38)
        self.assertEqual(cache.get('answer1', version=2), 42)
        cache.decr('answer1')
        self.assertEqual(cache.get('answer1', version=1), 37)
        self.assertEqual(cache.get('answer1', version=2), 42)

        cache.set('answer2', 37, version=1)
        cache.set('answer2', 42, version=2)
        cache.incr('answer2', version=2)
        self.assertEqual(cache.get('answer2', version=1), 37)
        self.assertEqual(cache.get('answer2', version=2), 43)
        cache.decr('answer2', version=2)
        self.assertEqual(cache.get('answer2', version=1), 37)
        self.assertEqual(cache.get('answer2', version=2), 42)

        cache.set('answer3', 37, version=1)
        cache.set('answer3', 42, version=2)
        caches['v2'].incr('answer3')
        self.assertEqual(cache.get('answer3', version=1), 37)
        self.assertEqual(cache.get('answer3', version=2), 43)
        caches['v2'].decr('answer3')
        self.assertEqual(cache.get('answer3', version=1), 37)
        self.assertEqual(cache.get('answer3', version=2), 42)

        cache.set('answer4', 37, version=1)
        cache.set('answer4', 42, version=2)
        caches['v2'].incr('answer4', version=1)
        self.assertEqual(cache.get('answer4', version=1), 38)
        self.assertEqual(cache.get('answer4', version=2), 42)
        caches['v2'].decr('answer4', version=1)
        self.assertEqual(cache.get('answer4', version=1), 37)
        self.assertEqual(cache.get('answer4', version=2), 42)

    def test_cache_versioning_get_set_many(self):
        # set, using default version = 1
        cache.set_many({'ford1': 37, 'arthur1': 42})
        self.assertDictEqual(
            cache.get_many(['ford1', 'arthur1']),
            {'ford1': 37, 'arthur1': 42}
        )
        self.assertDictEqual(
            cache.get_many(['ford1', 'arthur1'], version=1),
            {'ford1': 37, 'arthur1': 42}
        )
        self.assertDictEqual(
            cache.get_many(['ford1', 'arthur1'], version=2),
            {}
        )

        self.assertDictEqual(caches['v2'].get_many(['ford1', 'arthur1']), {})
        self.assertDictEqual(
            caches['v2'].get_many(['ford1', 'arthur1'], version=1),
            {'ford1': 37, 'arthur1': 42}
        )
        self.assertDictEqual(
            caches['v2'].get_many(['ford1', 'arthur1'], version=2),
            {}
        )

        # set, default version = 1, but manually override version = 2
        cache.set_many({'ford2': 37, 'arthur2': 42}, version=2)
        self.assertDictEqual(cache.get_many(['ford2', 'arthur2']), {})
        self.assertDictEqual(
            cache.get_many(['ford2', 'arthur2'], version=1),
            {}
        )
        self.assertDictEqual(
            cache.get_many(['ford2', 'arthur2'], version=2),
            {'ford2': 37, 'arthur2': 42}
        )

        self.assertDictEqual(
            caches['v2'].get_many(['ford2', 'arthur2']),
            {'ford2': 37, 'arthur2': 42}
        )
        self.assertDictEqual(
            caches['v2'].get_many(['ford2', 'arthur2'], version=1),
            {}
        )
        self.assertDictEqual(
            caches['v2'].get_many(['ford2', 'arthur2'], version=2),
            {'ford2': 37, 'arthur2': 42}
        )

        # v2 set, using default version = 2
        caches['v2'].set_many({'ford3': 37, 'arthur3': 42})
        self.assertDictEqual(cache.get_many(['ford3', 'arthur3']), {})
        self.assertDictEqual(
            cache.get_many(['ford3', 'arthur3'], version=1),
            {}
        )
        self.assertDictEqual(
            cache.get_many(['ford3', 'arthur3'], version=2),
            {'ford3': 37, 'arthur3': 42}
        )

        self.assertDictEqual(
            caches['v2'].get_many(['ford3', 'arthur3']),
            {'ford3': 37, 'arthur3': 42}
        )
        self.assertDictEqual(
            caches['v2'].get_many(['ford3', 'arthur3'], version=1),
            {}
        )
        self.assertDictEqual(
            caches['v2'].get_many(['ford3', 'arthur3'], version=2),
            {'ford3': 37, 'arthur3': 42}
        )

        # v2 set, default version = 2, but manually override version = 1
        caches['v2'].set_many({'ford4': 37, 'arthur4': 42}, version=1)
        self.assertDictEqual(
            cache.get_many(['ford4', 'arthur4']),
            {'ford4': 37, 'arthur4': 42}
        )
        self.assertDictEqual(
            cache.get_many(['ford4', 'arthur4'], version=1),
            {'ford4': 37, 'arthur4': 42}
        )
        self.assertDictEqual(
            cache.get_many(['ford4', 'arthur4'], version=2),
            {}
        )

        self.assertDictEqual(
            caches['v2'].get_many(['ford4', 'arthur4']),
            {}
        )
        self.assertDictEqual(
            caches['v2'].get_many(['ford4', 'arthur4'], version=1),
            {'ford4': 37, 'arthur4': 42}
        )
        self.assertDictEqual(
            caches['v2'].get_many(['ford4', 'arthur4'], version=2),
            {}
        )

    def test_incr_version(self):
        cache.set('answer', 42, version=2)
        self.assertIsNone(cache.get('answer'))
        self.assertIsNone(cache.get('answer', version=1))
        self.assertEqual(cache.get('answer', version=2), 42)
        self.assertIsNone(cache.get('answer', version=3))

        self.assertEqual(cache.incr_version('answer', version=2), 3)
        self.assertIsNone(cache.get('answer'))
        self.assertIsNone(cache.get('answer', version=1))
        self.assertIsNone(cache.get('answer', version=2))
        self.assertEqual(cache.get('answer', version=3), 42)

        caches['v2'].set('answer2', 42)
        self.assertEqual(caches['v2'].get('answer2'), 42)
        self.assertIsNone(caches['v2'].get('answer2', version=1))
        self.assertEqual(caches['v2'].get('answer2', version=2), 42)
        self.assertIsNone(caches['v2'].get('answer2', version=3))

        self.assertEqual(caches['v2'].incr_version('answer2'), 3)
        self.assertIsNone(caches['v2'].get('answer2'))
        self.assertIsNone(caches['v2'].get('answer2', version=1))
        self.assertIsNone(caches['v2'].get('answer2', version=2))
        self.assertEqual(caches['v2'].get('answer2', version=3), 42)

        self.assertRaises(ValueError, cache.incr_version, 'does_not_exist')

    def test_decr_version(self):
        cache.set('answer', 42, version=2)
        self.assertIsNone(cache.get('answer'))
        self.assertIsNone(cache.get('answer', version=1))
        self.assertEqual(cache.get('answer', version=2), 42)

        self.assertEqual(cache.decr_version('answer', version=2), 1)
        self.assertEqual(cache.get('answer'), 42)
        self.assertEqual(cache.get('answer', version=1), 42)
        self.assertIsNone(cache.get('answer', version=2))

        caches['v2'].set('answer2', 42)
        self.assertEqual(caches['v2'].get('answer2'), 42)
        self.assertIsNone(caches['v2'].get('answer2', version=1))
        self.assertEqual(caches['v2'].get('answer2', version=2), 42)

        self.assertEqual(caches['v2'].decr_version('answer2'), 1)
        self.assertIsNone(caches['v2'].get('answer2'))
        self.assertEqual(caches['v2'].get('answer2', version=1), 42)
        self.assertIsNone(caches['v2'].get('answer2', version=2))

        with self.assertRaises(ValueError):
            cache.decr_version('does_not_exist', version=2)

    def test_custom_key_func(self):
        # Two caches with different key functions aren't visible to each other
        cache.set('answer1', 42)
        self.assertEqual(cache.get('answer1'), 42)
        self.assertIsNone(caches['custom_key'].get('answer1'))
        self.assertIsNone(caches['custom_key2'].get('answer1'))

        caches['custom_key'].set('answer2', 42)
        self.assertIsNone(cache.get('answer2'))
        self.assertEqual(caches['custom_key'].get('answer2'), 42)
        self.assertEqual(caches['custom_key2'].get('answer2'), 42)

    def test_cache_write_unpickable_object(self):
        update_middleware = UpdateCacheMiddleware()
        update_middleware.cache = cache

        fetch_middleware = FetchFromCacheMiddleware()
        fetch_middleware.cache = cache

        request = self.factory.get('/cache/test')
        request._cache_update_cache = True
        get_cache_data = FetchFromCacheMiddleware().process_request(request)
        self.assertIsNone(get_cache_data)

        response = HttpResponse()
        content = 'Testing cookie serialization.'
        response.content = content
        response.set_cookie('foo', 'bar')

        update_middleware.process_response(request, response)

        get_cache_data = fetch_middleware.process_request(request)
        self.assertIsNotNone(get_cache_data)
        self.assertEqual(get_cache_data.content, content.encode('utf-8'))
        self.assertEqual(get_cache_data.cookies, response.cookies)

        update_middleware.process_response(request, get_cache_data)
        get_cache_data = fetch_middleware.process_request(request)
        self.assertIsNotNone(get_cache_data)
        self.assertEqual(get_cache_data.content, content.encode('utf-8'))
        self.assertEqual(get_cache_data.cookies, response.cookies)

    def test_add_fail_on_pickleerror(self):
        "See https://code.djangoproject.com/ticket/21200"
        with self.assertRaises(pickle.PickleError):
            cache.add('unpickable', Unpickable())

    def test_set_fail_on_pickleerror(self):
        "See https://code.djangoproject.com/ticket/21200"
        with self.assertRaises(pickle.PickleError):
            cache.set('unpickable', Unpickable())

    def test_clear_commits_transaction(self):
        # Ensure the database transaction is committed (#19896)
        cache.set("key1", "spam")
        cache.clear()
        transaction.rollback()
        self.assertIsNone(cache.get("key1"))

    # Modified Django tests

    def test_expiration(self):
        # Cache values can be set to expire
        cache.set('expire1', 'very quickly', 0.1)
        cache.set('expire2', 'very quickly', 0.1)
        cache.set('expire3', 'very quickly', 0.1)

        time.sleep(0.2)
        self.assertIsNone(cache.get("expire1"))

        cache.add("expire2", "newvalue")
        self.assertEqual(cache.get("expire2"), "newvalue")
        self.assertFalse(cache.has_key("expire3"))  # noqa

    def test_get_many(self):
        # Multiple cache keys can be returned using get_many
        cache.set('a', 'a')
        cache.set('b', 'b')
        cache.set('c', 'c')
        cache.set('d', 'd')

        with self.assertNumQueries(1):
            value = cache.get_many(['a', 'c', 'd'])
        self.assertEqual(value, {'a': 'a', 'c': 'c', 'd': 'd'})

        with self.assertNumQueries(1):
            value = cache.get_many(['a', 'b', 'e'])

        self.assertEqual(value, {'a': 'a', 'b': 'b'})

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
        self.assertEqual(value, {'c': 'c', 'd': 'd'})

        with self.assertNumQueries(1):
            value = the_cache.get_many(['a', 'b', 'e'])

        self.assertEqual(value, {'b': 'b'})

    def test_set_many(self):
        # Single keys can be set using set_many
        with self.assertNumQueries(1):
            caches['no_cull'].set_many({"key1": "spam"})

        # Multiple keys can be set using set_many
        with self.assertNumQueries(1):
            caches['no_cull'].set_many({"key1": "spam", "key2": "eggs"})
        self.assertEqual(cache.get("key1"), "spam")
        self.assertEqual(cache.get("key2"), "eggs")

    def test_set_many_expiration(self):
        # set_many takes a second ``timeout`` parameter
        with self.assertNumQueries(1):
            caches['no_cull'].set_many({"key1": "spam", "key2": "eggs"}, 0.1)

        cache.set("key3", "ham")
        time.sleep(0.2)
        self.assertIsNone(cache.get("key1"))
        self.assertIsNone(cache.get("key2"))
        self.assertEqual(cache.get("key3"), "ham")

        # set_many expired values can be replaced
        with self.assertNumQueries(1):
            caches['no_cull'].set_many(
                {"key1": "spam", "key2": "egg", "key3": "spam", "key4": "ham"},
                1
            )
        v = cache.get("key1")
        self.assertEqual(v, "spam")
        self.assertEqual(cache.get("key2"), "egg")
        self.assertEqual(cache.get("key3"), "spam")
        self.assertEqual(cache.get("key4"), "ham")

    def test_delete_many(self):
        # Multiple keys can be deleted using delete_many
        cache.set("key1", "spam")
        cache.set("key2", "eggs")
        cache.set("key3", "ham")
        with self.assertNumQueries(1):
            cache.delete_many(["key1", "key2"])
        self.assertIsNone(cache.get("key1"))
        self.assertIsNone(cache.get("key2"))
        self.assertEqual(cache.get("key3"), "ham")

    def test_invalid_keys(self):
        # mimic custom ``make_key`` method being defined since the default will
        # never show the below warnings
        def func(key, *args):
            return key

        old_func = cache.key_func
        cache.key_func = func

        try:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                # memcached does not allow whitespace or control characters in
                # keys
                cache.set('key with spaces', 'value')
                self.assertEqual(len(w), 2)
                self.assertIsInstance(w[0].message, CacheKeyWarning)

            with self.assertRaises(ValueError):
                # memcached limits key length to 250
                # We have a 250 character max length on our table
                cache.set('a' * 251, 'value')
        finally:
            cache.key_func = old_func

    # Original tests

    def test_add_with_expired(self):
        cache.add("mykey", "value", 0.1)
        self.assertEqual(cache.get("mykey"), "value")

        result = cache.add("mykey", "newvalue", 0.1)
        self.assertFalse(result)
        self.assertEqual(cache.get("mykey"), "value")

        time.sleep(0.2)

        result = cache.add("mykey", "newvalue", 1)
        self.assertTrue(result)
        self.assertEqual(cache.get("mykey"), "newvalue")

    @override_cache_settings(options={'COMPRESS_MIN_LENGTH': 10})
    def test_compressed(self):
        cache.set("key", "a" * 11)
        self.assertEqual(cache.get("key"), "a" * 11)

    @override_cache_settings(options={'COMPRESS_MIN_LENGTH': 10,
                                      'COMPRESS_LEVEL': 9})
    def test_compress_level(self):
        cache.set("key", "a" * 11)
        self.assertEqual(cache.get("key"), "a" * 11)

        # Check a bad compression level = zlib error
        with override_cache_settings(options={'COMPRESS_MIN_LENGTH': 10,
                                              'COMPRESS_LEVEL': 123}):
            with self.assertRaises(Exception) as cm:
                cache.set("key", "a" * 11)
            self.assertIn("Bad compression level", str(cm.exception))

    @override_cache_settings(options={'COMPRESS_MIN_LENGTH': 10})
    def test_changing_compressed_option_leaves_compressed_data_readable(self):
        a11 = "a" * 11
        cache.set("key", a11)

        # Turn it off - remains readable and settable
        with override_cache_settings(options={'COMPRESS_MIN_LENGTH': 0}):
            self.assertEqual(cache.get("key"), a11)
            cache.set("key", a11)
            self.assertEqual(cache.get("key"), a11)

        # Back on, still readable
        self.assertEqual(cache.get("key"), a11)
        cache.set("key", a11)
        self.assertEqual(cache.get("key"), a11)

    def test_our_options_quacks_like_djangos(self):
        from django.core.cache.backends.db import Options
        from django_mysql.cache import Options as OurOptions
        theirs = Options('something')
        ours = OurOptions('something')
        self.assertEqual(
            set(ours.__dict__.keys()),
            set(theirs.__dict__.keys())
        )

    def test_cull(self):
        self._perform_cull_test(caches['cull'], 50, 30)

    def test_zero_cull(self):
        self._perform_cull_test(caches['zero_cull'], 50, 20)

    def test_no_cull_only_deletes_when_told(self):
        self._perform_cull_test(caches['no_cull'], 50, 50)
        caches['no_cull'].cull()
        self.assertEqual(self.table_count(), 25)

    def test_cull_deletes_expired_first(self):
        cull_cache = caches['cull']
        cull_cache.set("key", "value", 0.1)
        time.sleep(0.2)

        # Add 30 more entries. The expired key should get deleted, leaving the
        # 30 new keys
        self._perform_cull_test(cull_cache, 30, 30)
        self.assertIsNone(cull_cache.get('key'))

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
        self.assertEqual(count, final_count)

    def test_incr_range(self):
        cache.set('overwhelm', BIGINT_SIGNED_MAX - 1)
        cache.incr('overwhelm')
        with self.assertRaises(OperationalError):
            cache.incr('overwhelm')

    def test_decr_range(self):
        cache.set('underwhelm', BIGINT_SIGNED_MIN + 1)
        cache.decr('underwhelm')
        with self.assertRaises(OperationalError):
            cache.decr('underwhelm')

    def test_cant_incr_decimals(self):
        # Cached values that aren't ints can't be incremented
        cache.set('answer', Decimal('1.1'))
        with self.assertRaises(ValueError):
            cache.incr('answer')

    def test_cant_decr_decimals(self):
        # Cached values that aren't ints can't be decremented
        cache.set('answer', Decimal('9.9'))
        with self.assertRaises(ValueError):
            cache.decr('answer')

    def test_set_int_subclass(self):
        # Storing an int subclass should return that int subclass
        cache.set('myint', MyInt(2))
        val = cache.get('myint')
        self.assertEqual(val.times2(), 4)

        # Can't increment it since it's a pickle object on the table, not an
        # integer
        with self.assertRaises(ValueError):
            cache.incr('myint')

    def test_unknown_value_type_errors(self):
        # Unknown value_type values should be errors, since we don't know how
        # to deserialize them. New value_types will probably be introduced by
        # later versions or subclasses of MySQLCache

        cache.set('mykey', 123)
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE `%s` SET value_type = '?'" % self.table_name
            )

        with self.assertRaises(ValueError):
            cache.get('mykey')

    # mysql_cache_migration tests

    def test_mysql_cache_migration(self):
        out = StringIO()
        call_command('mysql_cache_migration', stdout=out)
        output = out.getvalue()

        # Lint it
        with captured_stdout() as stderr:
            errors = check_code(output)
        self.assertEqual(
            errors,
            0,
            "Encountered {} errors whilst trying to lint the mysql cache "
            "migration.\nMigration:\n\n{}\n\nLint errors:\n\n{}"
            .format(errors, output, stderr.getvalue())
        )

    def test_mysql_cache_migration_alias(self):
        out = StringIO()
        call_command('mysql_cache_migration', 'default', stdout=out)
        output = out.getvalue()

        num_run_sqls = (len(output.split('RunSQL')) - 1)
        self.assertEqual(num_run_sqls, 1)

    def test_mysql_cache_migration_non_existent(self):
        out = StringIO()
        with self.assertRaises(CommandError):
            call_command('mysql_cache_migration', 'nonexistent', stdout=out)

    @override_cache_settings(
        BACKEND='django.core.cache.backends.dummy.DummyCache'
    )
    def test_mysql_cache_migration_no_mysql_caches(self):
        err = StringIO()
        call_command('mysql_cache_migration', stderr=err)
        self.assertIn("No MySQLCache instances in CACHES", err.getvalue())

    # cull_mysql_caches tests

    def test_cull_mysql_caches_basic(self):
        cache.set('key', 'value', 0.1)
        time.sleep(0.2)
        self.assertEqual(self.table_count(), 1)
        call_command('cull_mysql_caches', verbosity=0)
        self.assertEqual(self.table_count(), 0)

    def test_cull_mysql_caches_named_cache(self):
        cache.set('key', 'value', 0.1)
        time.sleep(0.2)
        self.assertEqual(self.table_count(), 1)

        out = StringIO()
        call_command('cull_mysql_caches', 'default', verbosity=1, stdout=out)
        output = out.getvalue()
        self.assertEqual(
            output.strip(),
            "Deleting from cache 'default'... 1 entries deleted."
        )
        self.assertEqual(self.table_count(), 0)

    def test_cull_mysql_caches_bad_cache_name(self):
        with self.assertRaises(CommandError) as cm:
            call_command('cull_mysql_caches', "NOTACACHE", verbosity=0)
        self.assertEqual("Cache 'NOTACACHE' does not exist", str(cm.exception))
