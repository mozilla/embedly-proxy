start_redis:
	sudo /etc/init.d/redis-server start

stop_redis:
	sudo /etc/init.d/redis-server stop

start_nginx:
	sudo /etc/init.d/nginx start

stop_nginx:
	sudo /etc/init.d/nginx stop

start_local: start_redis start_nginx

stop_local: stop_redis stop_nginx

build:
	sh scripts/build_embedly.sh

test: build
	docker run --user root -t app:build sh -c "pip install coverage flake8 && flake8 . && nosetests embedly/ --with-coverage --cover-package=embedly --cover-min-percentage=100"

dev: build start_local
	docker run --net=host --env-file=.env -e REDIS_URL=localhost -i -t app:build sh -c 'PYTHONPATH=. python embedly/dev_server.py'

gunicorn: build start_local
	docker run --net=host --env-file=.env -e REDIS_URL=localhost -i -t app:build gunicorn -c gunicorn.conf --pythonpath embedly wsgi 

compose_build: build
	docker-compose build

up: compose_build stop_local
	docker-compose up

deploy: compose_build
	sh scripts/deploy.sh $(TARGET)
