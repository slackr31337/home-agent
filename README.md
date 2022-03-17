# Home-Agent


This is an endpoint agent for Windows and Linux for collecting metrics for Home-Assistant sensors written in Python.

## Connectors
  - MQTT Client
  - Home-Assistant WS API (In-progress, not working)


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
    
    

# Install Linux
- Pull from master
```
cd /opt
git clone https://github.com/slackr31337/home-agent.git
```

- Add system user
```
sudo adduser --system --home ${DIR} --no-create-home --disabled-login homeagent
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

