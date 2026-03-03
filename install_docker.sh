#!/usr/bin/env bash

set -e

# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt-get update

sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# it's supposed to be available in base nvidia ubuntu install :
sudo apt-get install -y nvidia-container-toolkit

sudo adduser "${USER}" docker  # add user to docker group

sudo systemctl restart docker

echo "You can now use docker with gpu, using '--runtime nvidia --gpus all' args to docker run command, for instance"
echo "But you need to logout/login for docker group membership to take effect."
