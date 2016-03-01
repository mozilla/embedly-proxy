import os

from flask import Flask
from flask.ext.cors import CORS
import redis

import embedly.views


def create_app():
    app = Flask(__name__)
    CORS(app)

    app.config['EMBEDLY_URL'] = 'https://api.embedly.com/1/extract'
    app.config['EMBEDLY_KEY'] = os.environ.get('EMBEDLY_KEY', None)

    app.config['REDIS_TIMEOUT'] = 24 * 60 * 60  # 24 hour timeout
    app.config['REDIS_URL'] = os.environ.get('REDIS_URL', None)

    app.config['VERSION_INFO'] = ''
    if os.path.exists('./version.json'):  # pragma: no cover
        with open('./version.json') as version_file:
            app.config['VERSION_INFO'] = version_file.read()

    app.register_blueprint(embedly.views.blueprint)
    app.redis_client = redis.StrictRedis(host=app.config['REDIS_URL'], port=6379, db=0)

    return app


def run_dev_server():
    app = create_app()
    port = 7001
    try:
        # Receive port through an environment variable
        port = int(os.environ['PORT'])
    except (KeyError, ValueError):
        pass

    app.run(host='0.0.0.0', port=port)
