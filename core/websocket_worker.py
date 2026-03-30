import json
import time
import logging
from typing import Dict, Optional
from PySide6.QtCore import QThread, Signal
from websockets.client import WebSocketClientProtocol


class WebSocketWorker(QThread):
    connected = Signal()
    disconnected = Signal(str)
    message_received = Signal(dict)
    error = Signal(str)

    def __init__(self, url: str, headers: Optional[Dict] = None):
        super().__init__()
        self.url = url
        self.headers = headers or {}
        self._should_stop = False
        self._socket = None
        self._message_queue = []

    def cancel(self):
        self._should_stop = True

    def send(self, message: str, binary: bool = False):
        if self._socket:
            try:
                if binary:
                    self._socket.send(message.encode('utf-8'))
                else:
                    self._socket.send(message)
                return True
            except Exception as e:
                logging.error(f"WebSocket send error: {e}")
                self.error.emit(f"Failed to send message: {str(e)}")
                return False
        return False

    def run(self):
        try:
            import websockets
            logging.info(f"Connecting to WebSocket: {self.url}")
            
            extra_headers = None
            if self.headers:
                extra_headers = [(k, v) for k, v in self.headers.items()]
            
            self._run_sync(websockets, extra_headers)
            
        except ImportError:
            self.error.emit("websockets library not installed. Run: pip install websockets")
        except Exception as e:
            logging.error(f"WebSocket error: {e}")
            self.error.emit(f"WebSocket error: {str(e)}")

    def _run_sync(self, websockets, extra_headers):
        import asyncio
        
        async def connect():
            try:
                async with websockets.connect(
                    self.url,
                    extra_headers=extra_headers if extra_headers else None
                ) as socket:
                    self._socket = socket
                    self.connected.emit()
                    logging.info("WebSocket connected")
                    
                    while not self._should_stop:
                        try:
                            message = await asyncio.wait_for(socket.recv(), timeout=0.1)
                            timestamp = time.time()
                            
                            if isinstance(message, bytes):
                                self.message_received.emit({
                                    'type': 'binary',
                                    'data': message.hex(),
                                    'timestamp': timestamp
                                })
                            else:
                                self.message_received.emit({
                                    'type': 'text',
                                    'data': message,
                                    'timestamp': timestamp
                                })
                        except asyncio.TimeoutError:
                            continue
                        except Exception as e:
                            if not self._should_stop:
                                logging.error(f"WebSocket receive error: {e}")
                                self.error.emit(f"Receive error: {str(e)}")
                            break
                    
                    self._socket = None
                    
            except Exception as e:
                if not self._should_stop:
                    logging.error(f"WebSocket connection error: {e}")
                    self.error.emit(f"Connection error: {str(e)}")
        
        asyncio.get_event_loop().run_until_complete(connect())
        self.disconnected.emit("Connection closed")
