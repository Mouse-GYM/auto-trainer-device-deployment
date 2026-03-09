#!/usr/bin/env bash

(
  cd ./system-install
  sudo rsync -av --chown root:root ./ /
)
