import json
import time

import redis
import requests

from embedly.stats import statsd_client
from embedly.tasks import fetch_recommended_urls


class PocketClient(object):

    class PocketException(Exception):
        pass

    def __init__(self, pocket_url, redis_client, redis_data_timeout,
                 job_queue, job_ttl):
        self.pocket_url = pocket_url
        self.redis_client = redis_client
        self.redis_key = 'POCKET_RECOMMENDED_URLS'
        self.redis_in_flight_value = 'JOB_IN_FLIGHT'
        self.redis_data_timeout = redis_data_timeout
        self.job_queue = job_queue
        self.job_ttl = job_ttl

    def fetch_recommended_urls(self):
        with statsd_client.timer('pocket_request_timer'):
            try:
                response = requests.get(self.pocket_url)
            except requests.RequestException, e:
                raise self.PocketException(
                    ('Unable to communicate '
                     'with pocket: {error}').format(error=e))

        if response.status_code != 200:
            statsd_client.incr('pocket_request_failure')
            raise self.PocketException(
                ('Error status returned from '
                 'pocket: {error_code} {error_message}').format(
                    error_code=response.status_code,
                    error_message=response.content,
                  ))

        statsd_client.incr('pocket_request_success')

        pocket_data = []

        if response is not None:
            try:
                pocket_data = json.loads(response.content)
            except (TypeError, ValueError), e:
                statsd_client.incr('pocket_parse_failure')
                raise self.PocketException(
                    ('Unable to parse the JSON '
                     'response from pocket: {error}').format(error=e))

        recommended_urls = []

        for recommended_url in pocket_data['list']:
            recommended_urls.append({
              'url': recommended_url['dedupe_url'],
              'timestamp': ((
                  int(recommended_url['published_timestamp']) or
                  int(time.time())
              ) * 1000),
            })

        try:
            self.redis_client.set(self.redis_key, json.dumps(recommended_urls))
            self.redis_client.expire(self.redis_key, self.redis_data_timeout)
        except redis.RedisError:
            raise self.PocketException('Unable to write to redis.')

        return recommended_urls

    def get_recommended_urls(self):
        try:
            recommended_urls = self.redis_client.get(self.redis_key)
        except redis.RedisError:
            raise self.PocketException('Unable to read from redis.')

        if recommended_urls is None:
            recommended_urls = []
            statsd_client.incr('redis_recommended_cache_miss')

            try:
                self.job_queue.enqueue(
                    fetch_recommended_urls,
                    time.time(),
                    ttl=self.job_ttl,
                    at_front=True,
                )
            except Exception:
                statsd_client.incr('request_recommended_job_create_fail')
                raise self.PocketException(
                    'Unable to start the pocket fetch job.')

            statsd_client.incr('request_recommended_job_create')

            try:
                self.redis_client.set(
                    self.redis_key, self.redis_in_flight_value)
                self.redis_client.expire(self.redis_key, self.job_ttl)
            except redis.RedisError:
                raise self.PocketException('Unable to write to redis.')

        else:
            statsd_client.incr('redis_recommended_cache_hit')

            try:
                recommended_urls = json.loads(recommended_urls)
            except ValueError:
                raise self.PocketException(
                    ('Unable to load JSON data '
                     'from cache for key: {key}').format(key=self.redis_key))

        return recommended_urls
