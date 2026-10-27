"""Platform-independent media models and MPRIS metadata normalization."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


def unwrap(value: Any) -> Any:
    """Unwrap dbus-fast Variants and nested containers into plain values."""
    while hasattr(value, "value"):
        value = value.value
    if isinstance(value, dict):
        return {str(k): unwrap(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [unwrap(v) for v in value]
    return value


def clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        value = ", ".join(str(v) for v in value if v)
    return " ".join(str(value).replace("\u200b", "").split()).strip()


@dataclass(frozen=True)
class Track:
    title: str
    artist: str
    album: str
    playing: bool
    source: str
    duration_ms: int | None = None
    position_ms: int | None = None
    image_url: str | None = None
    track_id: str | None = None
    start_epoch: float | None = None
    kind: str = "local"

    @property
    def identity(self) -> tuple[str, str, str, str]:
        return (self.source, self.track_id or "", self.title.casefold(), self.artist.casefold())


def parse_mpris_metadata(metadata: Mapping[str, Any] | None, playback_status: str,
                         position_us: int | None = None, source: str = "MPRIS") -> Track | None:
    """Map an org.mpris.MediaPlayer2.Player snapshot to an app Track."""
    if playback_status == "Stopped":
        return None
    meta = unwrap(dict(metadata or {}))
    title = clean(meta.get("xesam:title"))
    artists = meta.get("xesam:artist", [])
    artist = clean(artists)
    album = clean(meta.get("xesam:album"))
    if not title and not artist:
        return None
    length = meta.get("mpris:length")
    try:
        duration_ms = max(0, int(length) // 1000) if length is not None else None
    except (TypeError, ValueError):
        duration_ms = None
    try:
        position_ms = max(0, int(position_us) // 1000) if position_us is not None else None
    except (TypeError, ValueError):
        position_ms = None
    art = clean(meta.get("mpris:artUrl")) or None
    track_id = clean(meta.get("mpris:trackid")) or None
    return Track(title, artist, album, playback_status == "Playing", source,
                 duration_ms, position_ms, art, track_id, kind="local")


def parse_browser_track(payload: Mapping[str, Any]) -> Track | None:
    """Validate browser bridge data before it enters the media selector."""
    if payload.get("site") != "youtube_music":
        return None
    title = clean(payload.get("title"))
    artist = clean(payload.get("artist"))
    if not title:
        return None
    status = str(payload.get("status", "")).lower()
    playing = bool(payload.get("playing", status == "playing")) and status != "paused"
    def integer(name: str) -> int | None:
        try:
            value = int(float(payload[name]))
            return max(0, value)
        except (KeyError, TypeError, ValueError, OverflowError):
            return None
    image = clean(payload.get("artwork")) or None
    if image and not image.startswith(("https://", "http://")):
        image = None
    return Track(title, artist, clean(payload.get("album")), playing,
                 "YouTube Music", integer("duration_ms"), integer("position_ms"),
                 image, clean(payload.get("video_id")) or None,
                 kind="youtube")


def player_priority(source: str, priorities: list[str]) -> int:
    """Higher result means preferred; configured names are substring matches."""
    source_folded = source.casefold()
    for index, name in enumerate(priorities):
        if name.casefold() in source_folded:
            return len(priorities) - index
    return 0


def choose_track(tracks: list[Track], priorities: list[str], show_paused: bool = False) -> Track | None:
    """Prefer playing sources, then configured player priority, then stable name."""
    candidates = [t for t in tracks if t.playing]
    if not candidates and show_paused:
        candidates = tracks
    if not candidates:
        return None
    return max(candidates, key=lambda t: (player_priority(t.source, priorities), t.source.casefold()))
