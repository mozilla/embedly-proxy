from unittest import TestCase

import mock


class MockTest(TestCase):

    def setUp(self):
        mock_requests_get_patcher = mock.patch(
            'embedly.extract.requests.get')
        self.mock_requests_get = mock_requests_get_patcher.start()
        self.addCleanup(mock_requests_get_patcher.stop)

        self.mock_redis = mock.Mock()
        self.mock_redis.get.return_value = None
        self.mock_redis.set.return_value = None

        super(MockTest, self).setUp()

    def get_mock_url_data(self, url):
        return {'original_url': url}

    def get_mock_urls_data(self, urls):
        return [self.get_mock_url_data(url) for url in urls]
