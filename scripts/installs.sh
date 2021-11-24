#!/bin/bash
PY=$(which python3)
DIR=/opt/homeagent

echo "Debian 11 dependency packages"

apt update
# libglib2.0-dev needed to pyler package
apt install libglib2.0-dev python3-dbus python3-gi python3-gi-cairo

# Needed for bluetooth sensors
apt install rfkill bluez bluez-firmware bluez-hcidump bluez-tools

echo "Adding homeagent user"
adduser --system --home ${DIR} --no-create-home --disabled-login homeagent

${PY} -V
echo "Creating virtualenv in ${DIR}"
cd ${DIR}
${PY} -m venv env




