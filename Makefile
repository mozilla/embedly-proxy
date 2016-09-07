build:
	sh scripts/build_embedly.sh

test: build 
	docker run -t -i -u root app:build sh -c "flake8 . && nosetests embedly/ --nocapture --with-coverage --cover-package=embedly --cover-min-percentage=100"

compose_build: build
	docker-compose build

shell: compose_build
	docker-compose run embedly ipython 

up: compose_build
	docker-compose up
