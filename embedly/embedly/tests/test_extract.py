# -*- coding: utf-8 -*-
import random
import json

import redis
import requests

from embedly.extract import URLExtractor
from embedly.tests.base import AppTest


class ExtractorTest(AppTest):

    def get_response_data(self, urls):
        return {
            url: self.get_mock_url_data(url)
            for url in urls
        }

    def setUp(self):
        super(ExtractorTest, self).setUp()

        self.extractor = URLExtractor(
            '',
            '',
            self.mock_redis,
            10,
            10,
            [],
            10,
            self.app.config['URL_BATCH_SIZE'],
        )

        self.sample_urls = [
            'http://example.com/?this=that&things=stuff',
            u'http://www.example.com/path/to/things/?these=中',
        ]

        self.expected_response = self.get_response_data(self.sample_urls)


class TestExtractorExtractURLsAsync(ExtractorTest):

    def test_multiple_urls_queried_with_cache_hit_and_jobs_started(self):
        sample_urls = [
            'http://www.example.com/{}'.format(random.random())
            for i in range(self.app.config['URL_BATCH_SIZE'] * 3)
        ]

        def get_mocked_cache_lookup(url, cached_data):
            def mocked_lookup(key):
                if key == self.extractor._get_cache_key(url):
                    return json.dumps(cached_data)

            return mocked_lookup

        cached_url = sample_urls[0]
        self.mock_redis.get.side_effect = get_mocked_cache_lookup(
            cached_url, self.get_mock_url_data(cached_url))

        uncached_urls = sample_urls[1:]
        embedly_data = self.get_mock_urls_data(uncached_urls)

        self.mock_requests_get.return_value = self.get_mock_response(
            content=json.dumps(embedly_data))

        cached_url_data = self.extractor.extract_urls_async(sample_urls)

        self.assertEqual(self.mock_redis.get.call_count, len(sample_urls))
        self.assertEqual(self.mock_redis.set.call_count, len(uncached_urls))
        self.assertEqual(self.mock_requests_get.call_count, 0)

        self.assertEqual(
            self.mock_fetch_task.delay.call_count,
            (len(uncached_urls)/self.app.config['URL_BATCH_SIZE']) + 1,
        )

        self.assertEqual(cached_url_data, self.get_response_data([cached_url]))

    def test_url_queried_multiple_times_starts_only_one_job(self):
        mock_cache = {}

        def mock_set(key, value, *args, **kwargs):
            mock_cache[key] = value

        def mock_get(key):
            return mock_cache[key] if key in mock_cache else None

        self.mock_redis.get.side_effect = mock_get
        self.mock_redis.set.side_effect = mock_set

        first_urls = ['http://www.example.com/1', 'http://www.example.com/2']

        cached_url_data = self.extractor.extract_urls_async(first_urls)

        self.assertEqual(cached_url_data, {})
        self.assertEqual(self.mock_redis.get.call_count, 2)
        self.assertEqual(self.mock_redis.set.call_count, 2)
        self.assertEqual(self.mock_requests_get.call_count, 0)
        self.assertEqual(self.mock_fetch_task.delay.call_count, 1)
        self.assertEqual(
            self.mock_fetch_task.delay.call_args[0][0], first_urls)

        second_urls = ['http://www.example.com/2', 'http://www.example.com/3']

        cached_url_data = self.extractor.extract_urls_async(second_urls)

        self.assertEqual(cached_url_data, {})
        self.assertEqual(self.mock_redis.get.call_count, 4)
        self.assertEqual(self.mock_redis.set.call_count, 3)
        self.assertEqual(self.mock_requests_get.call_count, 0)
        self.assertEqual(self.mock_fetch_task.delay.call_count, 2)
        self.assertEqual(
            self.mock_fetch_task.delay.call_args[0][0],
            ['http://www.example.com/3'],
        )


