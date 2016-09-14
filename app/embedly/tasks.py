def fetch_remote_url_data(urls, start_time, redis_client=None):
    import time
    from embedly.app import get_extractor
    from embedly.stats import statsd_client

    statsd_client.incr('task_fetch_url_start')

    extractor = get_extractor(redis_client=redis_client)

    url_data = extractor.get_remote_urls(urls)

    statsd_client.gauge('task_fetch_url_cached', len(url_data.keys()))

    job_time = int((time.time() - start_time) * 1000)
    statsd_client.timing('task_fetch_url_time', job_time)


def fetch_recommended_urls(start_time, redis_client=None):
    import time
    from embedly.app import get_pocket_client
    from embedly.stats import statsd_client

    statsd_client.incr('task_fetch_recommended_start')

    pocket_client = get_pocket_client(redis_client=redis_client)

    pocket_client.fetch_recommended_urls()

    job_time = int((time.time() - start_time) * 1000)
    statsd_client.timing('task_fetch_recommended_time', job_time)
