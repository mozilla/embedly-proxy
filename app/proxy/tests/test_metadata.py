# -*- coding: utf-8 -*-
import random
import json

import mock
import redis
import requests

from proxy.metadata import EmbedlyClient, MetadataClient, MozillaClient
from proxy.tests.base import AppTest


class MetadataClientTest(AppTest):

    def get_metadata_client_kwargs(self):
        return {
            'redis_client': self.mock_redis,
            'redis_data_timeout': 10,
            'redis_job_timeout': 10,
            'blocked_domains': [],
            'job_queue': self.mock_job_queue,
            'job_ttl': 10,
            'url_batch_size': self.app.config['URL_BATCH_SIZE'],
        }

    def get_metadata_client(self):
        def _make_remote_request(urls):
            mock_json = json.dumps(self.get_response_data(urls))
            return self.get_mock_response(content=mock_json)

        def _parse_remote_data(urls, remote_data):
            return self.get_response_data(urls)

        metadata_client = MetadataClient(**self.get_metadata_client_kwargs())
        metadata_client.SERVICE_NAME = 'test-service'
        metadata_client.TASK = mock.Mock()

        metadata_client._make_remote_request = mock.Mock()
        metadata_client._make_remote_request.side_effect = _make_remote_request

        metadata_client._parse_remote_data = mock.Mock()
        metadata_client._parse_remote_data.side_effect = _parse_remote_data

        return metadata_client

    def setUp(self):
        super(MetadataClientTest, self).setUp()

        self.metadata_client = self.get_metadata_client()

        self.sample_urls = [
            'http://example.com/?this=that&things=stuff',
            u'http://www.example.com/path/to/things/?these=中',
        ]

        self.expected_response = self.get_response_data(self.sample_urls)


class TestMetadataClientExtractURLsAsync(MetadataClientTest):

    def test_multiple_urls_queried_with_cache_hit_and_jobs_started(self):
        sample_urls = [
            'http://www.example.com/{}'.format(random.random())
            for i in range(self.app.config['URL_BATCH_SIZE'] * 3)
        ]

        def get_mocked_cache_lookup(url, cached_data):
            def mocked_lookup(key):
                if key == self.metadata_client._get_cache_key(url):
                    return json.dumps(cached_data)

            return mocked_lookup

        cached_url = sample_urls[0]
        self.mock_redis.get.side_effect = get_mocked_cache_lookup(
            cached_url, self.get_mock_url_data(cached_url))

        uncached_urls = sample_urls[1:]
        embedly_data = self.get_mock_urls_data(uncached_urls)

        self.mock_requests_get.return_value = self.get_mock_response(
            content=json.dumps(embedly_data))

        cached_url_data = self.metadata_client.extract_urls_async(sample_urls)

        self.assertEqual(self.mock_redis.get.call_count, len(sample_urls))
        self.assertEqual(self.mock_redis.setex.call_count, len(uncached_urls))
        self.assertEqual(self.mock_requests_get.call_count, 0)

        self.assertEqual(
            self.mock_job_queue.enqueue.call_count,
            (len(uncached_urls)/self.app.config['URL_BATCH_SIZE']) + 1,
        )

        self.assertEqual(cached_url_data, self.get_response_data([cached_url]))

    def test_url_queried_multiple_times_starts_only_one_job(self):
        mock_cache = {}

        def mock_setex(key, time, value, *args, **kwargs):
            mock_cache[key] = value

        def mock_get(key):
            return mock_cache[key] if key in mock_cache else None

        self.mock_redis.get.side_effect = mock_get
        self.mock_redis.setex.side_effect = mock_setex

        first_urls = ['http://www.example.com/1', 'http://www.example.com/2']

        cached_url_data = self.metadata_client.extract_urls_async(first_urls)

        self.assertEqual(cached_url_data, {})
        self.assertEqual(self.mock_redis.get.call_count, 2)
        self.assertEqual(self.mock_redis.setex.call_count, 2)
        self.assertEqual(self.mock_requests_get.call_count, 0)
        self.assertEqual(self.mock_job_queue.enqueue.call_count, 1)
        self.assertEqual(
            self.mock_job_queue.enqueue.call_args[0][1], first_urls)

        second_urls = ['http://www.example.com/2', 'http://www.example.com/3']

        cached_url_data = self.metadata_client.extract_urls_async(second_urls)

        self.assertEqual(cached_url_data, {})
        self.assertEqual(self.mock_redis.get.call_count, 4)
        self.assertEqual(self.mock_redis.setex.call_count, 3)
        self.assertEqual(self.mock_requests_get.call_count, 0)
        self.assertEqual(self.mock_job_queue.enqueue.call_count, 2)
        self.assertEqual(
            self.mock_job_queue.enqueue.call_args[0][1],
            ['http://www.example.com/3'],
        )


