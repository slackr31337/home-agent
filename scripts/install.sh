#!/bin/bash
PY=$(which python3)
DIR=/opt/home-agent
export HOMEAGENT=${DIR}


echo "Intalling Debian 11 dependency packages"

sudo apt update
sudo apt install -y python3 dmidecode

${PY} -V

# libglib2.0-dev needed to pyler package
sudo apt install -y libglib2.0-dev python3-dbus python3-gi python3-gi-cairo

# Needed for bluetooth sensors
#sudo apt install -y rfkill bluez bluez-firmware bluez-hcidump bluez-tools
sudo apt-get install bluetooth bluez libbluetooth-dev libudev-dev


echo "Cloning home-agent into /opt"
cd /opt

git clone https://github.com/slackr31337/home-agent.git

cd home-agent

echo "Creating virtualenv in ${DIR}"
${PY} -m venv env
source env/bin/activate
${PY} -m pip install -r requirements.txt
deactivate


echo "Adding homeagent user"
sudo adduser --system --home ${DIR} --no-create-home --disabled-login homeagent
sudo usermod -aG bluetooth homeagent

chown homeagent:homeagent /opt/home-agent

