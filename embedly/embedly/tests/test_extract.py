# -*- coding: utf-8 -*-
import json

import requests

from embedly.extract import URLExtractor, URLExtractorException
from embedly.tests.base import AppTest


class ExtractorTest(AppTest):

    def setUp(self):
        super(ExtractorTest, self).setUp()

        self.extractor = URLExtractor('', '', self.mock_redis, 10, [])

        self.sample_urls = [
            'http://example.com/?this=that&things=stuff',
            u'http://www.example.com/path/to/things/?these=中',
        ]

        self.expected_response = {
            url: self.get_mock_url_data(url)
            for url in self.sample_urls
        }


class TestExtract(ExtractorTest):

    def test_multiple_urls_queried_without_caching(self):
        embedly_data = self.get_mock_urls_data(self.sample_urls)

        self.mock_requests_get.return_value = self.get_mock_response(
            content=json.dumps(embedly_data))

        extracted_urls = self.extractor.extract_urls(self.sample_urls)

        self.assertEqual(self.mock_redis.get.call_count, 2)
        self.assertEqual(self.mock_redis.set.call_count, 2)
        self.assertEqual(self.mock_requests_get.call_count, 1)

        self.assertEqual(extracted_urls, self.expected_response)

    def test_request_error_raises_exception(self):
        self.mock_requests_get.side_effect = requests.RequestException()

        with self.assertRaises(URLExtractorException):
            self.extractor.extract_urls(self.sample_urls)

    def test_invalid_json_from_embedly_raises_exception(self):
        self.mock_requests_get.return_value = self.get_mock_response(
            content='\invalid json')

        with self.assertRaises(URLExtractorException):
            self.extractor.extract_urls(self.sample_urls)

    def test_error_from_embedly_raises_exception(self):
        self.mock_requests_get.return_value = self.get_mock_response(
            status=400,
            content=json.dumps({
                'type': 'error',
                'error_message': 'error',
                'error_code': 400,
            })
        )

        with self.assertRaises(URLExtractorException):
            self.extractor.extract_urls(self.sample_urls)

    def test_invalid_json_in_cache_raises_exception(self):

        def mocked_lookup(key):
            return '\invalid json'

        self.mock_redis.get.side_effect = mocked_lookup

        with self.assertRaises(URLExtractorException):
            self.extractor.extract_urls(self.sample_urls)

    def test_multiple_urls_queried_with_partial_cache_hit(self):

        def get_mocked_cache_lookup(url, cached_data):
            def mocked_lookup(key):
                if key == self.extractor._get_cache_key(url):
                    return json.dumps(cached_data)

            return mocked_lookup

        cached_url = self.sample_urls[0]
        self.mock_redis.get.side_effect = get_mocked_cache_lookup(
            cached_url, self.get_mock_url_data(cached_url))

        uncached_urls = self.sample_urls[1:]
        embedly_data = self.get_mock_urls_data(uncached_urls)

        self.mock_requests_get.return_value = self.get_mock_response(
            content=json.dumps(embedly_data))

        extracted_urls = self.extractor.extract_urls(self.sample_urls)

        self.assertEqual(self.mock_redis.get.call_count, 2)
        self.assertEqual(self.mock_requests_get.call_count, 1)

        self.assertEqual(
            self.mock_requests_get.call_args[0][0],
            self.extractor._build_embedly_url(uncached_urls),
        )

        self.assertEqual(extracted_urls, self.expected_response)

    def test_multiple_urls_queried_with_total_cache_hit(self):

        def mocked_lookup(url):
            return json.dumps(self.get_mock_url_data(url))

        self.mock_redis.get.side_effect = mocked_lookup

        extracted_urls = self.extractor.extract_urls(self.sample_urls)

        self.assertEqual(self.mock_redis.get.call_count, 2)
        self.assertEqual(self.mock_requests_get.call_count, 0)

        expected_response = {
            url: self.get_mock_url_data(self.extractor._get_cache_key(url))
            for url in self.sample_urls
        }

        self.assertEqual(extracted_urls, expected_response)

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

        extracted_urls = self.extractor.extract_urls([
            valid_url,
            invalid_url,
        ])

        self.assertEqual(self.mock_redis.get.call_count, 2)
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

        extracted_urls = self.extractor.extract_urls([
            unmodified_url,
            original_modified_url,
        ])

        self.assertIn(unmodified_url, extracted_urls)
        self.assertNotIn(original_modified_url, extracted_urls)
        self.assertNotIn(embedly_modified_url, extracted_urls)
