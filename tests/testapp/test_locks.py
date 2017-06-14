# -*- coding:utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from threading import Thread

import pytest
from django.db import OperationalError, connection
from django.db.transaction import TransactionManagementError, atomic
from django.test import TestCase, TransactionTestCase
from django.utils.six.moves import queue

from django_mysql.exceptions import TimeoutError
from django_mysql.locks import Lock, TableLock
from django_mysql.models import Model
from django_mysql.utils import connection_is_mariadb
from testapp.models import (
    AgedCustomer, Alphabet, Customer, ProxyAlphabet, TitledAgedCustomer
)


class LockTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super(LockTests, cls).setUpClass()

        cls.supports_lock_info = (
            connection_is_mariadb(connection) and
            connection.mysql_version >= (10, 0, 7)
        )
        if cls.supports_lock_info:
            with connection.cursor() as cursor:
                cursor.execute(
                    """SELECT COUNT(*) FROM INFORMATION_SCHEMA.PLUGINS
                       WHERE PLUGIN_NAME = 'metadata_lock_info'""")
                cls.lock_info_preinstalled = (cursor.fetchone()[0] > 0)
                if not cls.lock_info_preinstalled:
                    cursor.execute("INSTALL SONAME 'metadata_lock_info'")

    @classmethod
    def tearDownClass(cls):
        if cls.supports_lock_info and not cls.lock_info_preinstalled:
            with connection.cursor() as cursor:
                cursor.execute("UNINSTALL SONAME 'metadata_lock_info'")
        super(LockTests, cls).tearDownClass()

    def test_simple(self):
        mylock = Lock("mylock")
        assert not mylock.is_held()

        with mylock:
            assert mylock.is_held()
            assert Lock("mylock").is_held()

            cursor = connection.cursor()
            cursor.execute("SELECT CONNECTION_ID();")
            own_connection_id = cursor.fetchone()[0]
            assert mylock.holding_connection_id() == own_connection_id

        assert not mylock.is_held()
        assert not Lock("mylock").is_held()

    import_time_lock = Lock('defined_at_import_time')

    def test_error_on_unneeded_exit(self):
        mylock = Lock("mylock")
        assert not mylock.is_held()
        with pytest.raises(ValueError) as excinfo:
            mylock.__exit__(None, None, None)
        assert "unheld lock" in str(excinfo.value)

    def test_defined_at_import_time(self):
        import_time_lock = self.import_time_lock

        assert not import_time_lock.is_held()

        with import_time_lock:
            assert import_time_lock.is_held()

            cursor = connection.cursor()
            cursor.execute("SELECT CONNECTION_ID();")
            own_connection_id = cursor.fetchone()[0]
            assert (
                import_time_lock.holding_connection_id() == own_connection_id
            )

        assert not import_time_lock.is_held()

    def test_timeout_with_threads(self):
        to_me = queue.Queue()
        to_you = queue.Queue()

        def lock_until_told():
            with Lock('threading_test'):
                to_me.put("Locked")
                to_you.get(True)

        threading_test = Lock('threading_test', 0.05)
        assert not threading_test.is_held()

        other_thread = Thread(target=lock_until_told)
        other_thread.start()
        try:
            item = to_me.get(True)
            assert item == "Locked"

            cursor = connection.cursor()
            cursor.execute("SELECT CONNECTION_ID();")
            own_connection_id = cursor.fetchone()[0]

            assert threading_test.is_held()
            assert threading_test.holding_connection_id() != own_connection_id

            with pytest.raises(TimeoutError):
                with threading_test:
                        pass

            to_you.put("Stop")
        finally:
            other_thread.join()

        assert not threading_test.is_held()
        with threading_test:
            pass

    def test_threads_concurrent_access(self):
        """
        Test that the same lock object can be used in multiple threads, allows
        the definition of a lock upfront in a module.
        """
        to_me = queue.Queue()
        to_you = queue.Queue()
        the_lock = Lock('THElock', 0.05)

        def check_it_lock_it():
            assert not the_lock.is_held()
            with the_lock:
                to_me.put("Locked")
                to_you.get(True)

        other_thread = Thread(target=check_it_lock_it)
        other_thread.start()
        try:
            item = to_me.get(True)
            assert item == "Locked"

            cursor = connection.cursor()
            cursor.execute("SELECT CONNECTION_ID()")
            own_connection_id = cursor.fetchone()[0]

            assert the_lock.is_held()
            assert the_lock.holding_connection_id() != own_connection_id

            with pytest.raises(TimeoutError):
                with the_lock:
                    pass

            to_you.put("Stop")
        finally:
            other_thread.join()

        with the_lock:
            pass

    def test_holding_more_than_one(self):
        is_mariadb = connection_is_mariadb(connection)
        supports_multiple_locks = (
            (is_mariadb and connection.mysql_version >= (10, 0, 2)) or
            (not is_mariadb and connection.mysql_version >= (5, 7))
        )
        if not supports_multiple_locks:
            self.skipTest(
                "Only MySQL 5.7+ and MariaDB 10.0.2+ have the ability to hold "
                "more than one named lock"
            )

        lock_a = Lock("a")
        lock_b = Lock("b")
        with lock_a, lock_b:
            assert lock_a.is_held()

    def test_multi_connection(self):
        lock_a = Lock("a")
        lock_b = Lock("b", using='other')

        with lock_a, lock_b:
            # Different connections = can hold > 1!
            assert lock_a.is_held()
            assert lock_b.is_held()

    def test_held_with_prefix(self):
        if not self.supports_lock_info:
            self.skipTest(
                "Only MariaDB 10.0.7+ has the metadata_lock_info plugin on "
                "which held_with_prefix relies"
            )

        assert Lock.held_with_prefix('') == {}
        assert Lock.held_with_prefix('mylock') == {}

        with Lock('mylock-alpha') as lock:
            assert (
                Lock.held_with_prefix('') ==
                {'mylock-alpha': lock.holding_connection_id()}
            )
            assert (
                Lock.held_with_prefix('mylock') ==
                {'mylock-alpha': lock.holding_connection_id()}
            )
            assert (
                Lock.held_with_prefix('mylock-beta') ==
                {}
            )

        assert Lock.held_with_prefix('') == {}
        assert Lock.held_with_prefix('mylock') == {}

    def test_acquire_release(self):
        my_lock = Lock('not_a_context_manager')
        my_lock.acquire()
        my_lock.release()


