import os

import statsd

statsd_client = statsd.StatsClient(
    host=os.environ.get('STATSD_HOST', 'localhost'), prefix='embedly_proxy')
