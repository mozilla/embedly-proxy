import os
import urllib
import json

import requests
from flask import Flask, request, Response


EMBEDLY_URL = 'https://api.embedly.com/1/extract'
EMBEDLY_KEY = os.environ['EMBEDLY_KEY']


app = Flask(__name__)


def get_urls(urls):
    params = '&'.join([
        'key={}'.format(EMBEDLY_KEY),
        'urls={}'.format(','.join([urllib.quote_plus(url) for url in urls])),
    ])

    request_url = '{base}?{params}'.format(base=EMBEDLY_URL, params=params)
    response = requests.get(request_url)

    try:
        url_data = json.loads(response.content)
    except ValueError:
        url_data = []

    return url_data


@app.route('/extract')
def extract_urls():
    url_data = get_urls(request.args.getlist('urls'))

    return Response(
        json.dumps(url_data),
        status=200,
        mimetype='application/json',
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7001)
