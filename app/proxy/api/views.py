import json

import redis
from flask import Blueprint, current_app, request as Request, Response
from werkzeug.exceptions import HTTPException

from proxy.stats import statsd_client


blueprint = Blueprint('views', __name__)


def fail(response_data, status, error_msg):
    response_data['error'] = error_msg
    raise HTTPException(response=Response(
        json.dumps(response_data),
        status=status,
        mimetype='application/json',
    ))


@blueprint.route('/__heartbeat__')
def heartbeat():
    status = 200

    # Check cache connectivity
    try:
        current_app.redis_client.ping()
        statsd_client.incr('heartbeat.pass')
    except redis.ConnectionError:
        statsd_client.incr('heartbeat.fail')
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


def get_metadata(metadata_client, config, request):
    response_data = {
        'urls': {},
        'error': '',
    }

    def fail(response_data, status, error_msg):
        response_data['error'] = error_msg
        raise HTTPException(response=Response(
            json.dumps(response_data),
            status=status,
            mimetype='application/json',
        ))

    if request.content_type and 'application/json' not in request.content_type:
        fail(
            response_data,
            400,
            'The Content-Type header must be set to application/json',
        )

    try:
        urls = request.json['urls']
    except (HTTPException, TypeError, KeyError):
        fail(response_data, 400,
             'POST content must be a JSON encoded dictionary {urls: [...]}')

    if len(urls) > config['MAXIMUM_POST_URLS']:
        fail(response_data, 400, (
            'A single request must contain '
            'at most {max} URLs in the POST body.'
        ).format(max=config['MAXIMUM_POST_URLS']))

    if not all(urls):
        fail(response_data, 400, 'Do not send empty or null URLs.')

    try:
        response_data['urls'] = metadata_client.extract_urls_async(urls)
    except metadata_client.MetadataClientException, e:
        fail(response_data, 500, e.message)

    return Response(
        json.dumps(response_data),
        status=200,
        mimetype='application/json',
    )


@blueprint.route('/v2/extract', methods=['POST'])
def embedly_metadata():
    return get_metadata(
        current_app.embedly_client, current_app.config, Request)


@blueprint.route('/v2/metadata', methods=['POST'])
def mozilla_metadata():
    return get_metadata(
        current_app.mozilla_client, current_app.config, Request)


@blueprint.route('/v2/recommendations', methods=['GET'])
def get_recommended_urls():
    response_data = {
        'urls': {},
        'error': '',
    }

    try:
        response_data['urls'] = (
            current_app.pocket_client.get_recommended_urls())
    except current_app.pocket_client.PocketException, e:
        fail(response_data, 500, e.message)

    return Response(
        json.dumps(response_data),
        status=200,
        mimetype='application/json',
    )
