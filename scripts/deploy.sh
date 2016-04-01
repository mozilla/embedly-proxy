#!/bin/bash
for dockermachine in $(docker-machine ls | grep $1 | awk '{print $1}')
do 
  eval $(docker-machine env $dockermachine)
  docker-compose kill
  docker-compose build; docker-compose up -d
done
eval $(docker-machine env --unset)
