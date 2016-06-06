import json
import time
import urllib

import redis
import requests

from embedly.stats import statsd_client
from embedly.tasks import fetch_remote_url_data
from embedly.schema import EmbedlyURLSchema


IN_JOB_QUEUE = 'in job queue'


def group_by(items, size):
    while items:
        yield items[:size]
        items = items[size:]


class URLExtractor(object):

    class URLExtractorException(Exception):
        pass

    def __init__(self, embedly_url, embedly_key, redis_client,
                 redis_data_timeout, redis_job_timeout, blocked_domains,
                 job_queue, job_ttl, url_batch_size):
        self.embedly_url = embedly_url
        self.embedly_key = embedly_key
        self.redis_client = redis_client
        self.redis_data_timeout = redis_data_timeout
        self.redis_job_timeout = redis_job_timeout
        self.schema = EmbedlyURLSchema(blocked_domains=blocked_domains)
        self.job_queue = job_queue
        self.job_ttl = job_ttl
        self.url_batch_size = url_batch_size

    def _get_cache_key(self, url):
        return url

    def _get_cached_url(self, url):
        cache_key = self._get_cache_key(url)

        try:
            cached_data = self.redis_client.get(cache_key)
        except redis.RedisError:
            raise self.URLExtractorException('Unable to read from redis.')

        if cached_data is not None:
            statsd_client.incr('redis_cache_hit')
            try:
                return json.loads(cached_data)
            except ValueError:
                raise self.URLExtractorException(
                    ('Unable to load JSON data '
                     'from cache for key: {key}').format(key=cache_key))
        else:
            statsd_client.incr('redis_cache_miss')

    def _set_cached_url(self, url, data, timeout):
        cache_key = self._get_cache_key(url)

        try:
            self.redis_client.set(cache_key, json.dumps(data))
            self.redis_client.expire(cache_key, timeout)
            statsd_client.incr('redis_cache_write')
        except redis.RedisError:
            raise self.URLExtractorException('Unable to write to redis.')

    def _build_embedly_url(self, urls):
        params = '&'.join([
            'key={}'.format(self.embedly_key),
            'urls={}'.format(','.join([
                urllib.quote_plus(url.encode('utf8')) for url in urls
            ])),
        ])

        return '{base}?{params}'.format(
            base=self.embedly_url,
            params=params,
        )

    def _get_urls_from_embedly(self, urls):
        statsd_client.gauge('embedly_request_url_count', len(urls))

        request_url = self._build_embedly_url(urls)

        with statsd_client.timer('embedly_request_timer'):
            try:
                response = requests.get(request_url)
            except requests.RequestException, e:
                raise self.URLExtractorException(
                    ('Unable to communicate '
                     'with embedly: {error}').format(error=e))

        if response.status_code != 200:
            statsd_client.incr('embedly_request_failure')
            raise self.URLExtractorException(
                ('Error status returned from '
                 'embedly: {error_code} {error_message}').format(
                    error_code=response.status_code,
                    error_message=response.content,
                  ))

        statsd_client.incr('embedly_request_success')

        embedly_data = []

        if response is not None:
            try:
                embedly_data = json.loads(response.content)
            except (TypeError, ValueError), e:
                statsd_client.incr('embedly_parse_failure')
                raise self.URLExtractorException(
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

    def _queue_url_jobs(self, urls):
        batched_urls = group_by(list(urls), self.url_batch_size)

        for url_batch in batched_urls:
            try:
                self.job_queue.enqueue(
                    fetch_remote_url_data,
                    url_batch,
                    time.time(),
                    ttl=self.job_ttl,
                    at_front=True,
                )
                statsd_client.gauge(
                    'request_fetch_job_create', len(url_batch))
                statsd_client.gauge(
                    'request_fetch_job_queue_size', self.job_queue.count)

                for queued_url in url_batch:
                    self._set_cached_url(
                        queued_url, IN_JOB_QUEUE, self.redis_job_timeout)

            except Exception:
                statsd_client.incr('request_fetch_job_create_fail')

    def _remove_cached_keys(self, urls):
        self.redis_client.delete(*[self._get_cache_key(url) for url in urls])

    def get_cached_urls(self, urls):
        url_data = {}

        for url in urls:
            cached_url_data = self._get_cached_url(url)

            if cached_url_data is not None:
                url_data[url] = cached_url_data

        return url_data

    def get_remote_urls(self, urls):
        self._remove_cached_keys(urls)

        embedly_urls_data = self._get_urls_from_embedly(urls)
        validated_urls_data = {}

        for embedly_url in urls:
            if embedly_url in embedly_urls_data:
                embedly_data = embedly_urls_data[embedly_url]
                validated_data = self.schema.load(embedly_data)

                if not validated_data.errors:
                    self._set_cached_url(
                        embedly_url,
                        validated_data.data,
                        self.redis_data_timeout,
                    )

                    validated_urls_data[embedly_url] = validated_data.data

        return validated_urls_data

    def extract_urls_async(self, urls):
        all_cached_url_data = self.get_cached_urls(urls)

        if IN_JOB_QUEUE in all_cached_url_data.values():
            statsd_client.incr('request_in_job_queue')

        cached_url_data = {
            url: url_data
            for (url, url_data)
            in all_cached_url_data.items()
            if url_data != IN_JOB_QUEUE
        }

        uncached_urls = set(urls) - set(all_cached_url_data.keys())

        if uncached_urls:
            self._queue_url_jobs(uncached_urls)

        return cached_url_data
