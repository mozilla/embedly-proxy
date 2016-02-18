FROM python:2.7-slim

EXPOSE 7001
WORKDIR /embedly
COPY . /embedly
RUN pip install -r /embedly/requirements.txt

CMD ["/usr/local/bin/gunicorn", "--log-file=-", "embedly:app", "-b 0.0.0.0:7001"]
