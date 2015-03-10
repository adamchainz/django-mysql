# -*- coding:utf-8 -*-
from django.core.management import call_command, CommandError
from django.db.utils import ConnectionHandler
from django.test import TestCase
from django.utils.six.moves import StringIO

import mock


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


class DBParamsTests(TestCase):

    def test_invalid_number_of_databases(self):
        with self.assertRaises(CommandError) as cm:
            call_command('dbparams', 'default', 'default')
        self.assertIn("more than one connection", str(cm.exception))

    def test_invalid_database(self):
        with self.assertRaises(CommandError) as cm:
            call_command('dbparams', 'nonexistent')
        self.assertIn("does not exist", str(cm.exception))

    def test_invalid_both(self):
        with self.assertRaises(CommandError):
            call_command('dbparams', dsn=True, mysql=True)

    @mock.patch(command_connections, sqlite)
    def test_invalid_not_mysql(self):
        with self.assertRaises(CommandError) as cm:
            call_command('dbparams')
        self.assertIn("not a MySQL database connection", str(cm.exception))

    @mock.patch(command_connections, full_db)
    def test_mysql_full(self):
        out = StringIO()
        call_command('dbparams', stdout=out)
        output = out.getvalue()
        self.assertEqual(
            output,
            "--defaults-file=/tmp/defaults.cnf --user=ausername "
            "--password=apassword --host=ahost.example.com --port=12345 "
            "--ssl-ca=/tmp/mysql.cert mydatabase"
        )

    @mock.patch(command_connections, socket_db)
    def test_mysql_socket(self):
        out = StringIO()
        call_command('dbparams', stdout=out)
        output = out.getvalue()
        self.assertEqual(output, "--socket=/etc/mydb.sock")

    @mock.patch(command_connections, full_db)
    def test_dsn_full(self):
        out = StringIO()
        err = StringIO()
        call_command('dbparams', 'default', dsn=True, stdout=out, stderr=err)
        output = out.getvalue()
        self.assertEqual(
            output,
            "F=/tmp/defaults.cnf,u=ausername,p=apassword,h=ahost.example.com,"
            "P=12345,D=mydatabase"
        )

        errors = err.getvalue()
        self.assertIn("SSL params can't be", errors)

    @mock.patch(command_connections, socket_db)
    def test_dsn_socket(self):
        out = StringIO()
        err = StringIO()
        call_command('dbparams', dsn=True, stdout=out, stderr=err)

        output = out.getvalue()
        self.assertEqual(output, 'S=/etc/mydb.sock')

        errors = err.getvalue()
        self.assertEqual(errors, "")
