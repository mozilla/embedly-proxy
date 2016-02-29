import json
import unittest
import urllib

import requests
import mock

import embedly


class TestEmbedlyProxy(unittest.TestCase):

    def _get_url_data(self, url):
        return {
            'original_url': url,
        }

    def _get_urls_data(self, urls):
        return [self._get_url_data(url) for url in urls]

    def _build_query_url(self, urls):
        quoted_urls = [urllib.quote_plus(url) for url in urls]
        query_params = '&'.join(['urls={}'.format(url) for url in quoted_urls])
        return '/extract?{params}'.format(params=query_params)

    def setUp(self):
        self.app = embedly.app
        self.app.config['DEBUG'] = True
        self.app.config['TESTING'] = True

        self.client = self.app.test_client()

        mock_requests_get_patcher = mock.patch('embedly.requests.get')
        self.mock_requests_get = mock_requests_get_patcher.start()
        self.addCleanup(mock_requests_get_patcher.stop)

        mock_redis_patcher = mock.patch('embedly.redis_client')
        self.mock_redis = mock_redis_patcher.start()
        self.mock_redis.get.return_value = None
        self.mock_redis.set.return_value = None
        self.addCleanup(mock_redis_patcher.stop)

        self.sample_urls = [
            'http://example.com/?this=that&things=stuff',
            'www.example.com/path/to/things/?these=those'
        ]

        self.expected_response = {
            url: self._get_url_data(url)
            for url in self.sample_urls
        }

    def test_empty_query_returns_200(self):
        response = self.client.get('/extract')
        self.assertEqual(response.status_code, 200)

        response_data = json.loads(response.data)
        self.assertEqual(response_data, {})

    def test_empty_get_param_returns_200(self):
        response = self.client.get('/extract?urls=')
        self.assertEqual(response.status_code, 200)

        response_data = json.loads(response.data)
        self.assertEqual(response_data, {})

    def test_multiple_urls_queried_without_caching(self):
        embedly_data = self._get_urls_data(self.sample_urls)

        mock_response = mock.Mock()
        mock_response.content = json.dumps(embedly_data)
        self.mock_requests_get.return_value = mock_response

        response = self.client.get(self._build_query_url(self.sample_urls))

        self.assertEqual(response.status_code, 200)

        self.assertEqual(self.mock_redis.get.call_count, 2)
        self.assertEqual(self.mock_requests_get.call_count, 1)
        self.assertEqual(
            self.mock_requests_get.call_args[0][0],
            embedly.build_embedly_url(self.sample_urls),
        )

        response_data = json.loads(response.data)
        self.assertEqual(response_data, self.expected_response)

    def test_request_error_returns_empty_dict(self):
        self.mock_requests_get.side_effect = requests.RequestException()

        response = self.client.get(self._build_query_url(self.sample_urls))

        self.assertEqual(response.status_code, 200)

        response_data = json.loads(response.data)
        self.assertEqual(response_data, {})

    def test_invalid_json_from_embedly_returns_empty_dict(self):
        mock_response = mock.Mock()
        mock_response.content = '\invalid json'
        self.mock_requests_get.return_value = mock_response

        response = self.client.get(self._build_query_url(self.sample_urls))

        self.assertEqual(response.status_code, 200)

        self.assertEqual(self.mock_redis.get.call_count, 2)
        self.assertEqual(self.mock_requests_get.call_count, 1)

        response_data = json.loads(response.data)
        self.assertEqual(response_data, {})

    def test_error_from_embedly_returns_empty_dict(self):
        mock_response = mock.Mock()
        mock_response.content = json.dumps({
            'type': 'error',
            'error_message': 'error',
            'error_code': 400,
        })
        self.mock_requests_get.return_value = mock_response

        response = self.client.get(self._build_query_url(self.sample_urls))

        self.assertEqual(response.status_code, 200)

        self.assertEqual(self.mock_redis.get.call_count, 2)
        self.assertEqual(self.mock_requests_get.call_count, 1)

        response_data = json.loads(response.data)
        self.assertEqual(response_data, {})

    def test_multiple_urls_queried_with_partial_cache_hit(self):

        def get_mocked_cache_lookup(url, cached_data):
            def mocked_lookup(key):
                if key == embedly.get_cache_key(url):
                    return json.dumps(cached_data)

            return mocked_lookup

        cached_url = self.sample_urls[0]
        self.mock_redis.get.side_effect = get_mocked_cache_lookup(
            cached_url, self._get_url_data(cached_url))

        uncached_urls = self.sample_urls[1:]
        embedly_data = self._get_urls_data(uncached_urls)

        mock_response = mock.Mock()
        mock_response.content = json.dumps(embedly_data)
        self.mock_requests_get.return_value = mock_response

        response = self.client.get(self._build_query_url(self.sample_urls))

        self.assertEqual(response.status_code, 200)

        self.assertEqual(self.mock_redis.get.call_count, 2)
        self.assertEqual(self.mock_requests_get.call_count, 1)
        self.assertEqual(
            self.mock_requests_get.call_args[0][0],
            embedly.build_embedly_url(uncached_urls),
        )

        response_data = json.loads(response.data)

        self.assertEqual(response_data, self.expected_response)

    def test_multiple_urls_queried_with_total_cache_hit(self):

        def mocked_lookup(url):
            return json.dumps(self._get_url_data(url))

        self.mock_redis.get.side_effect = mocked_lookup

        response = self.client.get(self._build_query_url(self.sample_urls))

        self.assertEqual(response.status_code, 200)

        self.assertEqual(self.mock_redis.get.call_count, 2)
        self.assertEqual(self.mock_requests_get.call_count, 0)

        response_data = json.loads(response.data)

        expected_response = {
            url: self._get_url_data(embedly.get_cache_key(url))
            for url in self.sample_urls
        }
        self.assertEqual(response_data, expected_response)

    def test_protocol_and_query_are_removed_from_cache_key(self):

        def mocked_lookup(url):
            return json.dumps(self._get_url_data(url))

        self.mock_redis.get.side_effect = mocked_lookup

        similar_urls = [
            'https://www.google.ca/?q=hello',
            'http://www.google.ca/?q=hello',
            'http://www.google.ca/?q=goodbye',
            'http://www.google.ca/some/path/?q=derp',
            'http://www.google.ca/some/path/?q=beep',
        ]

        response = self.client.get(self._build_query_url(similar_urls))

        self.assertEqual(response.status_code, 200)

        self.assertEqual(self.mock_redis.get.call_count, 5)
        self.assertEqual(self.mock_requests_get.call_count, 0)
        self.assertEqual(len(self.mock_redis.get.call_args[0]), 1)
        self.assertEqual(
            set([call[0][0] for call in self.mock_redis.get.call_args_list]),
            set(['www.google.ca/', 'www.google.ca/some/path/']),
        )

        response_data = json.loads(response.data)

        expected_response = {
            url: self._get_url_data(embedly.get_cache_key(url))
            for url in similar_urls
        }

        self.assertEqual(response_data, expected_response)


if __name__ == '__main__':
    unittest.main()
