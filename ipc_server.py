import asyncio
import websockets
import json
import logging
from jarvis_common.events import JarvisEvent, EventType
from jarvis_common.schemas import Directive

logger = logging.getLogger(__name__)

class IPCBridgeServer:
    """
    Gap 3 & Phase 4: Bidirectional IPC Bridge Between Voice Agent and Self-Improver
    """
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.subscribers = []
        self.active_clients = set()

    async def handle_client(self, websocket, path):
        logger.info(f"New IPC connection from {websocket.remote_address}")
        self.active_clients.add(websocket)
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    event = JarvisEvent(**data)
                    logger.debug(f"Received IPC Event: {event.event_type} from {event.source}")
                    
                    # Notify subscribers
                    for sub in self.subscribers:
                        asyncio.create_task(sub(event))
                        
                except Exception as e:
                    logger.error(f"Malformed IPC message: {e}")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.active_clients.remove(websocket)
            logger.info(f"IPC connection closed from {websocket.remote_address}")

    def subscribe(self, callback):
        self.subscribers.append(callback)

    async def send_directive(self, directive: Directive):
        """Phase 4: Real-Time Guidance Injection (Bidirectional IPC)"""
        if not self.active_clients:
            logger.warning("No active IPC clients to send directive to.")
            return

        message = json.dumps(directive.model_dump())
        dead_clients = set()
        
        for client in self.active_clients:
            try:
                await client.send(message)
                logger.info(f"Sent directive {directive.type} to {client.remote_address}")
            except Exception as e:
                logger.error(f"Failed to send directive: {e}")
                dead_clients.add(client)
                
        self.active_clients -= dead_clients

    async def start_server(self):
        logger.info(f"Starting IPC Server on ws://{self.host}:{self.port}")
        await websockets.serve(self.handle_client, self.host, self.port)

# Usage example:
# bridge = IPCBridgeServer()
# asyncio.create_task(bridge.start_server())
