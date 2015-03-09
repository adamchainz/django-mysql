# -*- coding:utf-8 -*-
from __future__ import division

from contextlib import contextmanager
from subprocess import call, PIPE
import time


class WeightedAverageRate(object):
    """
    Adapted from percona-toolkit - provides a weighted average counter to keep
    at a certain rate of activity (row iterations etc.).
    """
    def __init__(self, target_t, weight=0.75):
        """
        target_t - Target time for t in update()
        weight - Weight of previous n/t values
        """
        self.target_t = target_t
        self.avg_n = 0.0
        self.avg_t = 0.0
        self.weight = weight

    def update(self, n, t):
        """
        Update weighted average rate.  Param n is generic; it's how many of
        whatever the caller is doing (rows, checksums, etc.).  Param s is how
        long this n took, in seconds (hi-res or not).

        Parameters:
            n - Number of operations (rows, etc.)
            t - Amount of time in seconds that n took

        Returns:
            n adjusted to meet target_t based on weighted decaying avg rate
        """
        if self.avg_n and self.avg_t:
            self.avg_n = (self.avg_n * self.weight) + n
            self.avg_t = (self.avg_t * self.weight) + t
        else:
            self.avg_n = n
            self.avg_t = t

        avg_rate = self.avg_n / self.avg_t
        new_n = int(avg_rate * self.target_t)
        return new_n


class StopWatch(object):
    """
    Context manager for timing a block
    """
    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args, **kwargs):
        self.end_time = time.time()
        self.total_time = self.end_time - self.start_time


@contextmanager
def noop_context(*args, **kwargs):
    yield


def settings_to_cmd_args(settings_dict):
    """
    Copied from django 1.8 MySQL backend DatabaseClient - where the runshell
    commandline creation has been extracted and made callable like so.
    """
    args = ['mysql']
    db = settings_dict['OPTIONS'].get('db', settings_dict['NAME'])
    user = settings_dict['OPTIONS'].get('user', settings_dict['USER'])
    passwd = settings_dict['OPTIONS'].get('passwd', settings_dict['PASSWORD'])
    host = settings_dict['OPTIONS'].get('host', settings_dict['HOST'])
    port = settings_dict['OPTIONS'].get('port', settings_dict['PORT'])
    cert = settings_dict['OPTIONS'].get('ssl', {}).get('ca')
    defaults_file = settings_dict['OPTIONS'].get('read_default_file')
    # Seems to be no good way to set sql_mode with CLI.

    if defaults_file:
        args += ["--defaults-file=%s" % defaults_file]
    if user:
        args += ["--user=%s" % user]
    if passwd:
        args += ["--password=%s" % passwd]
    if host:
        if '/' in host:
            args += ["--socket=%s" % host]
        else:
            args += ["--host=%s" % host]
    if port:
        args += ["--port=%s" % port]
    if cert:
        args += ["--ssl-ca=%s" % cert]
    if db:
        args += [db]
    return args


def have_program(program_name):
    status = call(['which', program_name], stdout=PIPE)
    return (status == 0)
