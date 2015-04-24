#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import sys
import subprocess


def main():
    try:
        sys.argv.remove('--nolint')
    except ValueError:
        run_lint = True
    else:
        run_lint = False

    try:
        sys.argv.remove('--lintonly')
    except ValueError:
        run_tests = True
    else:
        run_tests = False

    if run_tests:
        tests_main()

    if run_lint:
        exit_on_failure(run_flake8())
        exit_on_failure(run_2to3())


def tests_main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    sys.path.insert(0, "tests")
    from django.core.management import execute_from_command_line
    sys.argv.insert(1, "test")
    return execute_from_command_line(sys.argv)


def run_flake8():
    print('Running flake8 code linting')
    ret = subprocess.call(['flake8', 'django_mysql', 'tests'])
    print('flake8 failed' if ret else 'flake8 passed')
    return ret


def run_2to3():
    print('Running 2to3 checks')
    output = subprocess.check_output([
        '2to3',
        '-f', 'idioms',
        '-f', 'isinstance',
        '-f', 'set_literal',
        '-f', 'tuple_params',
        'django_mysql', 'tests'
    ]).strip()
    if output > '':
        print('2to3 failed')
        print(output)
        return 1
    else:
        print('2to3 passed')
        return 0


def exit_on_failure(ret, message=None):
    if ret:
        sys.exit(ret)


if __name__ == '__main__':
    main()