class TestMetadataClientGetCachedURLs(MetadataClientTest):

    def test_invalid_json_in_cache_raises_exception(self):

        def mocked_lookup(key):
            return '\invalid json'

        self.mock_redis.get.side_effect = mocked_lookup

        with self.assertRaises(MetadataClient.MetadataClientException):
            self.metadata_client.get_cached_urls(self.sample_urls)

    def test_redis_get_error_raises_exception(self):
        self.mock_redis.get.side_effect = redis.RedisError

        with self.assertRaises(MetadataClient.MetadataClientException):
            self.metadata_client.get_cached_urls(self.sample_urls)

    def test_multiple_urls_queried_from_cache(self):

        def get_fake_cache(urls):
            def mocked_lookup(cache_key):
                for url in urls:
                    if url in cache_key:
                        return json.dumps(self.get_mock_url_data(url))

            return mocked_lookup

        self.mock_redis.get.side_effect = get_fake_cache(self.sample_urls)

        # a url with no cache data
        missing_url = 'http://example.com/notcached'

        extracted_urls = self.metadata_client.get_cached_urls(
            self.sample_urls + [missing_url])

        self.assertEqual(self.mock_redis.get.call_count, 3)
        self.assertEqual(self.mock_redis.setex.call_count, 0)

        expected_response = {
            url: self.get_mock_url_data(url)
            for url in self.sample_urls
        }

        self.assertEqual(extracted_urls, expected_response)


class TestMetadataClientGetRemoteURLs(MetadataClientTest):

    def test_redis_get_error_raises_exception(self):
        self.mock_redis.setex.side_effect = redis.RedisError

        remote_data = self.get_mock_urls_data(self.sample_urls)

        self.metadata_client._make_remote_request.return_value = (
            self.get_mock_response(content=json.dumps(remote_data)))

        with self.assertRaises(MetadataClient.MetadataClientException):
            self.metadata_client.get_remote_urls(self.sample_urls)

        self.assertEqual(self.mock_redis.setex.call_count, 1)

    def test_invalid_json_from_remote_raises_exception(self):
        self.metadata_client._make_remote_request.side_effect = None
        self.metadata_client._make_remote_request.return_value = (
            self.get_mock_response(content='\invalid json'))

        with self.assertRaises(MetadataClient.MetadataClientException):
            self.metadata_client.get_remote_urls(self.sample_urls)

    def test_multiple_urls_queried_from_remote(self):
        remote_data = self.get_mock_urls_data(self.sample_urls)

        self.metadata_client._make_remote_request.return_value = (
            self.get_mock_response(content=json.dumps(remote_data)))

        extracted_urls = self.metadata_client.get_remote_urls(self.sample_urls)

        self.assertEqual(self.mock_redis.get.call_count, 0)
        self.assertEqual(self.mock_redis.setex.call_count, 2)

        self.assertEqual(extracted_urls, self.expected_response)

    def test_error_from_remote_raises_exception(self):
        self.metadata_client._make_remote_request.side_effect = None
        self.metadata_client._make_remote_request.return_value = (
            self.get_mock_response(
                status=400,
                content='Error',
            ))

        with self.assertRaises(MetadataClient.MetadataClientException):
            self.metadata_client.get_remote_urls(self.sample_urls)

    def test_request_error_raises_exception(self):
        self.metadata_client._make_remote_request.side_effect = (
            requests.RequestException())

        with self.assertRaises(MetadataClient.MetadataClientException):
            self.metadata_client.get_remote_urls(self.sample_urls)

    def test_task_fetches_data_and_caches(self):
        mock_cache = {}

        def mock_set(key, value, *args, **kwargs):
            mock_cache[key] = value

        def mock_get(key):
            return mock_cache[key] if key in mock_cache else None

        self.mock_redis.get.side_effect = mock_get
        self.mock_redis.setex.side_effect = mock_set

        embedly_data = self.get_mock_urls_data(self.sample_urls)

        self.metadata_client._make_remote_request.return_value = (
            self.get_mock_response(content=json.dumps(embedly_data)))

        for url in self.sample_urls:
            self.metadata_client._set_cached_url(
                url, self.metadata_client.IN_JOB_QUEUE, 0)

        extracted_urls = self.metadata_client.get_remote_urls(self.sample_urls)

        self.assertEqual(extracted_urls, self.expected_response)
        self.assertEqual(self.mock_redis.delete.call_count, 1)
        self.assertEqual(self.mock_redis.get.call_count, 0)
        self.assertEqual(
            self.mock_redis.setex.call_count, 2 * len(self.sample_urls))
        self.assertEqual(
            mock_cache.keys(),
            [self.metadata_client._get_cache_key(url)
                for url in self.sample_urls])
        self.assertNotIn(
            self.metadata_client.IN_JOB_QUEUE, mock_cache.values())

    def test_task_removes_placeholder_values_if_job_fails(self):
        existing_url = 'http://www.example.com'
        existing_url_key = self.metadata_client._get_cache_key(existing_url)
        mock_cache = {}

        def mock_set(key, value, *args, **kwargs):
            mock_cache[key] = value

        def mock_get(key):
            return mock_cache[key] if key in mock_cache else None

        def mock_delete(*args):
            for arg in args:
                del mock_cache[arg]

        self.mock_redis.get.side_effect = mock_get
        self.mock_redis.setex.side_effect = mock_set
        self.mock_redis.delete.side_effect = mock_delete
        self.metadata_client._make_remote_request.side_effect = (
            requests.RequestException)

        self.metadata_client._set_cached_url(
            existing_url, self.get_mock_url_data(existing_url), 0)

        for url in self.sample_urls:
            self.metadata_client._set_cached_url(
                url, self.metadata_client.IN_JOB_QUEUE, 0)

        with self.assertRaises(MetadataClient.MetadataClientException):
            self.metadata_client.get_remote_urls(self.sample_urls)

        self.assertEqual(self.mock_redis.delete.call_count, 1)
        self.assertEqual(self.mock_redis.get.call_count, 0)
        self.assertEqual(
            self.mock_redis.setex.call_count, len(self.sample_urls) + 1)
        self.assertEqual(mock_cache.keys(), [existing_url_key])


