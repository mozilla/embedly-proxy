import json

import redis
import requests

from embedly.tests.base import AppTest
from embedly.tests.test_extract import ExtractorTest


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


class TestExtractV2(ExtractorTest):

    def test_request_method_must_be_post(self):
        response = self.client.get('/v2/extract')
        self.assertEqual(response.status_code, 405)

    def test_content_type_must_be_application_json(self):
        response = self.client.post('/v2/extract')
        self.assertEqual(response.status_code, 400)

    def test_post_body_must_be_valid_json(self):
        response = self.client.post(
            '/v2/extract',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_valid_json_post_body_must_include_urls(self):
        response = self.client.post(
            '/v2/extract',
            data=json.dumps({}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)

    def test_empty_urls_param_returns_200(self):
        response = self.client.post(
            '/v2/extract',
            data=json.dumps({'urls': []}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)

        response_data = json.loads(response.data)
        self.assertEqual(response_data, {
            'urls': {},
            'error': '',
        })

    def test_urlextractorexception_returns_error(self):
        self.mock_requests_get.side_effect = requests.RequestException()

        response = self.client.post(
            '/v2/extract',
            data=json.dumps({'urls': self.sample_urls}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 500)

    def test_rejects_calls_with_too_many_urls(self):
        self.app.config['MAXIMUM_POST_URLS'] = 1

        response = self.client.post(
            '/v2/extract',
            data=json.dumps({'urls': self.sample_urls}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)

    def test_extract_returns_embedly_data(self):
        embedly_data = self.get_mock_urls_data(self.sample_urls)

        self.mock_requests_get.return_value = self.get_mock_response(
            content=json.dumps(embedly_data))

        response = self.client.post(
            '/v2/extract',
            data=json.dumps({'urls': self.sample_urls}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)

        response_data = json.loads(response.data)
        self.assertEqual(response_data, {
            'urls': self.expected_response,
            'error': '',
        })
