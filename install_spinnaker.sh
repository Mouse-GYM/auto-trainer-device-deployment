#!/usr/bin/env bash

set -e

_spinnaker_version="3.2.0.62"

# goto this-script directory:
cd "$(dirname "${0}")"

cd spinnaker

extract_dir="spinnaker-${_spinnaker_version}-arm64"

rm -rf "${extract_dir}"

tar xzf "spinnaker-${_spinnaker_version}-arm64-pkg.20.04.tar.gz"

cd "${extract_dir}"

./remove_spinnaker_arm.sh

echo "Pre-installing qt5-default required by spinnaker configure but not depended on .."
sudo apt-get install -y qt5-default

./install_spinnaker_arm.sh
