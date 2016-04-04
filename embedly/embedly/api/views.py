import json

import redis
from flask import Blueprint, current_app, request, Response
from werkzeug.exceptions import HTTPException

from embedly.extract import URLExtractorException


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
    return_status = 200
    url_data = {}
    urls = [url for url in request.args.getlist('urls') if len(url) > 0]

    if urls:
        try:
            url_data = current_app.extractor.extract_urls(urls)
        except URLExtractorException, e:
            # V1 API has no facility for reporting errors to the caller
            return_status = 500
            url_data = {'error': e.message}

    return Response(
        json.dumps(url_data),
        status=return_status,
        mimetype='application/json',
    )


@blueprint.route('/v2/extract', methods=['POST'])
def extract_urls_v2():
    response_data = {
        'urls': {},
        'error': '',
    }

    def fail(status, error_msg):
        response_data['error'] = error_msg
        raise HTTPException(response=Response(
            json.dumps(response_data),
            status=status,
            mimetype='application/json',
        ))

    if request.content_type != 'application/json':
        fail(400, 'The Content-Type header must be set to application/json')

    try:
        urls = request.json['urls']
    except (HTTPException, KeyError):
        fail(400,
             'POST content must be a JSON encoded dictionary {urls: [...]}')

    if len(urls) > current_app.config['MAXIMUM_POST_URLS']:
        fail(400, (
            'A single request must contain '
            'at most {max} URLs in the POST body.'
        ).format(max=current_app.config['MAXIMUM_POST_URLS']))

    try:
        response_data['urls'] = current_app.extractor.extract_urls(urls)
    except URLExtractorException, e:
        fail(500, e.message)

    return Response(
        json.dumps(response_data),
        status=200,
        mimetype='application/json',
    )
