import copy
from unittest import TestCase

import mock

from proxy.app import create_app


EMBEDLY_TEST_DATA = {
    'description': 'Example web site',
    'favicon_url': 'https://www.example.com/favicon.ico',
    'images': [{
        'entropy': 0.1,
        'height': 100,
        'size': 12345,
        'url': 'https://www.example.com/image.jpg',
        'width': 100,
    }],
    'original_url': 'http://www.example.com',
    'provider_display': 'www.example.com',
    'provider_name': 'Reddit',
    'provider_url': 'https://www.example.com',
    'title': 'Example web site',
    'type': 'html',
    'url': 'https://www.example.com/'
}


class AppTest(TestCase):

    def setUp(self):
        super(AppTest, self).setUp()

        mock_requests_get_patcher = mock.patch(
            'proxy.metadata.requests.get')
        self.mock_requests_get = mock_requests_get_patcher.start()
        self.addCleanup(mock_requests_get_patcher.stop)

        self.mock_redis = mock.Mock()
        self.mock_redis.get.return_value = None
        self.mock_redis.setex.return_value = None

        self.mock_job_queue = mock.Mock()

        self.app = create_app(
            redis_client=self.mock_redis, job_queue=self.mock_job_queue)
        self.app.config['DEBUG'] = True
        self.app.config['TESTING'] = True

        self.client = self.app.test_client()

        self.test_data = copy.copy(EMBEDLY_TEST_DATA)

    def get_mock_url_data(self, url):
        embedly_data = copy.copy(EMBEDLY_TEST_DATA)
        embedly_data['original_url'] = url
        return embedly_data

    def get_mock_urls_data(self, urls):
        return [self.get_mock_url_data(url) for url in urls]

    def get_mock_response(self, status=200, content='{}'):
        mock_response = mock.Mock()
        mock_response.status_code = status
        mock_response.content = content

        return mock_response
