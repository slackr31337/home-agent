"""Functions used to gather metrics and endpoint data"""

import os
import platform
import socket
import distro
import psutil
from psutil._common import bytes2human
from cpuinfo import get_cpu_info
from dmidecode import DMIDecode


from service.log import LOGGER
from service.util import get_boot
from device.raspberrypi import RaspberryPi

SKIP_MOUNTS = ["live", "docker", "subvol", "tmp"]
LOG_PREFIX = "[Linux]"
##########################################
class AgentPlatform:
    """OS Module for Linux"""

    platform = "linux"
    os = "Linux"
    hardware = "pc"

    ##########################################
    def __init__(self):
        LOGGER.info("%s Init module", LOG_PREFIX)
        self._uname = platform.uname()
        self._cpuinfo = get_cpu_info()
        self._sysinfo = {}
        self._sensors = {}
        self._attribs = {}
        self._hardware = None
        self._get_system_info()

    ##########################################
    def state(self):
        """Return sysinfo dict"""
        return self._sensors, self._attribs

    ##########################################
    def update(self):
        """Poll system sensors"""
        self._update_system_info()

    ##########################################
    def _get_system_info(self) -> dict:
        """Build system information and return dict"""
        arch = self._cpuinfo.get("arch")
        if "ARM" in arch:
            self._hardware = RaspberryPi()
            self.hardware = "raspberrypi"
        else:
            self._hardware = DMIDecode()

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
            "manufacturer": self._hardware.manufacturer(),
            "model": self._hardware.model(),
            "serial": self._hardware.serial_number(),
            "firmware": self._hardware.firmware(),
            "architecture": self._uname.machine,
            "platform": self._uname.system,
            "platform_release": _release,
            "platform_version": self._uname.release,
            "last_boot": get_boot(),
            "processor": self._cpuinfo.get("brand_raw", self._uname.processor),
            "processor_cores": psutil.cpu_count(logical=False),
            "processor_threads": psutil.cpu_count(),
        }
        LOGGER.debug(self._sysinfo)
        self._sensors.update(self._sysinfo.copy())

    ##########################################
    def _update_system_info(self) -> dict:
        """Build system information and return dict"""

        logins = psutil.users()
        users = 0
        attribs = {}
        for user in logins:
            users += 1
            host = user.host
            if len(host) == 0:
                host = "localhost"
            attribs[user.terminal] = f"{user.name}@{host}"

        self._attribs["users"] = attribs

        memory_usage = psutil.virtual_memory()
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

        self._attribs["processor_percent"] = {
            "frequency": f"{int(psutil.cpu_freq()[0])} Mhz"
        }

        self._attribs["memory_percent"] = {
            "total": bytes2human(memory_usage.total),
            "used": bytes2human(memory_usage.used),
        }

        nics = psutil.net_if_addrs()
        nic_stats = psutil.net_if_stats()
        io_counters = psutil.net_io_counters(pernic=True)
        for iface, addrs in nics.items():
            if "lo" in iface:
                continue

            stats = nic_stats[iface]
            nic_io = io_counters[iface]
            if "." in iface:
                iface = iface.replace(".", "_")

            key = f"network_{iface}"
            _data[key] = "Up" if stats.isup else "Down"

            self._attribs[key] = {
                "speed": stats.speed,
                "mtu": stats.mtu,
                "drops": nic_io.dropin,
                "errors": nic_io.errin,
                "received": bytes2human(nic_io.bytes_recv),
                "sent": bytes2human(nic_io.bytes_sent),
            }

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
                    self._attribs[key]["ipv4"] = _addr

                elif addr.family == socket.AF_INET6 and not _addr.startswith("fe80::"):
                    _data["ip6_addresses"].append(_addr)
                    self._attribs[key]["ipv6"] = _addr

                elif addr.family == socket.AF_PACKET:
                    # _data[f"network_{iface}_mac"] = _addr
                    _data["mac_addresses"].append(_addr)
                    self._attribs[key]["mac"] = _addr

        _data["ip_address"] = next(iter(_data["ip4_addresses"]), "")
        _data["ip6_address"] = next(iter(_data["ip6_addresses"]), "")
        _data["mac_address"] = next(iter(_data["mac_addresses"]), "")

        load1, load5, load15 = os.getloadavg()
        _data["load"] = load1
        self._attribs["load"] = {"load5": load5, "load15": load15}

        for disk in psutil.disk_partitions():
            if any(item in str(disk.mountpoint) for item in SKIP_MOUNTS):
                continue
            dev = str(disk.device).split("/", maxsplit=10)[-1]
            key = f"disk_{dev}"
            disk_usage = psutil.disk_usage(disk.mountpoint)
            _data[key] = int(disk_usage.percent)
            self._attribs[key] = {
                "mount": disk.mountpoint,
                "dev": disk.device,
                "fstype": disk.fstype,
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
                    _label = f"temp_{count}"
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
