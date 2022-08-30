#!/bin/bash
PY=$(which python3)
DIR=/opt/home-agent
export HOMEAGENT=${DIR}


echo "Intalling Debian 11 dependency packages"

sudo apt update
sudo apt install -y python3 python3-virtualenv python3-venv dmidecode

${PY} -V

# libglib2.0-dev needed for pyler package
sudo apt install -y libglib2.0-dev python3-dbus python3-gi python3-gi-cairo

# Needed for bluetooth sensors
#sudo apt install -y rfkill bluez bluez-firmware bluez-hcidump bluez-tools
sudo apt install bluetooth bluez libbluetooth-dev libudev-dev

echo "Adding homeagent user"
sudo adduser --system --home ${DIR} --no-create-home --disabled-login homeagent
sudo addgroup homeagent
sudo usermod -aG bluetooth homeagent
sudo usermod -aG sudo homeagent
mkdir /home/homeagent
chmod 770 /home/homeagent

echo "Cloning home-agent into /opt"
cd /opt

git clone https://github.com/slackr31337/home-agent.git


chown homeagent ${DIR}


echo "Creating virtualenv in ${DIR}"
cd home-agent
${PY} -m venv env
source env/bin/activate
${PY} -m pip install -r requirements.txt
deactivate

echo "Running patch_dmidecode.sh"
${DIR}/scripts/patch_dmidecode.sh

sudo cp ${DIR}/systemd/home-agent.service /lib/systemd/system/home-agent.service
sudo systemctl daemon-reload

