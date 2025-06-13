#!/usr/bin/env bash

if [ -a ".env" ]; then
    source ".env"
fi

if [ -z "${AUTOTRAINER_DASHBOARD_COMPOSE_NAME}" ]; then
    export AUTOTRAINER_DASHBOARD_COMPOSE_NAME="dashboard"
fi

docker compose -p ${AUTOTRAINER_DASHBOARD_COMPOSE_NAME} stop
