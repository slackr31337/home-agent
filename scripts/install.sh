#!/bin/bash
PY=$(which python3)
THIS_USER=$(whoami)
DIR=/opt/home-agent
USER=homeagent

if [[ -L "${DIR}" ]];then
    DIR=$(readlink -f ${DIR})
fi
export HOMEAGENT=${DIR}

echo "##########################################"
echo "Using base dir ${DIR}"


echo "Intalling Debian 11 dependency packages"
echo ""

if [ ! -d "/home/${USER}" ];then
    echo "Adding user ${USER}"

    sudo adduser --system --home ${DIR} --no-create-home --disabled-login ${USER}
    sudo addgroup ${USER}
    sudo usermod -aG bluetooth ${USER}
    sudo usermod -aG sudo ${USER}

    sudo mkdir -p /home/${USER} /home/${USER}/.config
    #if [ -d "${HOME}/.config/pulse" ]; then
    #    sudo cp -rf ${HOME}/.config/pulse /home/${USER}/.config/
    #fi 

    sudo chmod 775 /home/${USER}
    sudo chown -R ${USER}:${USER} /home/${USER}
    #sudo chmod 660 ~/.config/pulse/*
    
fi 

if [ -f "/etc/pulse/client.conf" ]; then
    sudo sed -i "s:; autospawn :autospawn :" /etc/pulse/client.conf
    sudo mkdir -p /home/${USER}/.pulse
    sudo chown -R ${USER}:${USER} /home/${USER}
fi


sudo apt update
sudo apt install -y sudo python3 python3-virtualenv python3-venv dmidecode

# libglib2.0-dev needed for pyler package
sudo apt install -y libglib2.0-dev python3-dbus python3-gi python3-gi-cairo

# Needed for audio sensors
sudo apt install -y libasound2-dev
python3 -m pip install pyalsaaudio

# Needed for bluetooth sensors
# sudo apt install -y rfkill bluez bluez-firmware bluez-hcidump bluez-tools
sudo apt -y install bluetooth bluez libbluetooth-dev libudev-dev

echo "##########################################"
cd $(dirname "${DIR}")
echo ""

if [ ! -d "${DIR}" ];then
    echo "Cloning home-agent into $(pwd)"
    #git clone https://github.com/slackr31337/home-agent.git
fi

echo "##########################################"
echo "Creating virtualenv in ${DIR}"
${PY} -V
echo ""

cd ${DIR}
if [ ! -d "${DIR}/env" ];then
    rm -rf env
fi

${PY} -m venv env
source env/bin/activate
${PY} -m pip install -r requirements.txt
deactivate

echo "##########################################"
echo "Running patch_dmidecode.sh"
echo ""
${DIR}/scripts/patch_dmidecode.sh



echo "##########################################"
echo "Updating .env"
if [ -f ".env.sh" ];then
    rm .env.sh
    echo ""
fi 
cp ./scripts/envvars.sh .env
sed -i "s:^HOMEAGENT=.*$:HOMEAGENT=${DIR}:" .env

if [ ! -f "/lib/systemd/system/home-agent.service" ];then
    TMP_FILE=/tmp/home-agent.service
    cp ${DIR}/systemd/home-agent.service ${TMP_FILE}
    sed -i "s:/opt/home-agent:${DIR}:" ${TMP_FILE}
    sed -i "s:python3:${PY}:" ${TMP_FILE}
    sudo cp ${TMP_FILE} /lib/systemd/system/home-agent.service
    rm ${TMP_FILE}
    sudo systemctl daemon-reload
    sudo systemctl enable home-agent
    echo "Added systemd service 'home-agent'"
fi
echo ""

#sudo chown -R ${USER} ${DIR}
sudo chown -R :${USER} ${DIR}

if [ ! -f "/etc/sudoers.d/homeagent" ];then
    echo "##########################################"
    echo "Adding sudoers file to /etc/sudoers.d/"
    sudo echo "homeagent ALL=(ALL) NOPASSWD: $(which dmidecode)" > /etc/sudoers.d/homeagent
fi 
echo ""


sudo xhost +

echo "##########################################"
echo "To start run: 'systemctl start home-agent'"
echo ""

systemctl start home-agent
sleep 1

systemctl status home-agent
echo ""


