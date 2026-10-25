import json
import logging
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("metro.ws")
router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manages active browser WebSocket connections and broadcasts typed state deltas."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, event_type: str, camera_id: str, data: dict, event_id: str = "evt_broadcast"):
        envelope = {
            "schema_version": "1.0",
            "event_id": event_id,
            "type": event_type,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "camera_id": camera_id,
            "data": data
        }
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(envelope)
            except Exception:
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send initial keepalive/heartbeat on connection
        await websocket.send_json({
            "schema_version": "1.0",
            "event_id": "evt_init",
            "type": "heartbeat",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "camera_id": "system",
            "data": {"status": "connected", "server_time": datetime.now(timezone.utc).isoformat()}
        })
        while True:
            # Keep socket open and receive any ping/commands from client
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket error: {e}")
        manager.disconnect(websocket)
