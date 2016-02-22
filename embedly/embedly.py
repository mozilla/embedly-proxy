import os
import urllib
import json

import requests
import redis
from flask import Flask, request, Response
from flask.ext.cors import CORS


EMBEDLY_URL = 'https://api.embedly.com/1/extract'
EMBEDLY_KEY = os.environ['EMBEDLY_KEY']

REDIS_TIMEOUT = 24 * 60 * 60
redis_client = redis.StrictRedis(host=os.environ['REDIS_URL'], port=6379, db=0)

app = Flask(__name__)
CORS(app)


def get_cached_url(url):
    cached_data = redis_client.get(url)

    if cached_data is not None:
        return json.loads(cached_data)


def set_cached_url(url, data):
    redis_client.set(url, json.dumps(data))
    redis_client.expire(url, REDIS_TIMEOUT)


def get_urls_from_embedly(urls):
    params = '&'.join([
        'key={}'.format(EMBEDLY_KEY),
        'urls={}'.format(','.join([urllib.quote_plus(url) for url in urls])),
    ])

    request_url = '{base}?{params}'.format(base=EMBEDLY_URL, params=params)
    response = requests.get(request_url)

    try:
        url_data = {
            data['original_url']: data
            for data in json.loads(response.content)
        }
    except ValueError:
        url_data = {}

    return url_data


@app.route('/extract')
def extract_urls():
    urls = request.args.getlist('urls')
    url_data = {}

    uncached_urls = []
    for url in urls:
        cached_url_data = get_cached_url(url)

        if cached_url_data is not None:
            url_data[url] = cached_url_data
        else:
            uncached_urls.append(url)

    if uncached_urls:
        embedly_url_data = get_urls_from_embedly(uncached_urls)

        for embedly_url, embedly_data in embedly_url_data.items():
            set_cached_url(embedly_url, embedly_data)

        url_data.update(embedly_url_data)

    return Response(
        json.dumps(url_data),
        status=200,
        mimetype='application/json',
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7001)
