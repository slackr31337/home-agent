#!/bin/bash

HOST=$(hostname)
MQTT=$(which mosquitto_pub)
OPTIONS="-d --capath /etc/ssl/certs -h ha.rd3s.com -p 8883"

publish() {
	echo "Publish: $1 $2"
	${MQTT} ${OPTIONS} -t $1 -m "$2"
}

if [ "${1}" == "pre" ]; then
	publish "devices/${HOSTNAME}/availability" "offline"

elif [ "${1}" == "post" ]; then
	publish "devices/${HOSTNAME}/availability" "online"

fi