class TableLockTests(TransactionTestCase):

    def tearDown(self):
        super(TableLockTests, self).tearDown()
        Alphabet.objects.all().delete()
        Alphabet.objects.using('other').all().delete()
        Customer.objects.all().delete()
        Customer.objects.using('other').all().delete()

    def test_write(self):
        Alphabet.objects.create(a=12345)
        with TableLock(write=[Alphabet]):
            assert Alphabet.objects.count() == 1

            Alphabet.objects.all().delete()
            assert Alphabet.objects.count() == 0

        assert Alphabet.objects.count() == 0

    def test_write_with_table_name(self):
        Alphabet.objects.create(a=71718)
        with TableLock(write=[Alphabet._meta.db_table]):
            assert Alphabet.objects.count() == 1

            Alphabet.objects.all().delete()
            assert Alphabet.objects.count() == 0

        assert Alphabet.objects.count() == 0

    def test_write_with_using(self):
        Alphabet.objects.using('other').create(a=878787)
        with TableLock(write=[Alphabet], using='other'):
            assert Alphabet.objects.using('other').count() == 1

            Alphabet.objects.using('other').all().delete()
            assert Alphabet.objects.using('other').count() == 0

        assert Alphabet.objects.using('other').count() == 0

    def test_write_twice(self):
        with TableLock(write=[Alphabet]):
            Alphabet.objects.create(a=1)

        with TableLock(write=[Alphabet]):
            Alphabet.objects.create(a=2)

    def test_write_fails_touching_other_table(self):
        with pytest.raises(OperationalError) as excinfo:
            with TableLock(write=[Alphabet]):
                Customer.objects.create(name="Lizzy")

        assert "was not locked with LOCK TABLES" in str(excinfo.value)

    def test_read_and_write(self):
        Customer.objects.create(name="Fred")
        with TableLock(read=[Customer], write=[Alphabet]):
            ab = Alphabet.objects.create(a=Customer.objects.count())
            assert ab.a == 1

    def test_creates_an_atomic(self):
        assert connection.get_autocommit() == 1
        assert not connection.in_atomic_block
        with TableLock(read=[Alphabet]):
            assert connection.get_autocommit() == 0
            assert connection.in_atomic_block
        assert connection.get_autocommit() == 1
        assert not connection.in_atomic_block

    def test_fails_in_atomic(self):
        with atomic(), pytest.raises(TransactionManagementError) as excinfo:
            with TableLock(read=[Alphabet]):
                pass

        assert str(excinfo.value).startswith("InnoDB requires that we not be")

    def test_fail_nested(self):
        with pytest.raises(TransactionManagementError) as excinfo:
            with TableLock(write=[Alphabet]), TableLock(write=[Customer]):
                pass

        assert str(excinfo.value).startswith("InnoDB requires that we not be")

    def test_atomic_works_in_lock(self):
        Alphabet.objects.create(a=4567)
        with TableLock(write=[Alphabet]):
            assert Alphabet.objects.count() == 1

            try:
                with atomic():
                    raise ValueError("Hi")
            except ValueError:
                pass

            Alphabet.objects.all().delete()
            assert Alphabet.objects.count() == 0

    def test_writes_fail_under_read(self):
        with TableLock(read=[Alphabet]):
            with pytest.raises(OperationalError) as excinfo:
                Alphabet.objects.update(a=2)

            assert (
                "was locked with a READ lock and can't be updated" in
                str(excinfo.value)
            )

    def test_fails_with_abstract_model(self):
        with pytest.raises(ValueError) as excinfo:
            with TableLock(read=[Model]):
                pass

        assert "Can't lock abstract model Model" in str(excinfo.value)

    def test_proxy_model(self):
        Alphabet.objects.create(a=2, b=3)

        with TableLock(read=[ProxyAlphabet]):
            ab = ProxyAlphabet.objects.get()
            assert ab.a_times_b == 6

        with TableLock(write=[ProxyAlphabet]):
            assert ProxyAlphabet.objects.count() == 1
            ProxyAlphabet.objects.all().delete()
            assert ProxyAlphabet.objects.count() == 0

        assert ProxyAlphabet.objects.count() == 0

    def test_inherited_model(self):
        TitledAgedCustomer.objects.create(title="Sir", name="Knighty")

        with TableLock(write=[TitledAgedCustomer]):
            assert Customer.objects.count() == 1

            TitledAgedCustomer.objects.create(name="Grandpa Potts", age=99)
            assert Customer.objects.count() == 2
            assert TitledAgedCustomer.objects.count() == 2

            TitledAgedCustomer.objects.all().delete()
            assert Customer.objects.count() == 0
            assert AgedCustomer.objects.count() == 0
            assert TitledAgedCustomer.objects.count() == 0

        assert Customer.objects.count() == 0
        assert AgedCustomer.objects.count() == 0
        assert TitledAgedCustomer.objects.count() == 0

    def test_inherited_model_top_parent_fails(self):
        AgedCustomer.objects.create(age=99999, name="Methuselah")
        with pytest.raises(OperationalError) as excinfo:
            with TableLock(write=[Customer]):
                # Django automatically follows down to children which aren't
                # locked
                Customer.objects.all().delete()
        assert "was not locked with LOCK TABLES" in str(excinfo.value)

    def test_read_and_write_with_threads(self):
        to_me = queue.Queue()

        def get_read_lock():
            with TableLock(read=[Alphabet]):
                to_me.put("Reading")

        try:
            # Thread can obtain lock alone
            other_thread = Thread(target=get_read_lock)
            other_thread.start()
            assert to_me.get() == "Reading"

            with TableLock(write=[Alphabet]):
                other_thread = Thread(target=get_read_lock)
                other_thread.start()

                # Doesn't lock now
                with pytest.raises(queue.Empty):
                    to_me.get(timeout=0.2)

            # Gets now
            assert to_me.get() == "Reading"
        finally:
            other_thread.join()

    def test_acquire_release(self):
        my_lock = TableLock(read=[Alphabet])
        my_lock.acquire()
        my_lock.release()
