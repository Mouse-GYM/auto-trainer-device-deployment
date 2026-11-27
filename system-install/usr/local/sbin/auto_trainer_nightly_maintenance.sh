#!/usr/bin/env bash

set -e

this_dir=$(dirname "$0")

AUTOTRAINER_NIGHTLY_MAINTENANCE_DEFAULT_FILE=${AUTOTRAINER_NIGHTLY_MAINTENANCE_DEFAULT_FILE:-"/etc/default/autotrainer_nightly_maintenance"}

status_file=${AUTOTRAINER_NIGHTLY_MAINTENANCE_STATUS_FILE:-"${HOME}/.config/Colorado/nightly_maintenance_status.json"}
# Our own arguments reach the script after ours, and the script reports to the last complete --status-file,
# so pick it the same way: a dangling one, one followed by another option, or an empty one is ignored.
for ((i = 1; i <= $#; i++)); do
    case "${!i}" in
        --status-file)
            next=$((i + 1))
            if [ "${next}" -le "$#" ] && [[ "${!next}" != -* ]]; then status_file=${!next}; fi
            ;;
        --status-file=?*)
            status_file=${!i#--status-file=}
            ;;
    esac
done

iso_now() {
    local now
    now=$(date +%Y-%m-%dT%H:%M:%S%z)
    # %:z is GNU-only; insert the offset colon by hand so the format matches the Python side on any date.
    echo "${now:0:22}:${now:22:2}"
}

started_at=$(iso_now)

# Failures before the script starts can only be reported here, to the same status file the script writes.
fail() {
    local message=$1 escaped tmp
    echo "${message}" >&2
    escaped=${message//\\/\\\\}
    escaped=${escaped//\"/\\\"}
    tmp="${status_file}.tmp.$$"
    if mkdir -p "$(dirname "${status_file}")" \
        && printf '{\n  "schema_version": 1,\n  "result": "failure",\n  "exit_code": 1,\n  "started_at": "%s",\n  "finished_at": "%s",\n  "errors": [\n    {"kind": "wrapper-failed", "path": null, "message": "%s"}\n  ],\n  "warnings": []\n}\n' \
            "${started_at}" "$(iso_now)" "${escaped}" > "${tmp}" \
        && mv -f "${tmp}" "${status_file}"
    then
        :
    else
        rm -f "${tmp}"
        echo "could not write ${status_file}" >&2
    fi
    exit 1
}

echo "Sourcing default file ${AUTOTRAINER_NIGHTLY_MAINTENANCE_DEFAULT_FILE}"
test -r "${AUTOTRAINER_NIGHTLY_MAINTENANCE_DEFAULT_FILE}" \
    || fail "defaults file ${AUTOTRAINER_NIGHTLY_MAINTENANCE_DEFAULT_FILE} is missing or unreadable"
. "${AUTOTRAINER_NIGHTLY_MAINTENANCE_DEFAULT_FILE}" \
    || fail "sourcing ${AUTOTRAINER_NIGHTLY_MAINTENANCE_DEFAULT_FILE} failed"
[ -n "${target_directory:-}" ] && [ -n "${venv_dir:-}" ] && [ -n "${delete_older_days:-}" ] \
    || fail "${AUTOTRAINER_NIGHTLY_MAINTENANCE_DEFAULT_FILE} must set target_directory, venv_dir and delete_older_days"

venv_python="${venv_dir}/bin/python"
test -x "${venv_python}" \
    || fail "maintenance venv interpreter ${venv_python} is missing or not executable; run install_maintenance_venv.sh"
"${venv_python}" -c 'import sys' \
    || fail "maintenance venv interpreter ${venv_python} cannot start"

declare -a args=(
    # prepend it :
    "--target-dir" "${target_directory}"
    "--delete-older-days" "${delete_older_days}"
    "--status-file" "${status_file}"
    # to the normal script args, so that can be eventually overridden with them
    "${@}"
)

# relay all our command args to the script itself:
"${venv_python}" "${this_dir}/jetson_daily_cleanup.py" "${args[@]}"
