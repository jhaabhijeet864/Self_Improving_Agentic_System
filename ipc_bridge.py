"""
IPC Bridge - Windows Named Pipe for Swara AI to Jarvis-OS Communication
Allows external processes (like Swara) to stream SessionEvents directly into Jarvis core.
"""

import asyncio
import json
import logging
import win32pipe
import win32file
import pywintypes
import struct
from pydantic import ValidationError

from jarvis_common import SessionEvent

logger = logging.getLogger(__name__)

class IPCBridge:
    def __init__(self, agent=None, pipe_name: str = r"\\.\pipe\jarvis_ipc"):
        self.pipe_name = pipe_name
        self.agent = agent
        self.running = False
        
    async def start(self):
        """Start the IPC Bridge Named Pipe server in a background task."""
        self.running = True
        loop = asyncio.get_running_loop()
        loop.create_task(self._listen_loop())
        logger.info(f"IPC Bridge started listening on {self.pipe_name}")

    async def stop(self):
        self.running = False

    async def _listen_loop(self):
        """Infinite loop to accept clients."""
        while self.running:
            try:
                # Create the named pipe
                pipe = win32pipe.CreateNamedPipe(
                    self.pipe_name,
                    win32pipe.PIPE_ACCESS_DUPLEX | win32file.FILE_FLAG_OVERLAPPED,
                    win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
                    win32pipe.PIPE_UNLIMITED_INSTANCES, 65536, 65536,
                    0,
                    None
                )
                
                # Wait for client in a non-blocking way using thread pool
                await asyncio.to_thread(win32pipe.ConnectNamedPipe, pipe, None)
                
                # Handle client in background task
                loop = asyncio.get_running_loop()
                loop.create_task(self._handle_client(pipe))
                
            except Exception as e:
                logger.error(f"Error creating named pipe: {e}")
                await asyncio.sleep(1.0)
                
    async def _handle_client(self, pipe):
        """Handle a connected Swara AI IPC client."""
        logger.info("New IPC Client Connected.")
        try:
            while self.running:
                # Read header (4 bytes message length) - in a thread to unblock
                hr, data = await asyncio.to_thread(
                    win32file.ReadFile, pipe, 65536
                )
                if hr != 0 or not data:
                    break
                    
                raw_json = data.decode('utf-8')
                try:
                    event_dict = json.loads(raw_json)
                    event = SessionEvent(**event_dict)
                    
                    logger.info(f"Received IPC Event from {event.source}: {event.event_type}")
                    
                    # Forward into Jarvis-OS if agent is bound
                    if self.agent and self.agent.running:
                        # Schedule task submission
                        asyncio.create_task(self._route_event_to_jarvis(event))
                        
                except (json.JSONDecodeError, ValidationError) as e:
                    logger.error(f"Malformed IPC Payload received: {e}")
                    
        except pywintypes.error as e:
            # 109 = ERROR_BROKEN_PIPE (Client disconnected normally)
            if e.winerror != 109:
                logger.error(f"IPC Client error: {e}")
        finally:
            logger.info("IPC Client Disconnected.")
            win32file.CloseHandle(pipe)
            
    async def _route_event_to_jarvis(self, event: SessionEvent):
        """Pass the Pydantic SessionEvent directly into Jarvis task executor."""
        # Wrap it up as an internal Jarvis-OS task
        async def ipc_task():
            return {"status": "event_processed", "event_id": event.event_id}
            
        await self.agent.execute_task(
            task_type=f"ipc:{event.event_type}",
            task_func=ipc_task,
            task_params={"event": event.dict()}
        )
