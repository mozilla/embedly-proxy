import time
import json

from proxy.tasks import (
    fetch_embedly_data, fetch_mozilla_data, fetch_recommended_urls)
from proxy.tests.test_metadata import MozillaClientTest, EmbedlyClientTest
from proxy.tests.test_pocket import PocketClientTest


class TestFetchEmbedlyDataTask(EmbedlyClientTest):

    def test_task_fetches_data_and_caches(self):
        embedly_data = self.get_mock_urls_data(self.sample_urls)

        self.mock_requests_get.return_value = self.get_mock_response(
            content=json.dumps(embedly_data))

        fetch_embedly_data(
            self.sample_urls, time.time(), redis_client=self.mock_redis)

        self.assertEqual(self.mock_requests_get.call_count, 1)
        self.assertEqual(self.mock_redis.delete.call_count, 1)
        self.assertEqual(self.mock_redis.get.call_count, 0)
        self.assertEqual(
            self.mock_redis.setex.call_count, len(self.sample_urls))


class TestFetchMozillaDataTask(MozillaClientTest):

    def test_task_fetches_data_and_caches(self):
        mozilla_data = self.get_mock_urls_data(self.sample_urls)

        self.mock_requests_post.return_value = self.get_mock_response(
            content=json.dumps(mozilla_data))

        fetch_mozilla_data(
            self.sample_urls, time.time(), redis_client=self.mock_redis)

        self.assertEqual(self.mock_requests_post.call_count, 1)
        self.assertEqual(self.mock_redis.delete.call_count, 1)
        self.assertEqual(self.mock_redis.get.call_count, 0)
        self.assertEqual(
            self.mock_redis.setex.call_count, len(self.sample_urls))


class TestFetchRecommendedUrlsTask(PocketClientTest):

    def test_task_fetches_data_and_caches(self):
        self.mock_requests_get.return_value = self.get_mock_response(
            content=json.dumps(self.sample_pocket_data))

        fetch_recommended_urls(time.time(), redis_client=self.mock_redis)

        self.assertEqual(self.mock_requests_get.call_count, 1)
        self.assertEqual(self.mock_redis.get.call_count, 0)
        self.assertEqual(self.mock_redis.setex.call_count, 1)
