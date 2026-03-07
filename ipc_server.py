import asyncio
import websockets
import json
import logging
from jarvis_common.events import JarvisEvent, EventType

logger = logging.getLogger(__name__)

class IPCBridgeServer:
    """
    Gap 3: IPC Bridge Between Voice Agent and Self-Improver
    """
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.subscribers = []

    async def handle_client(self, websocket, path):
        logger.info(f"New IPC connection from {websocket.remote_address}")
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    event = JarvisEvent(**data)
                    logger.debug(f"Received IPC Event: {event.event_type} from {event.source}")
                    
                    # Notify subscribers (like the autopsy engine or dashboard)
                    for sub in self.subscribers:
                        asyncio.create_task(sub(event))
                        
                except Exception as e:
                    logger.error(f"Malformed IPC message: {e}")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            logger.info(f"IPC connection closed from {websocket.remote_address}")

    def subscribe(self, callback):
        self.subscribers.append(callback)

    async def start_server(self):
        logger.info(f"Starting IPC Server on ws://{self.host}:{self.port}")
        await websockets.serve(self.handle_client, self.host, self.port)

# Usage example:
# bridge = IPCBridgeServer()
# asyncio.create_task(bridge.start_server())
