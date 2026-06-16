#!/usr/bin/env bash

(
  cd ./home-install
  rsync -av ./ "${HOME}/"
)

echo "Modifying .bashrc to source ~/.load_autotrainer_env.sh"
sed -i '\|. ~/.load_autotrainer_env.sh|d' ~/.bashrc  # first pass: remove
sed -i -e '$a\\n. ~/.load_autotrainer_env.sh' ~/.bashrc  # second pass: add at the end
