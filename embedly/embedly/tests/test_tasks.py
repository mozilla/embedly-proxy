import json

from embedly.tasks import fetch_remote_url_data
from embedly.tests.test_extract import ExtractorTest


class TestFetchRemoteUrlDataTask(ExtractorTest):

    def test_task_fetches_data_and_caches(self):
        embedly_data = self.get_mock_urls_data(self.sample_urls)

        self.mock_requests_get.return_value = self.get_mock_response(
            content=json.dumps(embedly_data))

        fetch_remote_url_data(self.sample_urls, redis_client=self.mock_redis)

        self.assertEqual(self.mock_requests_get.call_count, 1)
        self.assertEqual(self.mock_redis.get.call_count, 0)
        self.assertEqual(self.mock_redis.set.call_count, len(self.sample_urls))
