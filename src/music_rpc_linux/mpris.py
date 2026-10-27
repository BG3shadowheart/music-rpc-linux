"""Low-traffic asynchronous MPRIS discovery over the session D-Bus."""
from __future__ import annotations
import asyncio
import logging
from typing import Any
from .models import Track, parse_mpris_metadata, unwrap

MPRIS_PREFIX = "org.mpris.MediaPlayer2."
PLAYER_IFACE = "org.mpris.MediaPlayer2.Player"
PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"


class MprisMonitor:
    def __init__(self):
        self.bus = None

    async def _connect(self):
        from dbus_fast.message import Message, MessageType
        from dbus_fast.aio import MessageBus
        self.bus = await MessageBus().connect()
        self.Message = Message
        self.MessageType = MessageType

    async def scan(self) -> list[Track]:
        if self.bus is None:
            await self._connect()
        reply = await self.bus.call(self.Message(
            destination="org.freedesktop.DBus", path="/org/freedesktop/DBus",
            interface="org.freedesktop.DBus", member="ListNames"))
        if reply.message_type == self.MessageType.ERROR:
            raise ConnectionError(reply.error_name or "D-Bus ListNames failed")
        names = [name for name in reply.body[0] if name.startswith(MPRIS_PREFIX)]
        tracks = []
        for name in names:
            try:
                metadata = await self._get(name, "Metadata")
                status = await self._get(name, "PlaybackStatus")
                position = await self._get(name, "Position")
                if status not in ("Playing", "Paused", "Stopped"):
                    continue
                track = parse_mpris_metadata(metadata, status, position, name.removeprefix(MPRIS_PREFIX))
                if track:
                    tracks.append(track)
            except Exception as exc:
                # A bus owner can disappear between ListNames and property reads.
                logging.debug("MPRIS player %s changed during scan: %s", name, exc)
        return tracks

    async def _get(self, name: str, prop: str) -> Any:
        from dbus_fast.message import Message
        reply = await self.bus.call(Message(
            destination=name, path="/org/mpris/MediaPlayer2",
            interface=PROPERTIES_IFACE, member="Get",
            signature="ss", body=[PLAYER_IFACE, prop]))
        if reply.message_type == self.MessageType.ERROR:
            raise RuntimeError(reply.error_name or f"MPRIS property {prop} failed")
        return unwrap(reply.body[0])

    async def close(self):
        if self.bus is not None:
            self.bus.disconnect()
            self.bus = None

