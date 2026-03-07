import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
import uvicorn
import asyncio
from dashboard_api import app

class JarvisImproverService(win32serviceutil.ServiceFramework):
    """
    Gap 16: Windows Service / Daemon Mode
    Runs the Jarvis Self-Improver dashboard as a background Windows service.
    """
    _svc_name_ = "JarvisSelfImprover"
    _svc_display_name_ = "Jarvis Self-Improvement Engine"
    _svc_description_ = "Background daemon for the Jarvis Self-Improvement project"

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
            (self._svc_name_, '')
        )
        self.main()

    def main(self):
        # We start the uvicorn server in a separate thread/process or loop
        # Since uvicorn.run is blocking, we can just call it
        try:
            uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)
        except Exception as e:
            servicemanager.LogInfoMsg(f"JarvisImproverService failed: {str(e)}")

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(JarvisImproverService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(JarvisImproverService)
