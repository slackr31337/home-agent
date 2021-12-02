"""Functions used to gather metrics and endpoint data"""

import os
import platform
import socket
import distro
import psutil
from psutil._common import bytes2human
from datetime import datetime
from cpuinfo import get_cpu_info
from dmidecode import DMIDecode


from log import LOGGER

LOG_PREFIX = "[Linux]"
########################################################
class AgentPlatform:

    platform = "linux"
    os = "Linux"

    ########################################################
    def __init__(self):
        LOGGER.info("%s Init module", LOG_PREFIX)
        self._dmi = DMIDecode()
        self._uname = platform.uname()
        self._cpuinfo = get_cpu_info()
        self._sysinfo = {}
        self._sensors = {}
        self._attribs = {}
        self._get_system_info()

    ########################################################
    def state(self):
        """Return sysinfo dict"""
        return self._sensors, self._attribs

    ########################################################
    def update(self):
        self._update_system_info()

    ########################################################
    def _get_system_info(self):
        """Build system information and return dict"""

        info = distro.info()
        _name = info.get("id", "Unknown").title()
        _version = info.get("version_parts", info.get("version", ""))
        if "major" in _version:
            if len(_version["minor"]) > 0:
                _version = f"{_version['major']}.{_version['minor']}"
            else:
                _version = _version["major"]

        _release = f"{_name} {_version} ({info.get('codename')})"

        LOGGER.info("[%s] OS: %s", self.platform, _release)

        self._sysinfo = {
            "hostname": self._uname.node,
            "manufacturer": self._dmi.manufacturer(),
            "model": self._dmi.model(),
            "serial": self._dmi.serial_number(),
            "firmware": self._dmi.firmware(),
            "architecture": self._uname.machine,
            "platform": self._uname.system,
            "platform_release": _release,
            "platform_version": self._uname.release,
            "last_boot": get_boot(),
            "processor": self._cpuinfo.get("brand_raw", "Unknown"),
            "processor_cores": psutil.cpu_count(logical=False),
            "processor_threads": psutil.cpu_count(),
        }
        LOGGER.debug(self._sysinfo)
        self._sensors.update(self._sysinfo.copy())

    ########################################################
    def _update_system_info(self):
        """Build system information and return dict"""

        memory_usage = psutil.virtual_memory()
        logins = psutil.users()
        users = 0
        attribs = {}
        for user in logins:
            users += 1
            attribs[user[0]] = user[2]

        self._attribs["users"] = attribs

        _data = {
            "users": users,
            "ip_address": None,
            "ip4_addresses": [],
            "ip6_address": None,
            "ip6_addresses": [],
            "mac_address": None,
            "mac_addresses": [],
            "processor_percent": float(psutil.cpu_percent()),
            "processor_frequency": psutil.cpu_freq()[0],
            "memory_total": bytes2human(memory_usage.total),
            "memory_used": bytes2human(memory_usage.used),
            "memory_percent": float(memory_usage.percent),
        }

        nics = psutil.net_if_addrs()
        nic_stats = psutil.net_if_stats()
        io_counters = psutil.net_io_counters(pernic=True)
        for iface, addrs in nics.items():
            if "lo" in iface:
                continue
            stats = nic_stats[iface]
            nic_io = io_counters[iface]
            _data[f"network_{iface}_up"] = stats.isup
            _data[f"network_{iface}_speed"] = stats.speed
            _data[f"network_{iface}_mtu"] = stats.mtu
            _data[f"network_{iface}_rx"] = bytes2human(nic_io.bytes_recv)
            _data[f"network_{iface}_tx"] = bytes2human(nic_io.bytes_sent)
            _data[f"network_{iface}_drops"] = nic_io.dropin
            _data[f"network_{iface}_errors"] = nic_io.errin

            for addr in addrs:
                LOGGER.debug(
                    "%s iface %s addr: %s (%s)",
                    LOG_PREFIX,
                    iface,
                    addr.address,
                    addr.family,
                )
                _addr = str(addr.address)
                if addr.family == socket.AF_INET:
                    _data["ip4_addresses"].append(_addr)

                elif addr.family == socket.AF_INET6 and not _addr.startswith("fe80::"):
                    _data["ip6_addresses"].append(_addr)

                elif addr.family == socket.AF_PACKET:
                    _data[f"network_{iface}_mac"] = _addr
                    _data["mac_addresses"].append(_addr)

        _data["ip_address"] = next(iter(_data["ip4_addresses"]),"")
        _data["ip6_address"] = next(iter(_data["ip6_addresses"]),"")
        _data["mac_address"] = next(iter(_data["mac_addresses"]), "")

        load1, load5, load15 = os.getloadavg()
        _data["load"] = load1
        self._attribs["load"] = {"load5": load5, "load15": load15}


        for disk in psutil.disk_partitions():
            if "live" in disk.mountpoint:
                continue
            dev = str(disk.device).split("/")[-1]
            key = f"disk_{dev}"
            disk_usage = psutil.disk_usage(disk.mountpoint)
            _data[key] = int(disk_usage.percent)
            self._attribs[key] = {
                "mount": disk.mountpoint,
                "dev": disk.device,
                "total": bytes2human(disk_usage.total),
                "used": bytes2human(disk_usage.used),
            }

        disk_usage = psutil.disk_usage("/")
        _data["disk_root"] = int(disk_usage.percent)
        self._attribs["disk_root"] = {
            "mount": "/",
            "total": bytes2human(disk_usage.total),
            "used": bytes2human(disk_usage.used),
        }

        sensors = psutil.sensors_temperatures()
        for _type, sensors in sensors.items():
            count = 0
            for sensor in sensors:
                if len(sensor.label) == 0:
                    _label = f"Temp {count}"
                else:
                    _label = sensor.label.lower().replace(" ", "_")

                _data[f"{_type}_{_label}"] = int(sensor.current)
                count += 1

        fans = psutil.sensors_fans()
        for _type, _fans in fans.items():
            count = 0
            for fan in _fans:
                _label = fan.label.lower().replace(" ", "_")
                if len(_label) == 0:
                    _label = f"fan_{count}"

                _data[f"{_type}_{_label}"] = int(fan.current)
                count += 1

        battery = psutil.sensors_battery()
        if battery and battery.power_plugged is not None:
            _data["battery_percent"] = int(battery.percent)
            _data["battery_plugged_in"] = battery.power_plugged

        self._sensors.update(_data)

    ########################################################


########################################################
def get_boot():

    boot_time_timestamp = psutil.boot_time()
    bt = datetime.fromtimestamp(boot_time_timestamp)
    return f"{bt.year}-{bt.month}-{bt.day} {bt.hour}:{bt.minute}"


########################################################
