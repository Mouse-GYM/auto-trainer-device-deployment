#!/usr/bin/env bash

set -e  # exit with any "failed" command

status_file="$HOME/.config/Colorado/autotrainer_running_status.env"

# debug:
# exec > >(tee "$HOME/gui-start.log") 2>&1

if test "${DISPLAY}" != ":1002"
then
    echo "Not nomachine shared session"
    msg="You're running with physical display/monitor,\n\nPlease use nomachine to connect locally."
    zenity --no-wrap --info --text="${msg}"
    exit 1
fi

# give graphical window system bit of time:
sleep 3

args=()

# read last running status if any:
if test -f "${status_file}"
then
    . "${status_file}"
    args+=( --start-mode "${status}" )
fi

# bash -l -i -c "echo ; env ; echo \$PATH ; echo ; auto-trainer-local -d" &>/dev/null
# set -x
bash -l -i -c "set -x ; auto-trainer-local \"\${@}\" &>/dev/null" -- "${args[@]}"

# -l -i required to get .bashrc preread by bashrc.
# NB: assuming conda auto-trainer-1 env is auto-activated via .bashrc
