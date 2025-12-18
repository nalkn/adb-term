#!/bin/sh

set -e


# upgrade packages
echo "[*] Upgrade packages"
sudo apt update && sudo apt upgrade -y


# check / install python3
apt install python3 -y


# install tools
echo "[*] Install platform-tools and build-tools"
apt install android-sdk-platform-tools android-sdk-build-tools -y


# create python venv and install requirements
echo "[*] Create python virtual env"
python3 -m venv .venv
source .venv/bin/activate

echo "[*] Install python requirements"
pip install -r requirements.txt
