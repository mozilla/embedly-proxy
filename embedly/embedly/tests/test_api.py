import json

import redis
import mock

from embedly.app import create_app
from embedly.tests.base import ExtractTest


class APITest(ExtractTest):

    def setUp(self):
        super(APITest, self).setUp()

        self.app = create_app(redis_client=self.mock_redis)
        self.app.config['DEBUG'] = True
        self.app.config['TESTING'] = True

        self.client = self.app.test_client()


class TestHeartbeat(APITest):

    def test_heartbeat_returns_200_when_redis_available(self):
        response = self.client.get('/__heartbeat__')
        self.assertEqual(response.status_code, 200)

    def test_heartbeat_returns_500_when_redis_unavailable(self):
        self.mock_redis.ping.side_effect = redis.ConnectionError()
        response = self.client.get('/__heartbeat__')
        self.assertEqual(response.status_code, 500)


class TestLBHeartbeat(APITest):

    def test_heartbeat_returns_200_when_redis_available(self):
        response = self.client.get('/__lbheartbeat__')
        self.assertEqual(response.status_code, 200)

    def test_heartbeat_returns_200_when_redis_unavailable(self):
        self.mock_redis.ping.side_effect = redis.ConnectionError()
        response = self.client.get('/__lbheartbeat__')
        self.assertEqual(response.status_code, 200)


class TestVersion(APITest):

    def test_version_returns_git_info(self):
        self.app.config['VERSION_INFO'] = json.dumps({
            'commit': 'abc',
            'version': 'embedly-proxy-0.1',
            'source': 'https://github.com/mozilla/embedly-proxy.git'
        })

        response = self.client.get('/__version__')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, self.app.config['VERSION_INFO'])


class TestExtract(APITest):

    def setUp(self):
        super(TestExtract, self).setUp()

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

    def test_extract_returns_embedly_data(self):
        embedly_data = self._get_urls_data(self.sample_urls)

        mock_response = mock.Mock()
        mock_response.content = json.dumps(embedly_data)
        self.mock_requests_get.return_value = mock_response

        response = self.client.get(self._build_query_url(self.sample_urls))

        self.assertEqual(response.status_code, 200)

        response_data = json.loads(response.data)
        self.assertEqual(response_data, self.expected_response)