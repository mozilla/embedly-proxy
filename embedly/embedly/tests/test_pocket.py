# -*- coding: utf-8 -*-
import json
import time

import redis
import requests

from embedly.pocket import PocketClient
from embedly.tests.base import AppTest


class PocketClientTest(AppTest):

    def get_response_data(self, urls):
        return {
            url: self.get_mock_url_data(url)
            for url in urls
        }

    def setUp(self):
        super(PocketClientTest, self).setUp()

        self.pocket_client = PocketClient(
            'POCKET_KEY',
            self.mock_redis,
            10,
            self.mock_job_queue,
            10,
        )

        self.sample_pocket_data = {
            'list': [{
                'dedupe_url': 'http://www.example.com/recommended/content/',
                'domain': 'example.com',
                'excerpt': 'Recommended content!',
                'image_src': None,
                'published_timestamp': str(int(time.time())),
                'sort_id': 1,
                'title': 'Recommended Content',
                'url': 'http://donotuse.thisurl.com/',
            }, {
                'dedupe_url': 'http://www.example.com/recommended/other/',
                'domain': 'example.com',
                'excerpt': 'Recommended other content!',
                'image_src': None,
                'published_timestamp': str(int(time.time())),
                'sort_id': 2,
                'title': 'Recommended Other Content',
                'url': 'http://donotuse.thisurl.com/either/',
            }],
        }

        self.sample_recommended_urls = [
            self.get_pocket_content(url_data)
            for url_data in self.sample_pocket_data['list']
        ]

    def get_pocket_content(self, url_data):
        return {
            'url': url_data['dedupe_url'],
            'timestamp': int(url_data['published_timestamp']) * 1000,
        }


class TestPocketClientFetchRecommendedUrls(PocketClientTest):

    def test_pocket_client_returns_urls_and_stores_in_cache(self):
        self.mock_requests_get.return_value = self.get_mock_response(
            content=json.dumps(self.sample_pocket_data))

        recommended_urls = self.pocket_client.fetch_recommended_urls()

        self.assertEqual(recommended_urls, self.sample_recommended_urls)
        self.assertEqual(self.mock_redis.set.call_count, 1)
        self.assertEqual(self.mock_redis.expire.call_count, 1)

    def test_pocket_client_raises_exception_if_request_fails(self):
        self.mock_requests_get.side_effect = requests.RequestException

        with self.assertRaises(PocketClient.PocketException):
            self.pocket_client.fetch_recommended_urls()

    def test_pocket_client_raises_exception_if_response_not_200(self):
        self.mock_requests_get.return_value = self.get_mock_response(
            status=400)

        with self.assertRaises(PocketClient.PocketException):
            self.pocket_client.fetch_recommended_urls()

    def test_pocket_client_raises_exception_if_bad_json(self):
        self.mock_requests_get.return_value = self.get_mock_response(
            content=';badjson')

        with self.assertRaises(PocketClient.PocketException):
            self.pocket_client.fetch_recommended_urls()

    def test_pocket_client_raises_exception_if_redis_fails_to_get(self):
        self.mock_redis.get.side_effect = redis.RedisError

        with self.assertRaises(PocketClient.PocketException):
            self.pocket_client.fetch_recommended_urls()

    def test_pocket_client_raises_exception_if_redis_fails_to_set(self):
        self.mock_requests_get.return_value = self.get_mock_response(
            content=json.dumps(self.sample_pocket_data))

        self.mock_redis.set.side_effect = redis.RedisError

        with self.assertRaises(self.pocket_client.PocketException):
            self.pocket_client.fetch_recommended_urls()


class TestPocketClientGetRecommendedUrls(PocketClientTest):

    def test_pocket_client_returns_cached_url_data(self):
        self.mock_redis.get.return_value = json.dumps(
            self.sample_recommended_urls)

        recommended_urls = self.pocket_client.get_recommended_urls()

        self.assertEqual(recommended_urls, self.sample_recommended_urls)
        self.assertEqual(self.mock_redis.get.call_count, 1)
        self.assertEqual(self.mock_job_queue.enqueue.call_count, 0)

    def test_pocket_client_queues_task_if_no_cached_data_found(self):
        self.mock_redis.get.return_value = None

        recommended_urls = self.pocket_client.get_recommended_urls()

        self.assertEqual(recommended_urls, [])
        self.assertEqual(self.mock_redis.get.call_count, 1)
        self.assertEqual(self.mock_job_queue.enqueue.call_count, 1)

    def test_pocket_client_raises_exception_if_redis_fails(self):
        self.mock_redis.get.side_effect = redis.RedisError

        with self.assertRaises(PocketClient.PocketException):
            self.pocket_client.get_recommended_urls()

    def test_pocket_client_raises_exception_if_job_queue_fails(self):
        self.mock_job_queue.enqueue.side_effect = Exception

        with self.assertRaises(PocketClient.PocketException):
            self.pocket_client.get_recommended_urls()

    def test_pocket_client_raises_exception_if_cached_json_invalid(self):
        self.mock_redis.get.return_value = ';invalid json'

        with self.assertRaises(PocketClient.PocketException):
            self.pocket_client.get_recommended_urls()

    def test_pocket_client_raises_exception_if_unable_to_write_to_redis(self):
        self.mock_redis.set.side_effect = redis.RedisError

        with self.assertRaises(PocketClient.PocketException):
            self.pocket_client.get_recommended_urls()
