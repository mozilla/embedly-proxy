from embedly.stats import statsd_client

def get_url_data(url):
    print 'getting url data', url
    statsd_client.incr(url)
