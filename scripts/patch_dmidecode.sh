#!/bin/bash
VER=$(python -c 'import sys; print(str(sys.version_info[0])+"."+str(sys.version_info[1]))')
. envvars.sh
FILE=${HOMEAGENT}/env/lib/python${VER}/site-packages/dmidecode.py
sed -i 's:subprocess.Popen(self.dmidecode:subprocess.Popen(["/usr/bin/sudo", self.dmidecode]:' $FILE
