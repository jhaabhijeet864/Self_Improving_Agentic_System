"""
Win32 Daemon Service Wrapper for Jarvis-OS
Allows Jarvis-OS to run as a native Windows Service in the background.

To install/run:
python win32_daemon.py install
python win32_daemon.py start
"""
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import logging
import asyncio
import sys
import os

from jarvis_os_init import initialize_jarvis
from dashboard_api import app

class JarvisOSService(win32serviceutil.ServiceFramework):
    _svc_name_ = 'JarvisOS_Daemon'
    _svc_display_name_ = 'Jarvis-OS Core Agent Daemon'
    _svc_description_ = 'Runs the Jarvis-OS orchestrator, dashboard, and IPC bridge.'

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.agent = None

    def SvcStop(self):
        """Called by Windows Service Manager to stop the service."""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        if self.agent:
            asyncio.run(self.agent.stop())

    def SvcDoRun(self):
        """Called by Windows Service Manager to start the service."""
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.main()

    def main(self):
        """Synchronous main block running inside the service thread."""
        try:
            # We must use asyncio.run to launch our async system
            asyncio.run(self.async_main())
        except Exception as e:
            servicemanager.LogErrorMsg(f"JarvisOS failed to start: {e}")

    async def async_main(self):
        """Starts the Jarvis Agent and the FastAPI Dashboard."""
        import uvicorn
        
        # 1. Initialize
        self.agent = await initialize_jarvis()
        
        # We need to bind the agent to the global dashboard scope
        import dashboard_api
        dashboard_api.agent = self.agent
        
        # 2. Run Uvicorn dashboard server asynchronously
        config = uvicorn.Config(app=dashboard_api.app, host="0.0.0.0", port=8000, log_level="info")
        server = uvicorn.Server(config)
        
        # Run server concurrently with our agent
        server_task = asyncio.create_task(server.serve())
        
        # 3. Wait until told to stop by Windows Service Manager
        while True:
            rc = win32event.WaitForSingleObject(self.hWaitStop, 1000)
            if rc == win32event.WAIT_OBJECT_0:
                # Stop signal received
                break
                
        # Graceful shutdown
        server.should_exit = True
        await server_task
        await self.agent.stop()

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(JarvisOSService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(JarvisOSService)
