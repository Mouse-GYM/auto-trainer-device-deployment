#!/usr/bin/env bash

set -e

this_dir=$(dirname "$0")

AUTOTRAINER_NIGHTLY_MAINTENANCE_DEFAULT_FILE=${AUTOTRAINER_NIGHTLY_MAINTENANCE_DEFAULT_FILE:-"/etc/default/autotrainer_nightly_maintenance"}

echo "Sourcing default file ${AUTOTRAINER_NIGHTLY_MAINTENANCE_DEFAULT_FILE}"
. "${AUTOTRAINER_NIGHTLY_MAINTENANCE_DEFAULT_FILE}"

echo "Listing sync target directory .."

ls "${target_directory}"

echo "Activate python tool env"
. "${venv_dir}/bin/activate"

declare -a args=(
    # prepend it :
    "--target-dir" "${target_directory}"
    "--delete-older-days" "${delete_older_days}"
    # to the normal script args, so that can be eventually overridden with them
    "${@}"
)

# relay all our command args to the script itself:
python "${this_dir}/jetson_daily_cleanup.py" "${args[@]}"
