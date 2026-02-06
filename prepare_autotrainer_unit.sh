#!/usr/bin/env bash

set -e

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

desired_packages=(
  avahi-daemon
  libhdf5-serial-dev
  libxcb-cursor0
  busybox
  can-utils
  git git-lfs
)

sudo apt-get install -y "${desired_packages[@]}"

./install_docker.sh

echo "Copying target files ..."
(
  cd ./system-install
  sudo rsync -av ./ /
)


## second preparation part,
# do any remaining extra steps that are required after the first part,
# like configure some newly installed service.

# Disable gnome tracker service:
tracker_desktop_files=(
  /etc/xdg/autostart/tracker-extract.desktop
  /etc/xdg/autostart/tracker-miner-apps.desktop
  /etc/xdg/autostart/tracker-miner-fs.desktop
  /etc/xdg/autostart/tracker-miner-user-guides.desktop
  /etc/xdg/autostart/tracker-store.desktop
)
echo -e "\nHidden=true\n" | sudo tee --append "${tracker_desktop_files[@]}" > /dev/null

# Interval in days to check whether the filesystem is up to date in the database. 0 forces crawling anytime, -1 forces it only after unclean shutdowns, and -2 disables it entirely
gsettings set org.freedesktop.Tracker.Miner.Files crawling-interval -2  # Default: -1
# Set to false to completely disable any file monitoring
gsettings set org.freedesktop.Tracker.Miner.Files enable-monitors false # Default: true

# cleanup eventual already created db:
tracker reset --hard  # you'll have to confirm Y
# End disable gnome tracker service.


# Enable can_setup service on boot/startup.
sudo systemctl enable can_setup.service
# and start it for this boot cycle.
sudo systemctl start can_setup.service

# Reload mDNS with new service.
sudo service avahi-daemon restart

# Output for docker container logs
sudo mkdir -p /autotrainer/logs

sudo chmod ugo+w /autotrainer/logs

echo "Preparation complete."
