"""
WebSocket Connection Manager for Real-Time Events

This module provides WebSocket support for real-time notifications
across the platform (users, shops, admins).
"""
from typing import Dict, List, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and broadcasts"""

    def __init__(self):
        # Active connections by client type and ID
        # Structure: {client_type: {client_id: [websockets]}}
        self.active_connections: Dict[str, Dict[int, List[WebSocket]]] = {
            "user": {},
            "shop": {},
            "admin": {}
        }

        # Room-based connections (for specific resources)
        # Structure: {room_name: [websockets]}
        self.rooms: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, client_type: str, client_id: int, platform: str = "web"):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()

        if client_type not in self.active_connections:
            self.active_connections[client_type] = {}

        if client_id not in self.active_connections[client_type]:
            self.active_connections[client_type][client_id] = []

        self.active_connections[client_type][client_id].append(websocket)
        
        # DEBUG: Log connection state
        total_connections = sum(len(conns) for clients in self.active_connections.values() for conns in clients.values())
        logger.info(f"✅ WebSocket connected: {client_type}:{client_id} (platform: {platform}) | Total connections: {total_connections}")
        logger.info(f"📊 Active connections: {dict((k, list(v.keys())) for k, v in self.active_connections.items())}")

        # Send connection confirmation
        await self.send_personal_message(
            {
                "event": "connected",
                "client_type": client_type,
                "client_id": client_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            websocket
        )

    def disconnect(self, websocket: WebSocket, client_type: str, client_id: int):
        """Remove a WebSocket connection"""
        try:
            if (client_type in self.active_connections and
                client_id in self.active_connections[client_type]):

                if websocket in self.active_connections[client_type][client_id]:
                    self.active_connections[client_type][client_id].remove(websocket)

                # Clean up empty lists
                if not self.active_connections[client_type][client_id]:
                    del self.active_connections[client_type][client_id]

            # Remove from all rooms
            for room_sockets in self.rooms.values():
                room_sockets.discard(websocket)

            logger.info(f"WebSocket disconnected: {client_type}:{client_id}")
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket: {e}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to a specific WebSocket connection"""
        try:
            # Check if websocket is connected and ready
            if websocket.client_state.name != "CONNECTED":
                logger.warning(f"WebSocket is not connected (state: {websocket.client_state.name}), skipping message")
                return
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")

    async def send_to_client(self, message: dict, client_type: str, client_id: int):
        """Send message to all connections of a specific client"""
        logger.info(f"📤 send_to_client called: type={client_type}, id={client_id}, event={message.get('event')}")
        
        if (client_type in self.active_connections and
            client_id in self.active_connections[client_type]):

            connections_count = len(self.active_connections[client_type][client_id])
            logger.info(f"   Found {connections_count} connection(s) for {client_type}:{client_id}")
            
            disconnected = []
            sent_successfully = 0
            for websocket in self.active_connections[client_type][client_id]:
                try:
                    # Check if websocket is still connected
                    if websocket.client_state.name != "CONNECTED":
                        logger.warning(f"   ⚠️ WebSocket not connected (state: {websocket.client_state.name}), marking for removal")
                        disconnected.append(websocket)
                        continue
                    
                    await websocket.send_json(message)
                    sent_successfully += 1
                    logger.info(f"   ✅ Message sent successfully to {client_type}:{client_id}")
                except Exception as e:
                    logger.error(f"   ❌ Error sending to client {client_type}:{client_id}: {type(e).__name__}: {e}")
                    disconnected.append(websocket)

            logger.info(f"   📊 Sent to {sent_successfully}/{connections_count} connections")
            
            # Clean up disconnected websockets
            for ws in disconnected:
                logger.warning(f"   🗑️ Removing disconnected websocket for {client_type}:{client_id}")
                self.disconnect(ws, client_type, client_id)
        else:
            logger.warning(f"   ⚠️ No active connections found for {client_type}:{client_id}")

    async def broadcast_to_type(self, message: dict, client_type: str):
        """Broadcast message to all clients of a specific type"""
        logger.info(f"📢 broadcast_to_type called: type={client_type}, event={message.get('event')}")
        
        if client_type not in self.active_connections:
            logger.warning(f"   ⚠️ Client type '{client_type}' not found in active_connections")
            return

        clients_count = len(self.active_connections[client_type])
        logger.info(f"   Found {clients_count} client(s) of type {client_type}")
        
        disconnected = []
        sent_count = 0
        for client_id, websockets in self.active_connections[client_type].items():
            logger.info(f"   Broadcasting to {client_type}:{client_id} ({len(websockets)} connection(s))")
            for websocket in websockets:
                try:
                    # Check if websocket is still connected
                    if websocket.client_state.name != "CONNECTED":
                        logger.warning(f"   ⚠️ WebSocket not connected (state: {websocket.client_state.name}), marking for removal")
                        disconnected.append((websocket, client_type, client_id))
                        continue
                    
                    await websocket.send_json(message)
                    sent_count += 1
                    logger.info(f"   ✅ Message sent to {client_type}:{client_id}")
                except Exception as e:
                    logger.error(f"   ❌ Error broadcasting to {client_type}:{client_id}: {e}")
                    disconnected.append((websocket, client_type, client_id))

        logger.info(f"   📊 Total messages sent: {sent_count}")
        
        # Clean up disconnected websockets
        for ws, c_type, c_id in disconnected:
            self.disconnect(ws, c_type, c_id)

    async def broadcast_to_all(self, message: dict):
        """Broadcast message to all connected clients"""
        for client_type in self.active_connections:
            await self.broadcast_to_type(message, client_type)

    async def join_room(self, websocket: WebSocket, room_name: str):
        """Add a websocket to a room"""
        if room_name not in self.rooms:
            self.rooms[room_name] = set()
        self.rooms[room_name].add(websocket)
        logger.info(f"WebSocket joined room: {room_name}")

    async def leave_room(self, websocket: WebSocket, room_name: str):
        """Remove a websocket from a room"""
        if room_name in self.rooms:
            self.rooms[room_name].discard(websocket)
            if not self.rooms[room_name]:
                del self.rooms[room_name]
        logger.info(f"WebSocket left room: {room_name}")

    async def broadcast_to_room(self, message: dict, room_name: str):
        """Broadcast message to all websockets in a room"""
        if room_name not in self.rooms:
            return

        disconnected = []
        for websocket in self.rooms[room_name]:
            try:
                # Check if websocket is still connected
                if websocket.client_state.name != "CONNECTED":
                    disconnected.append(websocket)
                    continue
                    
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to room {room_name}: {e}")
                disconnected.append(websocket)

        # Clean up disconnected websockets
        for ws in disconnected:
            self.rooms[room_name].discard(ws)

    def get_connection_count(self) -> dict:
        """Get statistics about active connections"""
        stats = {
            "total": 0,
            "by_type": {}
        }

        for client_type, clients in self.active_connections.items():
            count = sum(len(websockets) for websockets in clients.values())
            stats["by_type"][client_type] = count
            stats["total"] += count

        stats["rooms"] = len(self.rooms)
        return stats


# Global connection manager instance
connection_manager = ConnectionManager()
