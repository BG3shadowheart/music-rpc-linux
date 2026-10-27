"""User configuration with defensive validation and atomic persistence."""
from __future__ import annotations
import json
import os
import shutil
from pathlib import Path
from typing import Any

APP_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "music-rpc-linux"
CONFIG_PATH = APP_DIR / "config.json"
DEFAULTS: dict[str, Any] = {
    "discord_app_id": "1561450956242161745",
    "player_priority": ["fooyin", "youtube music"],
    "show_paused": False,
    "ignore_ordinary_youtube": True,
    "artwork_lookup": True,
    "poll_seconds": 2.0,
    "autostart": False,
    "enabled": True,
    "diagnostic": False,
}


def validate_config(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Configuration must be a JSON object")
    value = dict(DEFAULTS)
    value.update(raw)
    app_id = str(value["discord_app_id"]).strip()
    if not app_id.isdecimal() or not 10 <= len(app_id) <= 25:
        raise ValueError("discord_app_id must be a Discord application ID")
    value["discord_app_id"] = app_id
    priority = value["player_priority"]
    if not isinstance(priority, list) or not all(isinstance(x, str) and x.strip() for x in priority):
        raise ValueError("player_priority must be a list of player name fragments")
    value["player_priority"] = [x.strip() for x in priority]
    value["poll_seconds"] = min(10.0, max(1.0, float(value["poll_seconds"])))
    for key in ("show_paused", "ignore_ordinary_youtube", "artwork_lookup", "autostart", "enabled", "diagnostic"):
        if not isinstance(value[key], bool):
            raise ValueError(f"{key} must be true or false")
    return value


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    try:
        return validate_config(json.loads(path.read_text(encoding="utf-8")))
    except FileNotFoundError:
        return dict(DEFAULTS)
    except (OSError, ValueError, TypeError) as exc:
        import logging
        logging.warning("Invalid configuration; using safe defaults: %s", exc)
        return dict(DEFAULTS)


def save_config(value: dict[str, Any], path: Path = CONFIG_PATH) -> dict[str, Any]:
    checked = validate_config(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(checked, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)
    return checked


def set_autostart(enabled: bool, app_command: str | None = None) -> None:
    """Manage only this app's per-user XDG desktop autostart entry."""
    path = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "autostart" / "music-rpc-linux.desktop"
    if not enabled:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    executable = app_command or os.environ.get("MUSIC_RPC_LAUNCHER") or shutil.which("music-rpc") or "music-rpc"
    path.write_text("[Desktop Entry]\nType=Application\nName=Music RPC\nExec=\"" + executable.replace("\\", "\\\\").replace('"', '\\"') + "\" --background\nIcon=music-rpc-linux\nTerminal=false\nX-GNOME-Autostart-enabled=true\n", encoding="utf-8")
