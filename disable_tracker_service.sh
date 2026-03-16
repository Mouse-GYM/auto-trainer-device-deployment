#!/usr/bin/env bash

set -e

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
# first pass: remove all previous Hidden= and empty lines:
for idx in ${!tracker_desktop_files[@]} ; do
  cur_file=${tracker_desktop_files[${idx}]}
  if test -f "${cur_file}" ; then
    sudo sed -i -e '/^Hidden=.*/d' -e '/^$/d' -e '$aHidden=true' "${cur_file}"
    # second pass: append Hidden=true
    sudo sed -i -e '$aHidden=true' "${cur_file}"
  fi
done

# Interval in days to check whether the filesystem is up to date in the database. 0 forces crawling anytime, -1 forces it only after unclean shutdowns, and -2 disables it entirely
gsettings set org.freedesktop.Tracker.Miner.Files crawling-interval -2  # Default: -1
# Set to false to completely disable any file monitoring
gsettings set org.freedesktop.Tracker.Miner.Files enable-monitors false # Default: true

# cleanup eventual already created db:
tracker reset --hard  # you'll have to confirm Y
# End disable gnome tracker service.
