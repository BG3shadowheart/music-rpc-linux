#!/usr/bin/env python3
"""Music RPC Linux entry point. This project intentionally contains no Windows backend."""
from __future__ import annotations
import argparse
import asyncio
import fcntl
import json
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from music_rpc_linux.config import APP_DIR, load_config
from music_rpc_linux.native_host import serve

STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "music-rpc-linux"
LOCK_DIR = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / f"music-rpc-linux-{os.getuid()}"


def configure_logging(debug=False):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO,
        handlers=[RotatingFileHandler(STATE_DIR / "music-rpc.log", maxBytes=1_000_000, backupCount=3),
                  logging.StreamHandler(sys.stderr)],
        format="%(asctime)s %(levelname)s %(message)s")


def single_instance():
    LOCK_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(LOCK_DIR, 0o700)
    lock = open(LOCK_DIR / "app.lock", "w", encoding="ascii")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        return None
    return lock


async def dump_state(config):
    from music_rpc_linux.mpris import MprisMonitor
    monitor = MprisMonitor()
    try:
        tracks = await monitor.scan()
        return {"players": [track.__dict__ for track in tracks], "priority": config["player_priority"]}
    finally:
        await monitor.close()


def main():
    parser = argparse.ArgumentParser(description="Linux music playback to Discord Rich Presence")
    parser.add_argument("--native-host", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--dump", action="store_true", help="print detected MPRIS players as JSON")
    parser.add_argument("--debug", action="store_true", help="enable detailed logs")
    parser.add_argument("--background", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    configure_logging(args.debug)
    if args.native_host:
        return serve()
    config = load_config()
    if args.dump:
        try:
            print(json.dumps(asyncio.run(dump_state(config)), indent=2, ensure_ascii=False))
            return 0
        except Exception as exc:
            print(json.dumps({"error": str(exc)}), file=sys.stderr)
            return 1
    lock = single_instance()
    if lock is None:
        logging.info("Another instance is already active")
        return 0
    try:
        from music_rpc_linux.ui import launch
        return launch(config)
    except ImportError as exc:
        logging.error("Desktop libraries are missing: %s", exc)
        return 2
    finally:
        lock.close()


if __name__ == "__main__":
    raise SystemExit(main())
