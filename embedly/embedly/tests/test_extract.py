import json

import requests

from embedly.extract import URLExtractor, URLExtractorException
from embedly.tests.base import MockTest


class TestExtract(MockTest):

    def setUp(self):
        super(TestExtract, self).setUp()

        self.extractor = URLExtractor('', '', self.mock_redis, 10)

        self.sample_urls = [
            'http://example.com/?this=that&things=stuff',
            'www.example.com/path/to/things/?these=those'
        ]

        self.expected_response = {
            url: self.get_mock_url_data(url)
            for url in self.sample_urls
        }

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

    def test_protocol_and_query_are_removed_from_cache_key(self):

        def mocked_lookup(url):
            return json.dumps(self.get_mock_url_data(url))

        self.mock_redis.get.side_effect = mocked_lookup

        similar_urls = [
            'https://www.google.ca/?q=hello',
            'http://www.google.ca/?q=hello',
            'http://www.google.ca/?q=goodbye',
            'http://www.google.ca/some/path/?q=derp',
            'http://www.google.ca/some/path/?q=beep',
        ]

        extracted_urls = self.extractor.extract_urls(similar_urls)

        self.assertEqual(self.mock_redis.get.call_count, 5)
        self.assertEqual(self.mock_requests_get.call_count, 0)
        self.assertEqual(len(self.mock_redis.get.call_args[0]), 1)

        called_urls = set([
            call[0][0] for call in
            self.mock_redis.get.call_args_list
        ])

        self.assertEqual(
            called_urls,
            set(['www.google.ca/', 'www.google.ca/some/path/']),
        )

        expected_response = {
            url: self.get_mock_url_data(self.extractor._get_cache_key(url))
            for url in similar_urls
        }

        self.assertEqual(extracted_urls, expected_response)
