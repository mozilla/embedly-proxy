build:
	docker build -t embedly embedly/

test: build
	docker run --user root -t embedly sh -c "pip install coverage flake8 && flake8 . && nosetests embedly/ --with-coverage --cover-package=embedly --cover-min-percentage=100"

compose_build:
	docker-compose build

up: compose_build
	docker-compose up

gunicorn:
	gunicorn -c embedly/gunicorn.conf --pythonpath embedly/embedly api.views:app
