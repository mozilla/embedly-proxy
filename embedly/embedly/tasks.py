def fetch_remote_url_data(urls, redis_client=None):
    from embedly.app import get_extractor
    from embedly.stats import statsd_client

    statsd_client.gauge('task_fetch_url_start', len(urls))

    extractor = get_extractor(redis_client=redis_client)

    url_data = extractor.get_remote_urls(urls)

    statsd_client.gauge('task_fetch_url_cached', len(url_data.keys()))
