FROM python:2.7 

WORKDIR /embedly
COPY . /embedly
RUN pip install -r /embedly/requirements.txt

CMD ["/usr/bin/gunicorn embedly:app -b localhost:7001"] 
