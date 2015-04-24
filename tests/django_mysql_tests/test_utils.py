# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from time import sleep
from unittest import skipUnless

from django.test import TestCase

from django_mysql.utils import (
    have_program, pt_fingerprint, PTFingerprintThread, WeightedAverageRate
)


class WeightedAverageRateTests(TestCase):

    def test_constant(self):
        # If we keep achieving a rate of 100 rows in 0.5 seconds, it should
        # recommend that we keep there
        rate = WeightedAverageRate(0.5)
        self.assertEqual(rate.update(100, 0.5), 100)
        self.assertEqual(rate.update(100, 0.5), 100)
        self.assertEqual(rate.update(100, 0.5), 100)

    def test_slow(self):
        # If we keep achieving a rate of 100 rows in 1 seconds, it should
        # recommend that we move to 50
        rate = WeightedAverageRate(0.5)
        self.assertEqual(rate.update(100, 1.0), 50)
        self.assertEqual(rate.update(100, 1.0), 50)
        self.assertEqual(rate.update(100, 1.0), 50)

    def test_fast(self):
        # If we keep achieving a rate of 100 rows in 0.25 seconds, it should
        # recommend that we move to 200
        rate = WeightedAverageRate(0.5)
        self.assertEqual(rate.update(100, 0.25), 200)
        self.assertEqual(rate.update(100, 0.25), 200)
        self.assertEqual(rate.update(100, 0.25), 200)

    def test_good_guess(self):
        # If we are first slow then hit the target at 50, we should be good
        rate = WeightedAverageRate(0.5)
        self.assertEqual(rate.update(100, 1.0), 50)
        self.assertEqual(rate.update(50, 0.5), 50)
        self.assertEqual(rate.update(50, 0.5), 50)
        self.assertEqual(rate.update(50, 0.5), 50)

    def test_zero_division(self):
        rate = WeightedAverageRate(0.5)
        self.assertEqual(rate.update(1, 0.0), 500)


@skipUnless(have_program('pt-fingerprint'),
            "pt-fingerprint must be installed")
class PTFingerprintTests(TestCase):

    def test_basic(self):
        self.assertEqual(pt_fingerprint('SELECT 5'), 'select ?')
        self.assertEqual(pt_fingerprint('SELECT 5;'), 'select ?')

    def test_long(self):
        query = """
            SELECT
                CONCAT(customer.last_name, ', ', customer.first_name)
                    AS customer,
                address.phone,
                film.title
            FROM rental
                INNER JOIN customer
                    ON rental.customer_id = customer.customer_id
                INNER JOIN address
                    ON customer.address_id = address.address_id
                INNER JOIN inventory
                    ON rental.inventory_id = inventory.inventory_id
                INNER JOIN film
                    ON inventory.film_id = film.film_id
            WHERE
                rental.return_date IS NULL AND
                rental_date + INTERVAL film.rental_duration DAY <
                    CURRENT_DATE()
            LIMIT 5"""
        self.assertEqual(
            pt_fingerprint(query),
            "select concat(customer.last_name, ?, customer.first_name) as "
            "customer, address.phone, film.title from rental inner join "
            "customer on rental.customer_id = customer.customer_id inner join "
            "address on customer.address_id = address.address_id inner join "
            "inventory on rental.inventory_id = inventory.inventory_id inner "
            "join film on inventory.film_id = film.film_id where "
            "rental.return_date is ? and rental_date ? interval "
            "film.rental_duration day < current_date() limit ?"
        )

    def test_the_thread_shuts_on_time_out(self):
        PTFingerprintThread.PROCESS_LIFETIME = 0.1
        pt_fingerprint("select 123")
        sleep(0.2)
        self.assertIsNone(PTFingerprintThread.the_thread)
        PTFingerprintThread.PROCESS_LIFETIME = 60
