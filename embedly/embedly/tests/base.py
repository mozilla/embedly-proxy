import urllib
from unittest import TestCase

import mock


class ExtractTest(TestCase):

    def setUp(self):
        mock_requests_get_patcher = mock.patch(
            'embedly.extract.requests.get')
        self.mock_requests_get = mock_requests_get_patcher.start()
        self.addCleanup(mock_requests_get_patcher.stop)

        self.mock_redis = mock.Mock()
        self.mock_redis.get.return_value = None
        self.mock_redis.set.return_value = None

        super(ExtractTest, self).setUp()

    def _get_url_data(self, url):
        return {'original_url': url}

    def _get_urls_data(self, urls):
        return [self._get_url_data(url) for url in urls]

    def _build_query_url(self, urls):
        quoted_urls = [urllib.quote_plus(url) for url in urls]
        query_params = '&'.join(['urls={}'.format(url) for url in quoted_urls])
        return '/extract?{params}'.format(params=query_params)
