import json

import requests

from embedly.extract import IN_JOB_QUEUE, URLExtractorException
from embedly.tasks import fetch_remote_url_data
from embedly.tests.test_extract import ExtractorTest


class TestFetchRemoteUrlDataTask(ExtractorTest):

    def test_task_fetches_data_and_caches(self):
        mock_cache = {url: IN_JOB_QUEUE for url in self.sample_urls}

        def mock_set(key, value, *args, **kwargs):
            mock_cache[key] = value

        def mock_get(key):
            return mock_cache[key] if key in mock_cache else None

        self.mock_redis.get.side_effect = mock_get
        self.mock_redis.set.side_effect = mock_set

        embedly_data = self.get_mock_urls_data(self.sample_urls)

        self.mock_requests_get.return_value = self.get_mock_response(
            content=json.dumps(embedly_data))

        fetch_remote_url_data(self.sample_urls, redis_client=self.mock_redis)

        self.assertEqual(self.mock_requests_get.call_count, 1)
        self.assertEqual(self.mock_redis.delete.call_count, 1)
        self.assertEqual(self.mock_redis.get.call_count, 0)
        self.assertEqual(self.mock_redis.set.call_count, len(self.sample_urls))
        self.assertEqual(mock_cache.keys(), self.sample_urls)
        self.assertNotIn(IN_JOB_QUEUE, mock_cache.values())

    def test_task_removes_placeholder_values_if_job_fails(self):
        existing_url = 'http://www.example.com'

        mock_cache = {url: IN_JOB_QUEUE for url in self.sample_urls}
        mock_cache[existing_url] = self.get_mock_url_data(existing_url)

        def mock_set(key, value, *args, **kwargs):
            mock_cache[key] = value

        def mock_get(key):
            return mock_cache[key] if key in mock_cache else None

        def mock_delete(*args):
            for arg in args:
                del mock_cache[arg]

        self.mock_redis.get.side_effect = mock_get
        self.mock_redis.set.side_effect = mock_set
        self.mock_redis.delete.side_effect = mock_delete
        self.mock_requests_get.side_effect = requests.RequestException

        with self.assertRaises(URLExtractorException):
            fetch_remote_url_data(
                self.sample_urls, redis_client=self.mock_redis)

        self.assertEqual(self.mock_requests_get.call_count, 1)
        self.assertEqual(self.mock_redis.delete.call_count, 1)
        self.assertEqual(self.mock_redis.get.call_count, 0)
        self.assertEqual(self.mock_redis.set.call_count, 0)
        self.assertEqual(mock_cache.keys(), [existing_url])