class EmbedlyClientTest(MetadataClientTest):

    def get_metadata_client(self):
        return EmbedlyClient(
            '',
            '',
            **self.get_metadata_client_kwargs()
        )


class TestEmbedlyClient(EmbedlyClientTest):

    def test_make_remote_embedly_call(self):
        self.mock_requests_get.return_value = self.get_mock_response(
            content=json.dumps(self.get_mock_urls_data(self.sample_urls)))

        remote_data = self.metadata_client.get_remote_urls(self.sample_urls)

        self.assertEqual(remote_data, self.expected_response)
        self.assertEqual(self.mock_requests_get.call_count, 1)

    def test_embedly_modified_urls_are_omitted_from_response(self):
        unmodified_url = 'http://www.example.com/unmodified'
        original_modified_url = 'http://example.com/modified'
        embedly_modified_url = 'http://example.com/modified?injected=content'

        embedly_data = self.get_mock_urls_data([
            unmodified_url,
            embedly_modified_url,
        ])

        self.mock_requests_get.return_value = self.get_mock_response(
            content=json.dumps(embedly_data))

        extracted_urls = self.metadata_client.get_remote_urls([
            unmodified_url,
            original_modified_url,
        ])

        self.assertIn(unmodified_url, extracted_urls)
        self.assertNotIn(original_modified_url, extracted_urls)
        self.assertNotIn(embedly_modified_url, extracted_urls)


class MozillaClientTest(MetadataClientTest):

    def get_metadata_client(self):
        return MozillaClient(
            '',
            **self.get_metadata_client_kwargs()
        )

    def get_mock_urls_data(self, urls):
        return {
            'urls': {
                url: self.get_mock_url_data(url) for url in urls
            }
        }


class TestMozillaClient(MozillaClientTest):

    def test_make_remote_mozilla_call(self):
        self.mock_requests_post.return_value = self.get_mock_response(
            content=json.dumps(self.get_mock_urls_data(self.sample_urls)))

        remote_data = self.metadata_client.get_remote_urls(self.sample_urls)

        self.assertEqual(remote_data, self.expected_response)
        self.assertEqual(self.mock_requests_post.call_count, 1)

    def test_mozilla_modified_urls_are_omitted_from_response(self):
        unmodified_url = 'http://www.example.com/unmodified'
        original_modified_url = 'http://example.com/modified'
        mozilla_modified_url = 'http://example.com/modified?injected=content'

        mozilla_data = self.get_mock_urls_data([
            unmodified_url,
            mozilla_modified_url,
        ])

        self.mock_requests_post.return_value = self.get_mock_response(
            content=json.dumps(mozilla_data))

        extracted_urls = self.metadata_client.get_remote_urls([
            unmodified_url,
            original_modified_url,
        ])

        self.assertIn(unmodified_url, extracted_urls)
        self.assertNotIn(original_modified_url, extracted_urls)
        self.assertNotIn(mozilla_modified_url, extracted_urls)
