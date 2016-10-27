# -*- coding:utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from unittest import mock, skipIf

import django
import pytest
from django.core.management import CommandError, call_command
from django.db.utils import ConnectionHandler
from django.test import SimpleTestCase
from django.utils.six.moves import StringIO

# Can't use @override_settings to swap out DATABASES, instead just mock.patch
# a new ConnectionHandler into the command module
command_connections = 'django_mysql.management.commands.dbparams.connections'

sqlite = ConnectionHandler({
    'default': {'ENGINE': 'django.db.backends.sqlite3'}
})

full_db = ConnectionHandler({'default': {
    'ENGINE': 'django.db.backends.mysql',
    'NAME': 'mydatabase',
    'USER': 'ausername',
    'PASSWORD': 'apassword',
    'HOST': 'ahost.example.com',
    'PORT': '12345',
    'OPTIONS': {
        'read_default_file': '/tmp/defaults.cnf',
        'ssl': {'ca': '/tmp/mysql.cert'}
    }
}})

socket_db = ConnectionHandler({'default': {
    'ENGINE': 'django.db.backends.mysql',
    'HOST': '/etc/mydb.sock',
}})


class DBParamsTests(SimpleTestCase):

    @skipIf(django.VERSION[:2] >= (1, 10),
            'argument parsing uses a fixed single argument in Django 1.10+')
    def test_invalid_number_of_databases(self):
        with pytest.raises(CommandError) as excinfo:
            call_command('dbparams', 'default', 'default', skip_checks=True)
        assert "more than one connection" in str(excinfo.value)

    def test_invalid_database(self):
        with pytest.raises(CommandError) as excinfo:
            call_command('dbparams', 'nonexistent', skip_checks=True)
        assert "does not exist" in str(excinfo.value)

    def test_invalid_both(self):
        with pytest.raises(CommandError):
            call_command('dbparams', dsn=True, mysql=True, skip_checks=True)

    @mock.patch(command_connections, sqlite)
    def test_invalid_not_mysql(self):
        with pytest.raises(CommandError) as excinfo:
            call_command('dbparams', skip_checks=True)
        assert "not a MySQL database connection" in str(excinfo.value)

    @mock.patch(command_connections, full_db)
    def test_mysql_full(self):
        out = StringIO()
        call_command('dbparams', stdout=out, skip_checks=True)
        output = out.getvalue()
        assert (
            output ==
            "--defaults-file=/tmp/defaults.cnf --user=ausername "
            "--password=apassword --host=ahost.example.com --port=12345 "
            "--ssl-ca=/tmp/mysql.cert mydatabase"
        )

    @mock.patch(command_connections, socket_db)
    def test_mysql_socket(self):
        out = StringIO()
        call_command('dbparams', stdout=out, skip_checks=True)
        output = out.getvalue()
        assert output == "--socket=/etc/mydb.sock"

    @mock.patch(command_connections, full_db)
    def test_dsn_full(self):
        out = StringIO()
        err = StringIO()
        call_command('dbparams', 'default', dsn=True,
                     stdout=out, stderr=err, skip_checks=True)
        output = out.getvalue()
        assert (
            output ==
            "F=/tmp/defaults.cnf,u=ausername,p=apassword,h=ahost.example.com,"
            "P=12345,D=mydatabase"
        )

        errors = err.getvalue()
        assert "SSL params can't be" in errors

    @mock.patch(command_connections, socket_db)
    def test_dsn_socket(self):
        out = StringIO()
        err = StringIO()
        call_command('dbparams', dsn=True,
                     stdout=out, stderr=err, skip_checks=True)

        output = out.getvalue()
        assert output == 'S=/etc/mydb.sock'

        errors = err.getvalue()
        assert errors == ""
