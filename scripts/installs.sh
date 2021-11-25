#!/bin/bash
PY=$(which python3)
DIR=/opt/homeagent
export HOMEAGENT=${DIR}
echo "Debian 11 dependency packages"

sudo apt update
sudo apt install -y dmidecode

# libglib2.0-dev needed to pyler package
sudo apt install -y libglib2.0-dev python3-dbus python3-gi python3-gi-cairo

# Needed for bluetooth sensors
sudo apt install -y rfkill bluez bluez-firmware bluez-hcidump bluez-tools

echo "Adding homeagent user"
sudo adduser --system --home ${DIR} --no-create-home --disabled-login homeagent

${PY} -V
echo "Creating virtualenv in ${DIR}"
cd ${DIR}

${PY} -m venv env
source env/bin/activate
${PY} -m pip install -r requirements.txt

deactivate



