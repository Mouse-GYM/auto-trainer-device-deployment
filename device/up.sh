#!/usr/bin/env bash

if [ -a ".env" ]; then
    source ".env"
fi

if [ -z "${AUTOTRAINER_COMPOSE_NAME}" ]; then
    export AUTOTRAINER_COMPOSE_NAME="autotrainer"
fi

docker compose -f docker-compose.yml -p ${AUTOTRAINER_COMPOSE_NAME} up -d
