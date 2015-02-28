# -*- coding:utf-8 -*-
from __future__ import division

from contextlib import contextmanager
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
