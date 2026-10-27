"""Coordinates D-Bus discovery, browser bridge, artwork and Discord RPC."""
from __future__ import annotations
import asyncio
import logging
import os
import time
from pathlib import Path
from .artwork import ArtworkResolver
from .bridge import BrowserBridge
from .config import APP_DIR
from .models import Track, choose_track
from .mpris import MprisMonitor
from .presence import DiscordPresence


class Runtime:
    def __init__(self, config: dict, on_status=None):
        self.config, self.on_status = config, on_status or (lambda _s: None)
        self.stop_event = asyncio.Event()
        self.mpris = MprisMonitor()
        self.bridge = BrowserBridge(lambda: None)
        cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "music-rpc-linux" / "artwork-cache.json"
        self.art = ArtworkResolver(cache, config["artwork_lookup"])
        self.discord = DiscordPresence(config["discord_app_id"])
        self.current: Track | None = None

    async def run(self):
        await self.bridge.start()
        self.on_status("Running — waiting for music")
        retry_delay = 1.0
        try:
            while not self.stop_event.is_set():
                try:
                    players = await self.mpris.scan()
                    retry_delay = 1.0
                    browser = self.bridge.current()
                    if browser:
                        players.append(browser)
                    track = choose_track(players, self.config["player_priority"], self.config["show_paused"])
                    if not self.config["enabled"]:
                        track = None
                    if track and (track.playing or self.config["show_paused"]):
                        artwork = await asyncio.to_thread(self.art.resolve, track)
                    else:
                        artwork = None
                    await self.discord.publish(track, artwork, self.config["show_paused"])
                    if track and (self.current is None or track.identity != self.current.identity or track.playing != self.current.playing):
                        logging.info("Selected %s playback (%s)", track.source, "playing" if track.playing else "paused")
                    elif track is None and self.current is not None:
                        logging.info("No active media; Discord presence cleared")
                    self.current = track
                    self.on_status(f"{track.title} — {track.artist}" if track else "Running — waiting for music")
                except Exception as exc:
                    logging.warning("Media scan failed; reconnecting: %s", exc)
                    self.on_status("Reconnecting to D-Bus or Discord")
                    await self.mpris.close()
                    retry_delay = min(20.0, retry_delay * 1.6)
                try:
                    wait_seconds = max(self.config["poll_seconds"], retry_delay)
                    await asyncio.wait_for(self.stop_event.wait(), timeout=wait_seconds)
                except asyncio.TimeoutError:
                    pass
        finally:
            await self.discord.close()
            await self.mpris.close()
            await self.bridge.close()

    def stop(self):
        self.stop_event.set()
