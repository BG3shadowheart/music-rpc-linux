"""Discord local IPC adapter with bounded retry and update deduplication."""
from __future__ import annotations
import asyncio
import logging
import time
from .models import Track


class DiscordPresence:
    def __init__(self, app_id: str):
        self.app_id = app_id
        self.rpc = None
        self.last_key = None
        self.retry_at = 0.0
        self.retry_delay = 2.0
        self.refresh_seconds = 30.0
        self.last_sent_at = 0.0
        self._last_identity = None
        self._last_playing = None
        self._last_position_ms = None
        self._last_position_clock = None
        self._start_epoch = None

    async def _connect(self):
        from pypresence import Presence
        self.rpc = Presence(self.app_id)
        await asyncio.to_thread(self.rpc.connect)
        self.retry_delay = 2.0
        logging.info("Connected to the local Discord RPC socket")

    async def publish(self, track: Track | None, artwork: str | None, show_paused: bool = False):
        if track is None or (not track.playing and not show_paused):
            if self.rpc and self.last_key is not None:
                try:
                    await asyncio.to_thread(self.rpc.clear)
                except Exception as exc:
                    logging.warning("Discord clear failed: %s", exc)
                    await self._disconnect()
            self.last_key = None
            return
        now_mono, now_wall = time.monotonic(), time.time()
        identity = (track.source, track.track_id, track.title, track.artist, track.album)
        position = track.position_ms
        if identity != self._last_identity or track.playing != self._last_playing:
            self._start_epoch = int(now_wall - (position or 0) / 1000) if track.playing else None
        elif track.playing and position is not None and self._last_position_ms is not None:
            expected = self._last_position_ms + (now_mono - self._last_position_clock) * 1000
            if abs(position - expected) > 3500:
                self._start_epoch = int(now_wall - position / 1000)
        self._last_identity, self._last_playing = identity, track.playing
        self._last_position_ms, self._last_position_clock = position, now_mono
        start = self._start_epoch if track.playing else None
        key = (track.title, track.artist, track.album, track.playing, artwork, start)
        if key == self.last_key and time.monotonic() - self.last_sent_at < self.refresh_seconds:
            return
        if self.rpc is None:
            if time.monotonic() < self.retry_at:
                return
            try:
                await self._connect()
            except Exception as exc:
                logging.info("Discord desktop IPC is unavailable: %s", exc)
                self.retry_at = time.monotonic() + self.retry_delay
                self.retry_delay = min(60, self.retry_delay * 1.7)
                return
        try:
            from pypresence import ActivityType, StatusDisplayType
            args = {"details": track.title[:128], "state": track.artist[:128] or track.source[:128],
                    "activity_type": ActivityType.LISTENING,
                    "status_display_type": StatusDisplayType.DETAILS,
                    "large_text": track.album[:128] if track.album else None,
                    "large_image": artwork[:256] if artwork else None}
            if start:
                args["start"] = start
            await asyncio.to_thread(self.rpc.update, **args)
            self.last_key = key
            self.last_sent_at = time.monotonic()
        except Exception as exc:
            logging.warning("Discord RPC update failed; reconnecting later: %s", exc)
            await self._disconnect()

    async def _disconnect(self):
        rpc, self.rpc = self.rpc, None
        self.last_key = None
        self.retry_at = time.monotonic() + self.retry_delay
        self.retry_delay = min(60, self.retry_delay * 1.7)
        if rpc:
            try:
                await asyncio.to_thread(rpc.close)
            except Exception:
                pass

    async def close(self):
        if self.rpc:
            try:
                await asyncio.to_thread(self.rpc.clear)
                await asyncio.to_thread(self.rpc.close)
            except Exception:
                pass
            self.rpc = None
