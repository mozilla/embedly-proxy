def fetch_embedly_data(urls, start_time, redis_client=None):
    import time
    from proxy.app import get_embedly_client
    from proxy.stats import statsd_client

    statsd_client.incr('task_fetch_url_start')

    embedly_client = get_embedly_client(redis_client=redis_client)

    url_data = embedly_client.get_remote_urls(urls)

    statsd_client.gauge('task_fetch_url_cached', len(url_data.keys()))

    job_time = int((time.time() - start_time) * 1000)
    statsd_client.timing('task_fetch_url_time', job_time)


def fetch_mozilla_data(urls, start_time, redis_client=None):
    import time
    from proxy.app import get_mozilla_client
    from proxy.stats import statsd_client

    statsd_client.incr('task_fetch_mozilla_start')

    mozilla_client = get_mozilla_client(redis_client=redis_client)

    url_data = mozilla_client.get_remote_urls(urls)

    statsd_client.gauge('task_fetch_mozilla_cached', len(url_data.keys()))

    job_time = int((time.time() - start_time) * 1000)
    statsd_client.timing('task_fetch_mozilla_time', job_time)


def fetch_recommended_urls(start_time, redis_client=None):
    import time
    from proxy.app import get_pocket_client
    from proxy.stats import statsd_client

    statsd_client.incr('task_fetch_recommended_start')

    pocket_client = get_pocket_client(redis_client=redis_client)

    pocket_client.fetch_recommended_urls()

    job_time = int((time.time() - start_time) * 1000)
    statsd_client.timing('task_fetch_recommended_time', job_time)
