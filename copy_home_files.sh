#!/usr/bin/env bash

(
  cd ./home-install
  rsync -av ./ "${HOME}/"
)
