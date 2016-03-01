import json
import os

import redis
from flask import Blueprint, current_app, request, Response

from embedly.extract import extract_urls


blueprint = Blueprint('views', __name__)


@blueprint.route('/__heartbeat__')
def heartbeat():
    status = 200

    # Check cache connectivity
    try:
        current_app.redis_client.ping()
    except redis.ConnectionError:
        status = 500

    return Response('', status=status)


@blueprint.route('/__lbheartbeat__')
def lbheartbeat():
    return Response('', status=200)


@blueprint.route('/__version__')
def version():
    return Response(
        current_app.config['VERSION_INFO'],
        status=200,
        mimetype='application/json',
    )


@blueprint.route('/extract', methods=['GET'])
def extract_urls_api_v1():
    urls = request.args.getlist('urls')
    url_data = extract_urls(urls)

    return Response(
        json.dumps(url_data),
        status=200,
        mimetype='application/json',
    )


@blueprint.route('/v2/extract', methods=['POST'])
def extract_urls_api_v2():
    try:
        urls = json.loads(request.values['urls'])
    except (KeyError, ValueError):
        urls = []

    url_data = extract_urls(urls)

    return Response(
        json.dumps(url_data),
        status=200,
        mimetype='application/json',
    )


if __name__ == '__main__':  # pragma: no cover
    port = 7001
    try:
        # Receive port through an environment variable
        port = int(os.environ['PORT'])
    except (KeyError, ValueError):
        pass

    current_app.run(host='0.0.0.0', port=port)
