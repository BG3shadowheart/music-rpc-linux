"""Same-user Unix socket endpoint for browser native-messaging packets."""
from __future__ import annotations
import asyncio
import json
import logging
import os
import stat
from pathlib import Path
from .models import Track, parse_browser_track

SOCKET_PATH = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "music-rpc-linux" / "bridge.sock"


class BrowserBridge:
    def __init__(self, on_track, path=SOCKET_PATH):
        self.path, self.on_track = Path(path), on_track
        self.server = None
        self.track: Track | None = None
        self.received_at = 0.0

    async def start(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self.path.parent, 0o700)
        try:
            info = self.path.lstat()
            if not stat.S_ISSOCK(info.st_mode):
                raise RuntimeError(f"Refusing to replace a non-socket file: {self.path}")
            self.path.unlink()
        except FileNotFoundError:
            pass
        self.server = await asyncio.start_unix_server(self._handle, path=str(self.path))
        os.chmod(self.path, 0o600)

    async def _handle(self, reader, writer):
        try:
            raw = await asyncio.wait_for(reader.readline(), timeout=2)
            if len(raw) > 1_000_000:
                raise ValueError("message too large")
            payload = json.loads(raw.decode("utf-8"))
            kind = payload.get("type")
            if kind == "remove":
                self.track = None
                self.received_at = 0
            elif kind == "update":
                track = parse_browser_track(payload.get("track", {}))
                self.track = track
                self.received_at = asyncio.get_running_loop().time()
            else:
                raise ValueError("unsupported browser message")
            if self.on_track:
                self.on_track()
            writer.write(b'{"ok":true}\n')
            await writer.drain()
        except Exception as exc:
            logging.warning("Rejected browser bridge message: %s", exc)
            writer.write(json.dumps({"ok": False, "error": str(exc)[:200]}).encode() + b"\n")
            try:
                await writer.drain()
            except Exception:
                pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    def current(self) -> Track | None:
        if self.track is None or asyncio.get_running_loop().time() - self.received_at > 12:
            self.track = None
            return None
        return self.track

    async def close(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
