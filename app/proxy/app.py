import os

import redis
from flask import Flask
from flask.ext.cors import CORS
from raven.contrib.flask import Sentry
from rq import Queue

import api.views
from metadata import EmbedlyClient, MozillaClient
from pocket import PocketClient


def get_config():
    return {
        'BLOCKED_DOMAINS': ['embedly.com'],
        'EMBEDLY_KEY': os.environ.get('EMBEDLY_KEY', None),
        'EMBEDLY_URL': 'https://api.embedly.com/1/extract',
        'MOZILLA_URL': (
            'https://page-metadata.services.mozilla.com/v1/metadata'),
        'JOB_TTL': 300,
        'MAXIMUM_POST_URLS': 25,
        'POCKET_URL': (
            'https://getpocket.com/v3/firefox/'
            'global-recs?consumer_key={pocket_key}').format(
                pocket_key=os.environ.get('POCKET_KEY', None)),
        'POCKET_DATA_TIMEOUT': 10 * 60,  # 10 minutes timeout
        'REDIS_DATA_TIMEOUT': 24 * 60 * 60,  # 24 hour timeout
        'REDIS_JOB_TIMEOUT': 60 * 60,  # 1 hour timeout
        'REDIS_URL': os.environ.get('REDIS_URL', None),
        'SENTRY_DSN': os.environ.get('SENTRY_DSN', ''),
        'SENTRY_PROCESSORS': ('raven.processors.RemovePostDataProcessor',),
        'URL_BATCH_SIZE': 5,
    }


def get_redis_client():  # pragma: nocover
    config = get_config()

    return redis.StrictRedis(host=config['REDIS_URL'], port=6379, db=0)


def get_job_queue(redis_client=None):
    redis_client = redis_client or get_redis_client()

    return Queue(connection=redis_client)


def get_metadata_client_args(redis_client=None, job_queue=None):
    config = get_config()

    return {
        'redis_client': redis_client or get_redis_client(),
        'redis_data_timeout': config['REDIS_DATA_TIMEOUT'],
        'redis_job_timeout': config['REDIS_JOB_TIMEOUT'],
        'blocked_domains': config['BLOCKED_DOMAINS'],
        'job_queue': job_queue or get_job_queue(),
        'job_ttl': config['JOB_TTL'],
        'url_batch_size': config['URL_BATCH_SIZE'],
    }


def get_embedly_client(redis_client=None, job_queue=None):
    config = get_config()

    return EmbedlyClient(
        embedly_url=config['EMBEDLY_URL'],
        embedly_key=config['EMBEDLY_KEY'],
        **get_metadata_client_args(redis_client, job_queue)
    )


def get_mozilla_client(redis_client=None, job_queue=None):
    config = get_config()

    return MozillaClient(
        mozilla_url=config['MOZILLA_URL'],
        **get_metadata_client_args(redis_client, job_queue)
    )


def get_pocket_client(redis_client=None, job_queue=None):
    config = get_config()

    return PocketClient(
        config['POCKET_URL'],
        redis_client or get_redis_client(),
        config['POCKET_DATA_TIMEOUT'],
        job_queue or get_job_queue(),
        config['JOB_TTL'],
    )


def create_app(redis_client=None, job_queue=None):
    config = get_config()

    app = Flask(__name__)
    CORS(app)

    # Maximum number of URLs to receive in an API call
    app.config.update(config)

    app.redis_client = redis_client or get_redis_client()

    app.job_queue = job_queue or get_job_queue(app.redis_client)

    app.embedly_client = get_embedly_client(app.redis_client, app.job_queue)

    app.mozilla_client = get_mozilla_client(app.redis_client, app.job_queue)

    app.pocket_client = get_pocket_client(app.redis_client, app.job_queue)

    app.config['VERSION_INFO'] = ''
    if os.path.exists('./version.json'):  # pragma: no cover
        with open('./version.json') as version_file:
            app.config['VERSION_INFO'] = version_file.read()

    app.register_blueprint(api.views.blueprint)

    app.sentry = Sentry(app)

    return app
