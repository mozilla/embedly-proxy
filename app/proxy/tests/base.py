import copy
from unittest import TestCase

import mock

from proxy.app import create_app


TEST_METADATA = {
    'description': 'Example web site',
    'favicon_url': 'https://www.example.com/favicon.ico',
    'images': [{
        'height': 100,
        'url': 'https://www.example.com/image.jpg',
        'width': 100,
    }],
    'original_url': 'http://www.example.com',
    'provider_name': 'Reddit',
    'title': 'Example web site',
    'url': 'https://www.example.com/'
}


class AppTest(TestCase):

    def setUp(self):
        super(AppTest, self).setUp()

        mock_requests_get_patcher = mock.patch(
            'proxy.metadata.requests.get')
        self.mock_requests_get = mock_requests_get_patcher.start()
        self.addCleanup(mock_requests_get_patcher.stop)

        mock_requests_post_patcher = mock.patch(
            'proxy.metadata.requests.post')
        self.mock_requests_post = mock_requests_post_patcher.start()
        self.addCleanup(mock_requests_post_patcher.stop)

        self.mock_domain_limiter = mock.Mock()
        mock_limiter_patcher = mock.patch(
            'proxy.metadata.rratelimit.SimpleLimiter')
        mock_simple_limiter = mock_limiter_patcher.start()
        mock_simple_limiter.return_value = self.mock_domain_limiter
        self.addCleanup(mock_limiter_patcher.stop)

        self.mock_redis = mock.Mock()
        self.mock_redis.get.return_value = None
        self.mock_redis.setex.return_value = None

        self.mock_job_queue = mock.Mock()

        self.app = create_app(
            redis_client=self.mock_redis, job_queue=self.mock_job_queue)
        self.app.config['DEBUG'] = True
        self.app.config['TESTING'] = True

        self.client = self.app.test_client()

        self.test_data = copy.copy(TEST_METADATA)

    def get_mock_url_data(self, url):
        test_metadata = copy.copy(TEST_METADATA)
        test_metadata['original_url'] = url
        return test_metadata

    def get_mock_urls_data(self, urls):
        return [self.get_mock_url_data(url) for url in urls]

    def get_mock_response(self, status=200, content='{}'):
        mock_response = mock.Mock()
        mock_response.status_code = status
        mock_response.content = content

        return mock_response

    def get_response_data(self, urls):
        return {
            url: self.get_mock_url_data(url)
            for url in urls
        }
