#!/usr/bin/env python2

import sys

vals = [float(line) for line in sys.stdin]
vals.sort()

percentiles = [50, 75, 90, 95, 99]

print "samples: %d" % len(vals)
for percentile in percentiles:
  print "%s%%: %s" % (percentile, vals[(len(vals) * percentile)/100])
