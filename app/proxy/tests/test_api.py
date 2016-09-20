import json
import time

import mock
import redis
from werkzeug.exceptions import HTTPException

from proxy.api.views import get_metadata
from proxy.tests.base import AppTest
from proxy.tests.test_metadata import (
    EmbedlyClientTest, MozillaClientTest, MetadataClientTest)
from proxy.tests.test_pocket import PocketClientTest


class TestHeartbeat(AppTest):

    def test_heartbeat_returns_200_when_redis_available(self):
        response = self.client.get('/__heartbeat__')
        self.assertEqual(response.status_code, 200)

    def test_heartbeat_returns_500_when_redis_unavailable(self):
        self.mock_redis.ping.side_effect = redis.ConnectionError()
        response = self.client.get('/__heartbeat__')
        self.assertEqual(response.status_code, 500)


class TestLBHeartbeat(AppTest):

    def test_heartbeat_returns_200_when_redis_available(self):
        response = self.client.get('/__lbheartbeat__')
        self.assertEqual(response.status_code, 200)

    def test_heartbeat_returns_200_when_redis_unavailable(self):
        self.mock_redis.ping.side_effect = redis.ConnectionError()
        response = self.client.get('/__lbheartbeat__')
        self.assertEqual(response.status_code, 200)


class TestVersion(AppTest):

    def test_version_returns_git_info(self):
        self.app.config['VERSION_INFO'] = json.dumps({
            'commit': 'abc',
            'version': 'embedly-proxy-0.1',
            'source': 'https://github.com/mozilla/embedly-proxy.git'
        })

        response = self.client.get('/__version__')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, self.app.config['VERSION_INFO'])


class TestGetMetadata(MetadataClientTest):

    def get_config(self, **kwargs):
        config = {
            'MAXIMUM_POST_URLS': 10,
        }

        config.update(**kwargs)
        return config

    def get_mock_request(self, urls=[],
                         content='', content_type='application/json'):
        mock_request = mock.Mock()
        mock_request.content_type = content_type
        mock_request.json = content or {
            'urls': urls,
        }

        return mock_request

    def test_wrong_content_type_raises_400(self):
        request = self.get_mock_request(content_type='\invalid')

        with self.assertRaises(HTTPException) as cm:
            get_metadata(self.metadata_client, self.get_config(), request)

        self.assertEqual(cm.exception.response.status_code, 400)

    def test_post_body_must_be_valid_json(self):
        request = self.get_mock_request(content='\invalid json')

        with self.assertRaises(HTTPException) as cm:
            get_metadata(self.metadata_client, self.get_config(), request)

        self.assertEqual(cm.exception.response.status_code, 400)

    def test_valid_json_post_body_must_include_urls(self):
        request = self.get_mock_request(content=json.dumps({}))

        with self.assertRaises(HTTPException) as cm:
            get_metadata(self.metadata_client, self.get_config(), request)

        self.assertEqual(cm.exception.response.status_code, 400)

    def test_empty_urls_param_returns_200(self):
        request = self.get_mock_request()
        response = get_metadata(
            self.metadata_client, self.get_config(), request)

        self.assertEqual(response.status_code, 200)

        response_data = json.loads(response.data)
        self.assertEqual(response_data, {
            'urls': {},
            'error': '',
        })

    def test_urlextractorexception_returns_error(self):
        self.mock_redis.get.side_effect = redis.RedisError()
        request = self.get_mock_request(urls=self.sample_urls)

        with self.assertRaises(HTTPException) as cm:
            get_metadata(self.metadata_client, self.get_config(), request)

        self.assertEqual(cm.exception.response.status_code, 500)

    def test_rejects_calls_with_too_many_urls(self):
        config = self.get_config(MAXIMUM_POST_URLS=1)
        request = self.get_mock_request(urls=self.sample_urls)

        with self.assertRaises(HTTPException) as cm:
            get_metadata(self.metadata_client, config, request)

        self.assertEqual(cm.exception.response.status_code, 400)

    def test_rejects_calls_null_urls(self):
        request = self.get_mock_request(urls=self.sample_urls + [None])

        with self.assertRaises(HTTPException) as cm:
            get_metadata(self.metadata_client, self.get_config(), request)

        self.assertEqual(cm.exception.response.status_code, 400)

    def test_extract_returns_cached_data(self):
        cached_urls = self.sample_urls

        def fake_cache(urls):
            def mock_cache_get(cache_key):
                for url in urls:
                    if url in cache_key:
                        return json.dumps(self.get_mock_url_data(url))

            return mock_cache_get

        self.mock_redis.get.side_effect = fake_cache(cached_urls)

        request = self.get_mock_request(urls=self.sample_urls)
        response = get_metadata(
            self.metadata_client, self.get_config(), request)

        self.assertEqual(response.status_code, 200)

        self.assertEqual(self.mock_redis.get.call_count, len(self.sample_urls))
        self.assertEqual(self.mock_redis.setex.call_count, 0)
        self.assertEqual(self.mock_requests_get.call_count, 0)

        response_data = json.loads(response.data)
        self.assertEqual(response_data, {
            'urls': self.expected_response,
            'error': '',
        })


