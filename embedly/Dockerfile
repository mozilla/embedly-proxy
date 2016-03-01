FROM python:2.7

EXPOSE 7001

RUN groupadd --gid 10001 app && \
    useradd --uid 10001 --gid 10001 --home /app --create-home app

WORKDIR /app
COPY ./requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY . /app

USER app

CMD ["/usr/local/bin/gunicorn", "-c", "gunicorn.conf", "--pythonpath", "embedly", "wsgi"]
