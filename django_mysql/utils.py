# -*- coding:utf-8 -*-
from __future__ import division


class WeightedAverageRate(object):
    # Sub: new
    #
    # Required Arguments:
    #   target_t   - Target time for t in <update()>
    #
    # Optional Arguments:
    #   weight - Weight of previous n/t values (default 0.75).
    #
    # Returns:
    #   WeightedAvgRate

    def __init__(self, target_t, weight=0.75):
        self.target_t = target_t
        self.avg_n = 0.0
        self.avg_t = 0.0
        self.weight = weight

    def update(self, n, t):
        # Update weighted average rate.  Param n is generic; it's how many of
        # whatever the caller is doing (rows, checksums, etc.).  Param s is how
        # long this n took, in seconds (hi-res or not).
        #
        # Parameters:
        #   n - Number of operations (rows, etc.)
        #   t - Amount of time in seconds that n took
        #
        # Returns:
        #   n adjust to meet target_t based on weighted decaying avg rate

        if self.avg_n and self.avg_t:
            self.avg_n = (self.avg_n * self.weight) + n
            self.avg_t = (self.avg_t * self.weight) + t
        else:
            self.avg_n = n
            self.avg_t = t

        avg_rate = self.avg_n / self.avg_t
        new_n = int(avg_rate * self.target_t)
        return new_n

        # if ( $self->{avg_n} && $self->{avg_t} ) {
        #   $self->{avg_n}    = ($self->{avg_n} * $self->{weight}) + $n;
        #   $self->{avg_t}    = ($self->{avg_t} * $self->{weight}) + $t;
        #   $self->{avg_rate} = $self->{avg_n}  / $self->{avg_t};
        #   PTDEBUG && _d('Weighted avg rate:', $self->{avg_rate}, 'n/s');
        # }
        # else {
        #   $self->{avg_n}    = $n;
        #   $self->{avg_t}    = $t;
        #   $self->{avg_rate} = $self->{avg_n}  / $self->{avg_t};
        #   PTDEBUG && _d('Initial avg rate:', $self->{avg_rate}, 'n/s');
        # }

        # my $new_n = int($self->{avg_rate} * $self->{target_t});
        # PTDEBUG && _d('Adjust n to', $new_n);
        # return $new_n;
