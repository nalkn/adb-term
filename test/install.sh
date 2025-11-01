#!/bin/sh

set -e


# upgrade packages
echo "[*] Upgrade packages"
sudo apt update && sudo apt upgrade


# install platform-tools
echo "[*] Install platform-tools"
...

# install build-tools
echo "[*] Install build-tools"
...


# create python venv and install requirements
echo "[*] Create python virtual env"
python -m venv .venv
source .venv/scrips/activate

echo "[*] Install python requirements"
pip install -r requirements.txt
