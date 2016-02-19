FROM python:2.7

EXPOSE 7001
WORKDIR /embedly
COPY . /embedly
RUN pip install -r /embedly/requirements.txt

CMD ["/usr/local/bin/gunicorn", "-c", "gunicorn.conf", "embedly:app"]