class TestExtractorGetCachedURLs(ExtractorTest):

    def test_invalid_json_in_cache_raises_exception(self):

        def mocked_lookup(key):
            return '\invalid json'

        self.mock_redis.get.side_effect = mocked_lookup

        with self.assertRaises(URLExtractor.URLExtractorException):
            self.extractor.get_cached_urls(self.sample_urls)

    def test_redis_get_error_raises_exception(self):
        self.mock_redis.get.side_effect = redis.RedisError

        with self.assertRaises(URLExtractor.URLExtractorException):
            self.extractor.get_cached_urls(self.sample_urls)

    def test_multiple_urls_queried_from_cache(self):

        def get_fake_cache(urls):
            def mocked_lookup(url):
                if url in urls:
                    return json.dumps(self.get_mock_url_data(url))

            return mocked_lookup

        self.mock_redis.get.side_effect = get_fake_cache(self.sample_urls)

        # a url with no cache data
        missing_url = 'http://example.com/notcached'

        extracted_urls = self.extractor.get_cached_urls(
            self.sample_urls + [missing_url])

        self.assertEqual(self.mock_redis.get.call_count, 3)
        self.assertEqual(self.mock_redis.set.call_count, 0)
        self.assertEqual(self.mock_requests_get.call_count, 0)

        expected_response = {
            url: self.get_mock_url_data(self.extractor._get_cache_key(url))
            for url in self.sample_urls
        }

        self.assertEqual(extracted_urls, expected_response)


class TestExtractorGetRemoteURLs(ExtractorTest):

    def test_multiple_urls_queried_from_embedly(self):
        embedly_data = self.get_mock_urls_data(self.sample_urls)

        self.mock_requests_get.return_value = self.get_mock_response(
            content=json.dumps(embedly_data))

        extracted_urls = self.extractor.get_remote_urls(self.sample_urls)

        self.assertEqual(self.mock_redis.get.call_count, 0)
        self.assertEqual(self.mock_redis.set.call_count, 2)
        self.assertEqual(self.mock_requests_get.call_count, 1)

        self.assertEqual(extracted_urls, self.expected_response)

    def test_redis_get_error_raises_exception(self):
        self.mock_redis.set.side_effect = redis.RedisError

        embedly_data = self.get_mock_urls_data(self.sample_urls)

        self.mock_requests_get.return_value = self.get_mock_response(
            content=json.dumps(embedly_data))

        with self.assertRaises(URLExtractor.URLExtractorException):
            self.extractor.get_remote_urls(self.sample_urls)

        self.assertEqual(self.mock_requests_get.call_count, 1)
        self.assertEqual(self.mock_redis.set.call_count, 1)

    def test_request_error_raises_exception(self):
        self.mock_requests_get.side_effect = requests.RequestException()

        with self.assertRaises(URLExtractor.URLExtractorException):
            self.extractor.get_remote_urls(self.sample_urls)

    def test_invalid_json_from_embedly_raises_exception(self):
        self.mock_requests_get.return_value = self.get_mock_response(
            content='\invalid json')

        with self.assertRaises(URLExtractor.URLExtractorException):
            self.extractor.get_remote_urls(self.sample_urls)

    def test_error_from_embedly_raises_exception(self):
        self.mock_requests_get.return_value = self.get_mock_response(
            status=400,
            content=json.dumps({
                'type': 'error',
                'error_message': 'error',
                'error_code': 400,
            })
        )

        with self.assertRaises(URLExtractor.URLExtractorException):
            self.extractor.get_remote_urls(self.sample_urls)

    def test_invalid_data_not_included_in_results(self):
        valid_url = 'https://example.com/valid'
        valid_url_data = self.get_mock_url_data(valid_url)

        invalid_url = 'https://example.com/invalid'
        invalid_url_data = self.get_mock_url_data(invalid_url)
        invalid_url_data['cache_age'] = 'invalid integer'

        embedly_data = [
            valid_url_data,
            invalid_url_data,
        ]

        self.mock_requests_get.return_value = self.get_mock_response(
            content=json.dumps(embedly_data))

        extracted_urls = self.extractor.get_remote_urls([
            valid_url,
            invalid_url,
        ])

        self.assertEqual(self.mock_redis.get.call_count, 0)
        self.assertEqual(self.mock_redis.set.call_count, 1)
        self.assertEqual(self.mock_requests_get.call_count, 1)

        self.assertIn(valid_url, extracted_urls)
        self.assertNotIn(invalid_url, extracted_urls)

        self.assertEqual(extracted_urls, {
            valid_url: valid_url_data,
        })

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

        extracted_urls = self.extractor.get_remote_urls([
            unmodified_url,
            original_modified_url,
        ])

        self.assertIn(unmodified_url, extracted_urls)
        self.assertNotIn(original_modified_url, extracted_urls)
        self.assertNotIn(embedly_modified_url, extracted_urls)
