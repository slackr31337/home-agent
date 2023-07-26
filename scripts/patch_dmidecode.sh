#!/bin/bash
PY_BIN=$(which python3)
PY_VER=$(${PY_BIN} -c 'import sys; print(str(sys.version_info[0])+"."+str(sys.version_info[1]))')

patch_file () {
    if [ -f "${1}" ]; then
        sudo sed -i 's:subprocess.Popen(self.dmidecode:subprocess.Popen(["/usr/bin/sudo", self.dmidecode]:' ${1}
        echo "patched ${1}"
    fi
}

. ./scripts/envvars.sh
cd ${HOMEAGENT}

for prefix in env /usr /usr/local;do
	PATCH_FILE="${prefix}/lib/python${PY_VER}/dist-packages/dmidecode.py"

	if [[ -f "${PATCH_FILE}" ]];then
		echo "Patching ${PATCH_FILE}"
    		sudo sed -i 's:subprocess.Popen(self.dmidecode:subprocess.Popen(["/usr/bin/sudo", self.dmidecode]:' \
    		${PATCH_FILE}
    	fi
done
