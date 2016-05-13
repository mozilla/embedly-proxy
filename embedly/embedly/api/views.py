import json

import redis
from flask import Blueprint, current_app, request, Response
from werkzeug.exceptions import HTTPException

from embedly.tasks import get_url_data
from embedly.stats import statsd_client
from embedly.extract import URLExtractorException


blueprint = Blueprint('views', __name__)


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

    if not all(urls):
        fail(400, 'Do not send empty or null URLs.')

    url = urls[0]
    print 'Queueing from view', url
    current_app.job_queue.enqueue(get_url_data, url)

    try:
        response_data['urls'] = current_app.extractor.extract_urls(urls)
    except URLExtractorException, e:
        fail(500, e.message)

    return Response(
        json.dumps(response_data),
        status=200,
        mimetype='application/json',
    )
