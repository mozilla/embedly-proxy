import json
import time
import urllib
import urlparse

import redis
import requests
import rratelimit

from proxy.stats import statsd_client
from proxy.tasks import fetch_embedly_data, fetch_mozilla_data
from proxy.schema import EmbedlyURLSchema


def group_by(items, size):
    while items:
        yield items[:size]
        items = items[size:]


class MetadataClient(object):
    IN_JOB_QUEUE = 'in job queue'

    class MetadataClientException(Exception):
        pass

    def __init__(self, redis_client, redis_data_timeout, redis_job_timeout,
                 blocked_domains, job_queue, job_ttl, url_batch_size):
        self.redis_client = redis_client
        self.redis_data_timeout = redis_data_timeout
        self.redis_job_timeout = redis_job_timeout
        self.schema = EmbedlyURLSchema(blocked_domains=blocked_domains)
        self.job_queue = job_queue
        self.job_ttl = job_ttl
        self.url_batch_size = url_batch_size
        self.domain_limiter = rratelimit.SimpleLimiter(
            redis=self.redis_client,
            action='domain_limit',
            limit=10,
            period=1,
        )

    def _get_cache_key(self, url):
        return u'{service}:{url}'.format(service=self.SERVICE_NAME, url=url)

    def _get_cached_url(self, url):
        cache_key = self._get_cache_key(url)

        try:
            cached_data = self.redis_client.get(cache_key)
        except redis.RedisError:
            raise self.MetadataClientException('Unable to read from redis.')

        if cached_data is not None:
            statsd_client.incr('redis_cache_hit')
            try:
                return json.loads(cached_data)
            except ValueError:
                raise self.MetadataClientException(
                    ('Unable to load JSON data '
                     'from cache for key: {key}').format(key=cache_key))
        else:
            statsd_client.incr('redis_cache_miss')

    def _set_cached_url(self, url, data, timeout):
        cache_key = self._get_cache_key(url)

        try:
            self.redis_client.setex(cache_key, timeout, json.dumps(data))
            statsd_client.incr('redis_cache_write')
        except redis.RedisError:
            raise self.MetadataClientException('Unable to write to redis.')

    def _queue_url_jobs(self, urls):
        batched_urls = group_by(list(urls), self.url_batch_size)

        for url_batch in batched_urls:
            try:
                self.job_queue.enqueue(
                    self.TASK,
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
                        queued_url, self.IN_JOB_QUEUE, self.redis_job_timeout)

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

    def _make_remote_request(self, urls):
        raise NotImplementedError

    def _parse_remote_data(self, remote_data):
        raise NotImplementedError

    def _get_remote_urls_data(self, urls):
        statsd_client.gauge('{service}_request_url_count'.format(
            service=self.SERVICE_NAME), len(urls))

        with statsd_client.timer('{service}_request_timer'.format(
                                 service=self.SERVICE_NAME)):
            try:
                response = self._make_remote_request(urls)
            except requests.RequestException, e:
                raise self.MetadataClientException(
                    ('Unable to communicate '
                     'with {service}: {error}').format(
                         service=self.SERVICE_NAME, error=e))

        if response.status_code != 200:
            statsd_client.incr('{service}_request_failure'.format(
                service=self.SERVICE_NAME))
            raise self.MetadataClientException(
                ('Error status returned from '
                 '{service}: {error_code} {error_message}').format(
                    service=self.SERVICE_NAME,
                    error_code=response.status_code,
                    error_message=response.content,
                  ))

        statsd_client.incr('{service}_request_success'.format(
            service=self.SERVICE_NAME))

        remote_data = []

        if response is not None:
            try:
                remote_data = json.loads(response.content)
            except (TypeError, ValueError), e:
                statsd_client.incr('{service}_parse_failure'.format(
                    service=self.SERVICE_NAME))
                raise self.MetadataClientException(
                    ('Unable to parse the JSON '
                     'response from {service}: {error}').format(
                         service=self.SERVICE_NAME, error=e))

        return self._parse_remote_data(urls, remote_data)

    def _domain_limit_urls(self, urls):
        allowed_urls = []

        for url in urls:
            domain = urlparse.urlparse(url).netloc
            if self.domain_limiter.checked_insert(domain):
                allowed_urls.append(url)
            else:
                statsd_client.incr('domain_rate_limit_exceeded')

        return allowed_urls

    def get_remote_urls(self, urls):
        self._remove_cached_keys(urls)

        remote_urls_data = self._get_remote_urls_data(urls)
        validated_urls_data = {}

        for original_url in urls:
            if original_url in remote_urls_data:
                remote_data = remote_urls_data[original_url]
                validated_data = self.schema.load(remote_data)

                if not validated_data.errors:
                    self._set_cached_url(
                        original_url,
                        validated_data.data,
                        self.redis_data_timeout,
                    )

                    validated_urls_data[original_url] = validated_data.data

        return validated_urls_data

    def extract_urls_async(self, urls):
        all_cached_url_data = self.get_cached_urls(urls)

        if self.IN_JOB_QUEUE in all_cached_url_data.values():
            statsd_client.incr('request_in_job_queue')

        cached_url_data = {
            url: url_data
            for (url, url_data)
            in all_cached_url_data.items()
            if url_data != self.IN_JOB_QUEUE
        }

        uncached_urls = set(urls) - set(all_cached_url_data.keys())

        if uncached_urls:
            allowed_urls = self._domain_limit_urls(uncached_urls)
            self._queue_url_jobs(allowed_urls)

        return cached_url_data


class EmbedlyClient(MetadataClient):
    SERVICE_NAME = 'embedly'
    TASK = staticmethod(fetch_embedly_data)

    def __init__(self, embedly_url, embedly_key, *args, **kwargs):
        self.embedly_url = embedly_url
        self.embedly_key = embedly_key
        super(EmbedlyClient, self).__init__(*args, **kwargs)

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

    def _make_remote_request(self, urls):
        return requests.get(self._build_embedly_url(urls))

    def _parse_remote_data(self, urls, remote_data):
        return {
            url_data['original_url']: url_data
            for url_data in remote_data
            if url_data['original_url'] in urls
        }


class MozillaClient(MetadataClient):
    SERVICE_NAME = 'mozilla'
    TASK = staticmethod(fetch_mozilla_data)

    def __init__(self, mozilla_url, *args, **kwargs):
        self.mozilla_url = mozilla_url
        super(MozillaClient, self).__init__(*args, **kwargs)

    def _make_remote_request(self, urls):
        return requests.post(
            self.mozilla_url,
            headers={'content-type': 'application/json'},
            json={'urls': urls},
        )

    def _parse_remote_data(self, urls, remote_data):
        return {
            url_data['original_url']: url_data
            for url_data in remote_data['urls'].values()
            if url_data['original_url'] in urls
        }
