#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import sys
import subprocess


FLAKE8_ARGS = ['django_mysql', 'tests']


def main():
    try:
        sys.argv.remove('--nolint')
    except ValueError:
        run_flake8 = True
    else:
        run_flake8 = False

    try:
        sys.argv.remove('--lintonly')
    except ValueError:
        run_tests = True
    else:
        run_tests = False

    if run_tests:
        tests_main()

    if run_flake8:
        exit_on_failure(flake8_main(FLAKE8_ARGS))


def tests_main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    sys.path.insert(0, "tests")
    from django.core.management import execute_from_command_line
    sys.argv.insert(1, "test")
    return execute_from_command_line(sys.argv)


def flake8_main(args):
    print('Running flake8 code linting')
    ret = subprocess.call(['flake8'] + args)
    print('flake8 failed' if ret else 'flake8 passed')
    return ret


def exit_on_failure(ret, message=None):
    if ret:
        sys.exit(ret)


if __name__ == '__main__':
    main()
