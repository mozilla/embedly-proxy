import copy
from unittest import TestCase

import mock

from embedly.app import create_app


EMBEDLY_TEST_DATA = {
    'app_links': [{
        'namespace': 'Example',
        'package': 'Example',
        'path': '/example/',
        'type': 'example',
    }],
    'authors': [{
        'name': 'Julius Caeser',
        'url': 'https://www.example.com/julius/',
    }],
    'cache_age': 78022,
    'content': '<html><body>Hello!</body></html>',
    'description': 'Example web site',
    'embeds': [{
        'author_name': 'Julius Caeser',
        'author_url': 'https://www.example.com/julius/',
        'cache_age': 123,
        'description': 'Stuff!',
        'provider_name': 'Things!',
        'provider_url': 'https://www.example.com/',
        'thumbnail_height': 123,
        'thumbnail_url': 'https://www.example.com/image.jpg',
        'thumbnail_width': 123,
        'title': 'This and that.',
        'type': 'html',
        'version': '1.0',
    }],
    'entities': [{
        'name': 'Person',
        'count': 1,
    }],
    'favicon_colors': [{
        'color': [208, 226, 240],
        'weight': 0.1926269531,
    }],
    'favicon_url': 'https://www.example.com/favicon.ico',
    'images': [{
        'caption': 'An image',
        'colors': [{
            'color': [208, 226, 240],
            'weight': 0.1926269531,
        }],
        'entropy': 0.1,
        'height': 100,
        'size': 12345,
        'url': 'https://www.example.com/image.jpg',
        'width': 100,
    }],
    'keywords': [{
        'name': 'Person',
        'score': 1,
    }],
    'language': 'English',
    'lead': 'Leading in!',
    'media': {
        'author_name': 'Julius Caeser',
        'author_url': 'https://www.example.com/julius/',
        'cache_age': 123,
        'description': 'Stuff!',
        'provider_name': 'Things!',
        'provider_url': 'https://www.example.com/',
        'thumbnail_height': 123,
        'thumbnail_url': 'https://www.example.com/image.jpg',
        'thumbnail_width': 123,
        'title': 'This and that.',
        'type': 'html',
        'version': '1.0',
    },
    'offset': 12345,
    'original_url': 'http://www.example.com',
    'provider_display': 'www.example.com',
    'provider_name': 'Reddit',
    'provider_url': 'https://www.example.com',
    'published': 1459186964000,
    'related': [{
        'author_name': 'Julius Caeser',
        'author_url': 'https://www.example.com/julius/',
        'cache_age': 123,
        'description': 'Stuff!',
        'provider_name': 'Things!',
        'provider_url': 'https://www.example.com/',
        'thumbnail_height': 123,
        'thumbnail_url': 'https://www.example.com/image.jpg',
        'thumbnail_width': 123,
        'title': 'This and that.',
        'type': 'html',
        'version': '1.0',
    }],
    'safe': True,
    'title': 'Example web site',
    'type': 'html',
    'url': 'https://www.example.com/'
}


class AppTest(TestCase):

    def setUp(self):
        super(AppTest, self).setUp()

        mock_requests_get_patcher = mock.patch(
            'embedly.extract.requests.get')
        self.mock_requests_get = mock_requests_get_patcher.start()
        self.addCleanup(mock_requests_get_patcher.stop)

        self.mock_redis = mock.Mock()
        self.mock_redis.get.return_value = None
        self.mock_redis.set.return_value = None

        mock_fetch_task_patcher = mock.patch(
            'embedly.extract.fetch_remote_url_data')
        self.mock_fetch_task = mock_fetch_task_patcher.start()
        self.addCleanup(mock_fetch_task_patcher.stop)

        self.app = create_app(redis_client=self.mock_redis)
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
