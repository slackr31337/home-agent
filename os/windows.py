"""Functions used to gather MS Windows metrics and endpoint data"""

import platform
import socket
import psutil
from psutil._common import bytes2human
from cpuinfo import get_cpu_info
import wmi


from utilities.log import LOGGER
from utilities.util import get_boot

LOG_PREFIX = "[Windows]"
########################################################
class AgentPlatform:
    _svc_name_ = "HomeAgent"
    _svc_display_name_ = "Home Agent for Home Assistant"
    _svc_description_ = "PC sensors and notifications"
    platform = "windows"
    os = "Windows"

    ########################################################
    def __init__(self, args=None):
        LOGGER.info("%s Init module", LOG_PREFIX)
        self._running = False
        self._wmi = wmi.WMI()
        self._uname = platform.uname()
        self._cpuinfo = get_cpu_info()
        self._sysinfo = {}
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
        return self._sysinfo

    ########################################################
    def update(self):
        return self._update_system_info()

    ########################################################
    def _get_system_info(self):
        """Build system information and return dict"""

        _name = self._uname.system
        _version = self._uname.release
        _codename = self._uname.version
        _release = f"{_name} {_version} ({_codename})"

        LOGGER.info("[%s] OS: %s", self.platform, _release)
        for board_id in self._wmi.Win32_BaseBoard():
            LOGGER.debug(board_id)
            serial = board_id.SerialNumber.strip()

        self._sysinfo = {
            "hostname": self._uname.node,
            # "manufacturer": self._dmi.manufacturer(),
            # "model": self._dmi.model(),
            "serial": serial,
            # "firmware": self._dmi.firmware(),
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
    def _update_system_info(self):
        """Build system information and return dict"""

        memory_usage = psutil.virtual_memory()
        _users = []
        for item in psutil.users():
            _users.append(item.name)

        _data = {
            "users": _users,
            "ip_address": None,
            "ip4_address": [],
            "ip6_address": [],
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
            if "Loopback" in iface:
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
                    _data["ip4_address"].append(_addr)

                elif addr.family == socket.AF_INET6 and not _addr.startswith("fe80::"):
                    _data["ip6_address"].append(_addr)

                elif addr.family == socket.AF_LINK:
                    _data[f"network_{iface}_mac"] = _addr
                    _data["mac_addresses"].append(_addr)

        _data["ip_address"] = next(iter(_data["ip4_address"]), "")
        _data["mac_address"] = next(iter(_data["mac_addresses"]), "")

        _data["disk"] = []
        for disk in psutil.disk_partitions():
            try:
                disk_usage = psutil.disk_usage(disk.mountpoint)
                disk_info = {
                    "mount": disk.mountpoint,
                    "total": bytes2human(disk_usage.total),
                    "used": bytes2human(disk_usage.used),
                    "percent": int(disk_usage.percent),
                }
                _data["disk"].append(disk_info)

            except PermissionError as err:
                pass

        self._sysinfo.update(_data)
        return self._sysinfo
