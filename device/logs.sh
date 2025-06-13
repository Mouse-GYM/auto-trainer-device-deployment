#!/usr/bin/env bash

if [ -a ".env" ]; then
    source ".env"
fi

if [ -z "${AUTOTRAINER_COMPOSE_NAME}" ]; then
    export AUTOTRAINER_COMPOSE_NAME="autotrainer"
fi

docker compose -p ${AUTOTRAINER_COMPOSE_NAME} logs --follow
