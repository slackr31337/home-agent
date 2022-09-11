#!/bin/bash

patch_file () {
    if [ -f "${1}" ]; then
        sudo sed -i 's:subprocess.Popen(self.dmidecode:subprocess.Popen(["/usr/bin/sudo", self.dmidecode]:' ${1}
        echo "patched ${1}"
    fi
}

. ./scripts/envvars.sh
cd ${HOMEAGENT}

VER=$(python3 -c 'import sys; print(str(sys.version_info[0])+"."+str(sys.version_info[1]))')

for prefix in env /usr /usr/local;do
    patch_file "${prefix}/lib/python${VER}/site-packages/dmidecode.py"
done
