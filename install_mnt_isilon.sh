#!/usr/bin/env bash

set -e

mkdir -p /mnt/isilon
# first pass: remove any previous matching line:
sed -i -e '/\/\/data.ucdenver.pvt\/dept\/SOM\/PHYS\/ChristieLab /d' /etc/fstab
# second pass: add desired mount:
sed -i -e '$a//data.ucdenver.pvt/dept/SOM/PHYS/ChristieLab /mnt/isilon cifs vers=2.0,credentials=/etc/credentials,file_mode=0777,dir_mode=0777,noauto,x-systemd.automount,x-systemd.idle-timeout=1h 0 0' /etc/fstab

systemctl daemon-reload

systemctl restart remote-fs.target || true  # may fail if access denied, for instance

echo "Assuming /etc/credentials is populated and has correct permission, now doing ls /mnt/isilon should work"
