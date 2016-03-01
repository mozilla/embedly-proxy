import json
import urllib
import urlparse

from flask import current_app
import requests


def get_cache_key(url):
    split_url = urlparse.urlsplit(url)
    return '{base}{path}'.format(base=split_url.netloc, path=split_url.path)


def get_cached_url(url):
    cache_key = get_cache_key(url)
    cached_data = current_app.redis_client.get(cache_key)

    if cached_data is not None:
        return json.loads(cached_data)


def set_cached_url(url, data):
    cache_key = get_cache_key(url)
    current_app.redis_client.set(cache_key, json.dumps(data))
    current_app.redis_client.expire(cache_key, current_app.config['REDIS_TIMEOUT'])


def build_embedly_url(urls):
    params = '&'.join([
        'key={}'.format(current_app.config['EMBEDLY_KEY']),
        'urls={}'.format(','.join([urllib.quote_plus(url) for url in urls])),
    ])

    return '{base}?{params}'.format(
        base=current_app.config['EMBEDLY_URL'],
        params=params,
    )


def get_urls_from_embedly(urls):
    request_url = build_embedly_url(urls)

    try:
        response = requests.get(request_url)
    except requests.RequestException:
        response = None

    embedly_data = []
    if response is not None:
        try:
            embedly_data = json.loads(response.content)
        except (TypeError, ValueError):
            pass

    parsed_data = {}
    if type(embedly_data) is list:
        parsed_data = {
            url_data['original_url']: url_data
            for url_data in embedly_data
        }

    return parsed_data


def extract_urls(urls):
    url_data = {}

    uncached_urls = []
    for url in urls:
        cached_url_data = get_cached_url(url)

        if cached_url_data is not None:
            url_data[url] = cached_url_data
        else:
            uncached_urls.append(url)

    if uncached_urls:
        embedly_url_data = get_urls_from_embedly(uncached_urls)

        for embedly_url, embedly_data in embedly_url_data.items():
            set_cached_url(embedly_url, embedly_data)

        url_data.update(embedly_url_data)

    return url_data
