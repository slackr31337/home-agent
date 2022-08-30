#!/bin/bash

. ./scripts/envvars.sh
cd ${HOMEAGENT}
VER=$(python3 -c 'import sys; print(str(sys.version_info[0])+"."+str(sys.version_info[1]))')
FILE=env/lib/python${VER}/site-packages/dmidecode.py
sudo sed -i 's:subprocess.Popen(self.dmidecode:subprocess.Popen(["/usr/bin/sudo", self.dmidecode]:' $FILE
echo "patched ${FILE}"

FILE=/usr/local/lib/python${VER}/dist-packages/dmidecode.py
sudo sed -i 's:subprocess.Popen(self.dmidecode:subprocess.Popen(["/usr/bin/sudo", self.dmidecode]:' $FILE
echo "patched ${FILE}"
