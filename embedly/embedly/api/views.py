import json

import redis
from flask import Blueprint, current_app, request, Response


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
def extract_urls_v1():
    urls = request.args.getlist('urls')
    url_data = current_app.extractor.extract_urls(urls)
    return Response(
        json.dumps(url_data),
        status=200,
        mimetype='application/json',
    )


@blueprint.route('/v2/extract', methods=['POST'])
def extract_urls_v2():
    url_data = {}

    if request.json is not None:
        urls = request.json.get('urls', [])
        url_data = current_app.extractor.extract_urls(urls)

    return Response(
        json.dumps(url_data),
        status=200,
        mimetype='application/json',
    )
