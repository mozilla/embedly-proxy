import json
import urllib

import requests

from schema import EmbedlyURLSchema


class URLExtractorException(Exception):
    pass


class URLExtractor(object):

    def __init__(self, embedly_url, embedly_key, redis_client, redis_timeout):
        self.embedly_url = embedly_url
        self.embedly_key = embedly_key
        self.redis_client = redis_client
        self.redis_timeout = redis_timeout
        self.schema = EmbedlyURLSchema()

    def _get_cache_key(self, url):
        return url

    def _get_cached_url(self, url):
        cache_key = self._get_cache_key(url)
        cached_data = self.redis_client.get(cache_key)

        if cached_data is not None:
            try:
                return json.loads(cached_data)
            except ValueError:
                raise URLExtractorException(
                    ('Unable to load JSON data '
                     'from cache for key: {key}').format(key=cache_key))

    def _set_cached_url(self, url, data):
        cache_key = self._get_cache_key(url)
        self.redis_client.set(cache_key, json.dumps(data))
        self.redis_client.expire(cache_key, self.redis_timeout)

    def _build_embedly_url(self, urls):
        params = '&'.join([
            'key={}'.format(self.embedly_key),
            'urls={}'.format(','.join([
                urllib.quote_plus(url) for url in urls
            ])),
        ])

        return '{base}?{params}'.format(
            base=self.embedly_url,
            params=params,
        )

    def _get_urls_from_embedly(self, urls):
        request_url = self._build_embedly_url(urls)

        try:
            response = requests.get(request_url)
        except requests.RequestException, e:
            raise URLExtractorException(
                ('Unable to communicate '
                 'with embedly: {error}').format(error=e))

        if response.status_code != 200:
            raise URLExtractorException(
                ('Error status returned from '
                 'embedly: {error}').format(error=response.status_code))

        embedly_data = []

        if response is not None:
            try:
                embedly_data = json.loads(response.content)
            except (TypeError, ValueError), e:
                raise URLExtractorException(
                    ('Unable to parse the JSON '
                     'response from embedly: {error}').format(error=e))

        parsed_data = {}

        if type(embedly_data) is list:
            parsed_data = {
                url_data['original_url']: url_data
                for url_data in embedly_data
                if url_data['original_url'] in urls
            }

        return parsed_data

    def extract_urls(self, urls):
        url_data = {}

        uncached_urls = []
        for url in urls:
            cached_url_data = self._get_cached_url(url)

            if cached_url_data is not None:
                url_data[url] = cached_url_data
            else:
                uncached_urls.append(url)

        if uncached_urls:
            embedly_url_data = self._get_urls_from_embedly(uncached_urls)
            validated_url_data = {}

            for embedly_url, embedly_data in embedly_url_data.items():
                validated_data = self.schema.load(embedly_data)

                if not validated_data.errors:
                    self._set_cached_url(embedly_url, validated_data.data)
                    validated_url_data[embedly_url] = validated_data.data

            url_data.update(validated_url_data)

        return url_data
