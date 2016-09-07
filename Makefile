build:
	sh scripts/build_embedly.sh

test: build 
	docker run -u root -t -i app:build sh -c "flake8 . && nosetests embedly/ --with-coverage --cover-package=embedly --cover-min-percentage=100"

compose_build: build
	docker-compose build

shell: compose_build
	docker-compose run embedly ipython 

up: compose_build
	docker-compose up

deploy: compose_build
	sh scripts/deploy.sh $(TARGET)
