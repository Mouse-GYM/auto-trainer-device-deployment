#!/usr/bin/env bash

set -e

venv_dir="/usr/local/autotrainer/venv_maintenance"
rm -rf "${venv_dir}"

# mkdir -p "${venv_dir}"
python3.8 -m venv "${venv_dir}"

. "${venv_dir}/bin/activate"

# required for cleanup script:
python -m pip install "opencv-python>=4,<5"

echo "${venv_dir} now populated and usable"
