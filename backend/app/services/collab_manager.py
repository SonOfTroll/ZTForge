"""
Real-time collaboration manager — Socket.io event handling.

Manages per-canvas rooms with presence tracking, cursor broadcasting,
and node/edge synchronization. Redis is used for ephemeral state
(cursors, who's online) while Postgres holds durable canvas state.

Architecture note: Socket.io events are fire-and-forget for cursor/presence
(loss is acceptable), but node/edge mutations go through the REST API
for durability, then broadcast via socket for real-time sync.
"""

from typing import Any
from dataclasses import dataclass, field

import socketio

from app.core.logging import get_logger

logger = get_logger("ztforge.collab")


@dataclass
class RoomState:
    """Ephemeral per-room state — not persisted to DB."""
    canvas_id: str
    users: dict[str, dict[str, Any]] = field(default_factory=dict)
    # user_id -> {display_name, color, cursor_position, connected_at}


class CollabManager:
    def __init__(self, sio: socketio.AsyncServer):
        self.sio = sio
        self.rooms: dict[str, RoomState] = {}
        self._register_handlers()

    def _register_handlers(self) -> None:
        self.sio.on("canvas:join", handler=self.on_join)
        self.sio.on("canvas:leave", handler=self.on_leave)
        self.sio.on("cursor:move", handler=self.on_cursor_move)
        self.sio.on("node:add", handler=self.on_node_change)
        self.sio.on("node:move", handler=self.on_node_change)
        self.sio.on("node:delete", handler=self.on_node_change)
        self.sio.on("edge:add", handler=self.on_edge_change)
        self.sio.on("edge:delete", handler=self.on_edge_change)
        self.sio.on("comment:add", handler=self.on_comment)
        self.sio.on("disconnect", handler=self.on_disconnect)

    async def on_join(self, sid: str, data: dict[str, Any]) -> None:
        canvas_id = data.get("canvas_id", "")
        user_id = data.get("user_id", "")
        display_name = data.get("display_name", "Anonymous")

        if not canvas_id:
            return

        # Assign a color for this user's cursor
        colors = ["#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#06b6d4", "#f97316"]
        room = self.rooms.get(canvas_id, RoomState(canvas_id=canvas_id))
        color_idx = len(room.users) % len(colors)

        room.users[user_id] = {
            "sid": sid,
            "display_name": display_name,
            "color": colors[color_idx],
            "cursor": {"x": 0, "y": 0},
        }
        self.rooms[canvas_id] = room

        await self.sio.enter_room(sid, canvas_id)
        logger.info("user_joined_canvas", user=display_name, canvas=canvas_id)

        # Notify others in the room
        await self.sio.emit(
            "presence:join",
            {"user_id": user_id, "display_name": display_name, "color": colors[color_idx]},
            room=canvas_id,
            skip_sid=sid,
        )
        # Send current room state to the joining user
        await self.sio.emit(
            "presence:state",
            {"users": room.users},
            to=sid,
        )

    async def on_leave(self, sid: str, data: dict[str, Any]) -> None:
        canvas_id = data.get("canvas_id", "")
        user_id = data.get("user_id", "")
        await self._remove_user(sid, canvas_id, user_id)

    async def on_disconnect(self, sid: str) -> None:
        # Find which room this sid was in and clean up
        for canvas_id, room in list(self.rooms.items()):
            for uid, info in list(room.users.items()):
                if info.get("sid") == sid:
                    await self._remove_user(sid, canvas_id, uid)

    async def _remove_user(self, sid: str, canvas_id: str, user_id: str) -> None:
        room = self.rooms.get(canvas_id)
        if not room:
            return
        user_info = room.users.pop(user_id, None)
        if user_info:
            await self.sio.leave_room(sid, canvas_id)
            await self.sio.emit(
                "presence:leave",
                {"user_id": user_id},
                room=canvas_id,
            )
            logger.info("user_left_canvas", user=user_id, canvas=canvas_id)
        # Clean up empty rooms
        if not room.users:
            del self.rooms[canvas_id]

    async def on_cursor_move(self, sid: str, data: dict[str, Any]) -> None:
        """Broadcast cursor position — fire and forget, no persistence."""
        canvas_id = data.get("canvas_id", "")
        await self.sio.emit(
            "cursor:update",
            {
                "user_id": data.get("user_id"),
                "position": data.get("position", {"x": 0, "y": 0}),
            },
            room=canvas_id,
            skip_sid=sid,
        )

    async def on_node_change(self, sid: str, data: dict[str, Any]) -> None:
        """
        Relay node mutations to room. The actual state change is persisted
        via the REST API — this just ensures real-time sync for other clients.
        """
        canvas_id = data.get("canvas_id", "")
        event_type = data.get("event_type", "node:update")
        await self.sio.emit(
            event_type,
            data,
            room=canvas_id,
            skip_sid=sid,
        )

    async def on_edge_change(self, sid: str, data: dict[str, Any]) -> None:
        canvas_id = data.get("canvas_id", "")
        event_type = data.get("event_type", "edge:update")
        await self.sio.emit(
            event_type,
            data,
            room=canvas_id,
            skip_sid=sid,
        )

    async def on_comment(self, sid: str, data: dict[str, Any]) -> None:
        canvas_id = data.get("canvas_id", "")
        await self.sio.emit(
            "comment:new",
            data,
            room=canvas_id,
            skip_sid=sid,
        )
