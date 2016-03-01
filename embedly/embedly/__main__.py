import os

from embedly.app import create_app


app = create_app()
port = 7001
try:
    # Receive port through an environment variable
    port = int(os.environ['PORT'])
except (KeyError, ValueError):
    pass

app.run(host='0.0.0.0', port=port)
