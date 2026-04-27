#!/usr/bin/env bash

set -e  # exit on any unhandled command error

_expected_user="autotrainer"


if test "${USER}" != "${_expected_user}" -a "${FORCE_USER}" != "1"
then
    echo "Expecting to run with ${_expected_user} user, but got ${USER}" >&2
    echo "You can force any user with setting env. var. FORCE_USER=1" >&2
    exit 1
fi

# goto this-script directory:
cd "$(dirname "${0}")"

## first preparation part,
# install any desired extra package,
# and copy our custom service files to target location

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <device_name>" >&2
  exit 1
fi

device_name="$1"

echo "Setting hostname to ${device_name}"
sudo hostnamectl set-hostname "${device_name}"

#

echo "Copying target home and system files ..."
echo Skipping ./copy_home_files.sh for now.
./copy_system_files.sh

#

desired_packages=(
  avahi-daemon
  libhdf5-serial-dev
  libxcb-cursor0
  busybox
  can-utils
  git git-lfs
  python3.8-venv
  zenity  # display GUI msg box from CLI
  libopenblas0  # for nvidia torch
)
sudo apt-get install -y "${desired_packages[@]}"

#

./disable_tracker_service.sh

./install_docker.sh

# isilon mount
sudo ./install_mnt_isilon.sh

sudo ./install_maintenance_venv.sh

echo "Adding/enabling autotrainer systemd units"
sudo systemctl enable autotrainer_maintenance.timer
sudo systemctl start autotrainer_maintenance.timer

# Enable can_setup service on boot/startup.
sudo systemctl enable can_setup.service
# and start it for this boot cycle.
sudo systemctl start can_setup.service

# Reload mDNS with new service.
sudo service avahi-daemon restart

# Output for docker container logs
sudo mkdir -p /autotrainer/logs
sudo chmod ugo+w /autotrainer/logs

echo "Installing spinnaker library"
./install_spinnaker.sh

# finally:

echo "Adding user to required or useful groups"
for group in systemd-journal flirimaging adm
do
    sudo adduser "${USER}" "${group}"
done

echo "Preparation complete."
