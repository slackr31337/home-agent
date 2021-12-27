"""Windows service for Home Agent"""
# pylint: skip-file
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket

from run import main as run_main

#########################################
class AppServerSvc(win32serviceutil.ServiceFramework):
    _svc_name_ = "HomeAgent"
    _svc_display_name_ = "Home Agent service for Home Assistant"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )
        self.main()

    def main(self):
        run_main()


#########################################
if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(AppServerSvc)
