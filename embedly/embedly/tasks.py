def get_url_data(urls):
    from embedly.app import get_extractor
    from embedly.stats import statsd_client


    extractor = get_extractor()

    url_data = extractor.extract_urls(urls, remote_fetch=True)
    print 'getting url data', url_data
