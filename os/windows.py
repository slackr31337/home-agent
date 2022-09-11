"""Functions used to gather MS Windows metrics and endpoint data"""

import platform
import socket
import psutil
from psutil._common import bytes2human
from cpuinfo import get_cpu_info
import wmi


from service.log import LOGGER
from service.util import get_boot

LOG_PREFIX = r"[Windows]"
########################################################
class AgentPlatform:
    """OS Module for Windows"""

    _svc_name_ = "HomeAgent"
    _svc_display_name_ = "Home Agent for Home Assistant"
    _svc_description_ = "PC sensors and notifications"

    platform = "windows"
    os = "Windows"

    ########################################################
    def __init__(self):
        LOGGER.info("%s Init module", LOG_PREFIX)
        self._running = False
        self._wmi = wmi.WMI()
        self._uname = platform.uname()
        self._cpuinfo = get_cpu_info()
        self._sysinfo = {}
        self._attribs = {}
        self._get_system_info()

    ########################################################
    def start(self):
        """Set running"""
        self._running = True

    ########################################################
    def stop(self):
        """Set running"""
        self._running = False

    ########################################################
    def state(self):
        """Return sysinfo dict"""
        return self._sysinfo, self._attribs

    ########################################################
    def update(self):
        """Poll sensor data"""
        return self._update_system_info()

    ########################################################
    def _get_system_info(self):
        """Build system information and return dict"""

        _name = self._uname.system
        _version = self._uname.release
        _codename = self._uname.version
        _release = f"{_name} {_version} ({_codename})"
        LOGGER.info("[%s] OS: %s", self.platform, _release)

        board_id = self._wmi.Win32_BaseBoard()[0]
        self._sysinfo = {
            "hostname": str(self._uname.node).lower(),
            "manufacturer": board_id.Manufacturer,
            "model": board_id.Product,
            "serial": board_id.SerialNumber.strip(),
            "firmware": board_id.Version.split()[-1],
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

    ########################################################
    def _update_system_info(self)->dict:
        """Build system information and return dict"""

        users = 0
        attribs = {}
        logins = psutil.users()
        for user in logins:
            LOGGER.debug(user)
            users += 1
            host = user.host
            if not host or len(host) == 0:
                host = "localhost"
            term = user.terminal
            if not term:
                term = f"desktop{users}"
            attribs[term] = f"{user.name}@{host}"

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
            "frequency": f"{int(psutil.cpu_freq()[0])} Mhz",
            "cores": psutil.cpu_count(logical=False),
            "threads": psutil.cpu_count(),
        }

        self._attribs["memory_percent"] = {
            "total": bytes2human(memory_usage.total),
            "used": bytes2human(memory_usage.used),
        }

        nics = psutil.net_if_addrs()
        nic_stats = psutil.net_if_stats()
        io_counters = psutil.net_io_counters(pernic=True)
        for iface, addrs in nics.items():
            if "Loopback" in iface:
                continue
            stats = nic_stats[iface]
            nic_io = io_counters[iface]
            if "." in iface:
                iface = iface.replace(".", "_")

            key = f"network_{iface}".lower()
            _data[key] = "Up" if stats.isup else "Down"

            self._attribs[key] = {
                "name": iface,
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

                elif "AF_INET6" in str(addr.family) and not _addr.startswith("fe80::"):
                    _data["ip6_addresses"].append(_addr)
                    self._attribs[key]["ipv6"] = _addr

                elif "AF_LINK" in str(addr.family):
                    _addr = _addr.replace("-", ":")
                    _data[f"network_{iface}_mac"] = _addr
                    _data["mac_addresses"].append(_addr)
                    self._attribs[key]["mac"] = _addr

        _data["ip_address"] = next(iter(_data["ip4_addresses"]), "")
        _data["ip6_address"] = next(iter(_data["ip6_addresses"]), "")
        _data["mac_address"] = next(iter(_data["mac_addresses"]), "")

        for disk in psutil.disk_partitions():
            try:
                dev = str(disk.mountpoint).split(":", maxsplit=1)[0].lower()
                key = f"disk_{dev}"
                disk_usage = psutil.disk_usage(disk.mountpoint)
                _data[key] = int(disk_usage.percent)
                self._attribs[key] = {
                    "mount": disk.mountpoint,
                    "fstype": disk.fstype,
                    "total": bytes2human(disk_usage.total),
                    "used": bytes2human(disk_usage.used),
                }
            except PermissionError:
                pass

        self._sysinfo.update(_data)
        return self._sysinfo
