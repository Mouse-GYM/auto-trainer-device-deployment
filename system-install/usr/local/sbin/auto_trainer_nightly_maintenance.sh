#!/usr/bin/env bash

set -e

echo "Listing network directory .."

ls /mnt/isilon

. /usr/local/autotrainer/venv_maintenance/bin/activate

this_dir=$(dirname "$0")

# relay all our command args to the script itself:
python "${this_dir}/jetson_daily_cleanup.py" "${@}"