class TestEmbedlyMetadata(EmbedlyClientTest):

    def test_extract_returns_cached_data(self):
        cached_urls = self.sample_urls

        def fake_cache(urls):
            def mock_cache_get(cache_key):
                for url in urls:
                    if url in cache_key:
                        return json.dumps(self.get_mock_url_data(url))

            return mock_cache_get

        self.mock_redis.get.side_effect = fake_cache(cached_urls)

        response = self.client.post(
            '/v2/extract',
            data=json.dumps({'urls': self.sample_urls}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(self.mock_redis.get.call_count, len(self.sample_urls))
        self.assertEqual(self.mock_redis.setex.call_count, 0)
        self.assertEqual(self.mock_requests_get.call_count, 0)

        response_data = json.loads(response.data)
        self.assertEqual(response_data, {
            'urls': self.expected_response,
            'error': '',
        })

    def test_request_method_must_be_post(self):
        response = self.client.get('/v2/extract')
        self.assertEqual(response.status_code, 405)


class TestMozillaMetadata(MozillaClientTest):

    def test_extract_returns_cached_data(self):
        cached_urls = self.sample_urls

        def fake_cache(urls):
            def mock_cache_get(cache_key):
                for url in urls:
                    if url in cache_key:
                        return json.dumps(self.get_mock_url_data(url))

            return mock_cache_get

        self.mock_redis.get.side_effect = fake_cache(cached_urls)

        response = self.client.post(
            '/v2/metadata',
            data=json.dumps({'urls': self.sample_urls}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(self.mock_redis.get.call_count, len(self.sample_urls))
        self.assertEqual(self.mock_redis.setex.call_count, 0)
        self.assertEqual(self.mock_requests_get.call_count, 0)

        response_data = json.loads(response.data)
        self.assertEqual(response_data, {
            'urls': self.expected_response,
            'error': '',
        })

    def test_request_method_must_be_post(self):
        response = self.client.get('/v2/metadata')
        self.assertEqual(response.status_code, 405)


class TestPocket(PocketClientTest):

    def test_uncached_recommendations_returns_empty_queues_job(self):
        response = self.client.get('/v2/recommendations')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_redis.get.call_count, 1)
        self.assertEqual(self.mock_redis.setex.call_count, 1)
        self.assertEqual(self.mock_job_queue.enqueue.call_count, 1)

        response_data = json.loads(response.data)
        self.assertEqual(response_data, {
            'urls': [],
            'error': '',
        })

    def test_cached_recommendations_returned(self):
        recommendation_data = [{
            'url': 'http://www.example.com/recommended',
            'timestamp': time.time(),
        }, {
            'url': 'http://www.example.com/otherrecommended',
            'timestamp': time.time(),
        }]

        self.mock_redis.get.return_value = json.dumps(recommendation_data)

        response = self.client.get('/v2/recommendations')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_redis.get.call_count, 1)
        self.assertEqual(self.mock_redis.setex.call_count, 0)
        self.assertEqual(self.mock_job_queue.enqueue.call_count, 0)

        response_data = json.loads(response.data)
        self.assertEqual(response_data, {
            'urls': recommendation_data,
            'error': '',
        })

    def test_pocket_exception_returns_500(self):
        self.mock_redis.get.side_effect = redis.RedisError()

        response = self.client.get('/v2/recommendations')

        self.assertEqual(response.status_code, 500)
