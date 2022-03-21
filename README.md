# Home-Agent

This is an endpoint agent for Windows and Linux for collecting metrics for Home-Assistant sensors written in Python.

## Description

I wanted to have the ability to connect my servers and computers to [Home-Assistant](https://www.home-assistant.io/). Collect sesnor data, call services and trigger notifications right on my desktop. 

Test endpoints:
  - HP Laptop
  - ASUS Server
  - Raspberry Pi 3 (My Car)
      - GeeekPi 4 Channel Relay Board HAT [link](https://wiki.52pi.com/index.php/EP-0099)
      - Sixfab 4G LTE/GPS HAT [link](https://sixfab.com/hardware/)
      - Pisugar 2 Pro UPS/RTC [link](https://github.com/PiSugar/PiSugar)
      - USB to CAN module [amazon link](https://www.amazon.com/gp/product/B07P9JGXXB/)


## Connectors

  - MQTT Client
  - Home-Assistant WS API (In-progress, not working yet)


## Sensors

  - OS Info
  - CPU
  - Memory
  - Disk
  - Network
  - Hardware sensors
  - Laptop battery
  - Device tracker
  - OS Users
  

  # Linux
  
    - X11 screen idle state and screen capture
    - Desktop notifications
    - Media Player and audio states
    - More ToDo
    
  # Windows
  
    - Screen idle state and screen capture
    - More ToDo
    
    
    
## Dependencies

A Home-Assistant install (https://www.home-assistant.io/installation/)

Mosquitto MQTT Server (https://mosquitto.org/)

Python3 (3.9+ preferred)
- paho-mqtt or hass_client
- pyler
- mss


# Install Linux
- Pull from master
```
cd /opt
git clone https://github.com/slackr31337/home-agent.git
```

- Add system user
```
sudo adduser --system --home /opt/home-agent --no-create-home --disabled-login homeagent
sudo addgroup homeagent
chown homeagent /opt/home-agent
```

- Create python virtual env 
```
cd home-agent
python3 -m venv env
source env/bin/activate
python3 -m pip install -r requirements.txt
deactivate
```

- Create config.yaml from example
```
  #Home Assistant connector. mqtt or api
  connector: mqtt
  
  # MQTT host, port and auth
  mqtt:
    host: mqtt.host.local
    port: 1883
    user: "mqtt"
    password: "secret_password"

  #Device name in Home Assistant
  host:
    friendly_name: "My Laptop"

  #Map location network to key
  device_tracker:
    home: "192.168.1.0/24"
    work: "192.168.2.0/24"

  #Map location key to name
  locations:
    home: "home"
    work: "My Work"

```


## Running home-agent
```
cd /opt/home-agent
user@laptop:/opt/home-agent$ source env/bin/activate
(env) user@laptop:/opt/home-agent$ 

(env) user@laptop:/opt/home-agent$ python3 run.py -h
[            run.py:               main()]  INFO Starting Home Agent endpoint
usage: run.py [-h] [-c CONFIG] [-s] [-d]

Home Agent endpoint

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Set config.yaml file
  -s, --service         Run as service
  -d, --debug           Turn on DEBUG logging

(env) user@laptop:/opt/home-agent$ python3 run.py -s -c secrets.yaml 
[            run.py:               main()]  INFO Starting Home Agent endpoint
[            run.py:               main()]  INFO [HomeAgent] Loading config file: secrets.yaml
[            run.py:        run_service()]  INFO [HomeAgent] is starting
[          agent.py:         _os_module()]  INFO [HomeAgent] Loading OS module: linux
[          linux.py:           __init__()]  INFO [Linux] Init module
[          linux.py:   _get_system_info()]  INFO [linux] OS: Debian 11 (bullseye)
[          agent.py:  _connector_module()]  INFO [HomeAgent] Loading connector module: mqtt
[           mqtt.py:              setup()]  INFO [MQTT] Setup MQTT client homeagent_laptop_1647535914
[           mqtt.py:              setup()]  INFO [MQTT] Using TLS connection with TLS_CA_CERT: /etc/ssl/certs/ca-certificates.crt
[          agent.py:  _connector_module()]  INFO [HomeAgent] Connector subscribe: homeassistant/status
[          agent.py:  _connector_module()]  INFO [HomeAgent] Connector subscribe: devices/laptop/command
[          agent.py:  _connector_module()]  INFO [HomeAgent] Connector subscribe: devices/laptop/event
[          agent.py:  _connector_module()]  INFO [HomeAgent] Connector subscribe: devices/laptop/status
[           mqtt.py:              start()]  INFO [MQTT] Starting connector to Home-Assistant
[           mqtt.py:            connect()]  INFO [MQTT] Connecting to mqtt.server.local:8883 (attempt 1)
[           mqtt.py:    mqtt_on_connect()]  INFO [MQTT] Connected mqtt://mqtt.server.local:8883
[           mqtt.py:    mqtt_on_connect()]  INFO [MQTT] Subscribing to homeassistant/status
[           mqtt.py:    mqtt_on_connect()]  INFO [MQTT] Subscribing to devices/laptop/command
[           mqtt.py:    mqtt_on_connect()]  INFO [MQTT] Subscribing to devices/laptop/event
[           mqtt.py:    mqtt_on_connect()]  INFO [MQTT] Subscribing to devices/laptop/status
[          agent.py:  _connector_module()]  INFO [HomeAgent] Connector is connected: True

...
```

## Running systemd service
```
cp /opt/home-agent/systemd/home-agent.service /lib/systemd/system/
systemctl enable home-agent
systemctl start home-agent
```

```
rob@slackRMobileLTE:/opt/home-agent# systemctl status home-agent.service 
● homeagent.service - Home-agent Endpoint Service
     Loaded: loaded (/lib/systemd/system/homeagent.service; enabled; vendor preset: enabled)
     Active: active (running) since Thu 2022-03-17 12:24:25 GMT; 4h 22min ago
   Main PID: 6023 (python3)
      Tasks: 3 (limit: 2178)
        CPU: 17min 9.183s
     CGroup: /system.slice/homeagent.service
             └─6023 /opt/home-agent/env/bin/python3 /opt/home-agent/run.py -s -c /opt/home-agent/secrets.yaml

```


## Home-Assistant MQTT Device
![home-assistant-device1](https://github.com/slackr31337/home-agent/blob/main/screenshots/home-assistant-device1.jpg?raw=true)

![home-assistant-device2](https://github.com/slackr31337/home-agent/blob/main/screenshots/home-assistant-server02.jpg?raw=true)


## Authors

Robert Dunmire III @slackr31337 slackr31337@gmail.com

## Version History

* 0.0.1-alpha1
  * Inital Release


## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details
