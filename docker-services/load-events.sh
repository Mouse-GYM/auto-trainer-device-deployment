#!/usr/bin/env bash
#
# Loads earlier days' event files into the device database through the running api service.
#
#   ./load-events.sh                      # yesterday (device-local)
#   ./load-events.sh 20261123             # one day (yyyyMMdd or yyyy-MM-dd)
#   ./load-events.sh 20261120 20261121    # several days, one load each, in the order given
#
# The command must run inside the api container: it posts to the service's local admin port, which is bound to
# the container's loopback only, so the load runs in the service process. A separate container could not reach that
# port. Ctrl-C cancels the load in progress.

cd "$(dirname "$0")" || exit 1

if [ -a ".env" ]; then
    source ".env"
fi

if [ -z "${AUTOTRAINER_COMPOSE_NAME}" ]; then
    export AUTOTRAINER_COMPOSE_NAME="autotrainer"
fi

compose=(docker compose -f docker-compose.yml -p "${AUTOTRAINER_COMPOSE_NAME}")

if [ -z "$("${compose[@]}" ps --status running -q api)" ]; then
    echo "The api service is not running in compose project '${AUTOTRAINER_COMPOSE_NAME}'; start it with ./up.sh." >&2
    exit 1
fi

# Keep a TTY when there is one, so Ctrl-C reaches the command and cancels the load.
exec_flags=()
if [ ! -t 0 ] || [ ! -t 1 ]; then
    exec_flags=(-T)
fi

load() {
    "${compose[@]}" exec "${exec_flags[@]}" api dotnet AutoTrainer.Api.dll load-events "$@"
}

if [ $# -eq 0 ]; then
    load
    exit $?
fi

failed=()
for day in "$@"; do
    [ $# -gt 1 ] && echo "=== ${day} ==="
    load "${day}" || failed+=("${day}")
    [ $# -gt 1 ] && echo
done

if [ ${#failed[@]} -gt 0 ]; then
    echo "Failed: ${failed[*]}" >&2
    exit 1
fi
