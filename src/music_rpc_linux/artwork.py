"""Permanent artwork lookup. Never uploads local files or opens a public relay."""
from __future__ import annotations
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from .models import Track

USER_AGENT = "Music-RPC-Linux/1.0 (+local artwork lookup)"


def video_id_from_url(url: str | None) -> str | None:
    if not url:
        return None
    found = re.search(r"(?:[?&]v=|/vi/|youtu\.be/|/embed/)([A-Za-z0-9_-]{11})", url)
    return found.group(1) if found else None


class ArtworkResolver:
    def __init__(self, cache_path: Path, lookup_enabled: bool = True):
        self.path, self.enabled = cache_path, lookup_enabled
        self.cache: dict[str, str] = {}
        self.probes: dict[str, tuple[bool, float]] = {}
        self.no_art_until: dict[str, float] = {}
        try:
            value = json.loads(cache_path.read_text(encoding="utf-8"))
            if isinstance(value, dict):
                self.cache = {str(k): str(v) for k, v in value.items() if self._remote(v)}
        except (OSError, ValueError, TypeError):
            pass

    @staticmethod
    def _remote(url: str | None) -> bool:
        return isinstance(url, str) and url.startswith("https://")

    @staticmethod
    def key(track: Track) -> str:
        return "|".join((track.artist.casefold().strip(), track.title.casefold().strip()))

    def resolve(self, track: Track) -> str | None:
        key = self.key(track)
        if self.no_art_until.get(key, 0) > time.monotonic():
            return None
        supplied = track.image_url
        # Browser art is stable and remote; local file:// covers are deliberately excluded.
        candidates: list[str] = []
        if self._remote(supplied):
            candidates.append(supplied)
        video_id = video_id_from_url(supplied) or (track.track_id if track.kind == "youtube" else None)
        if video_id and re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            candidates.extend([f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
                               f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"])
        candidates.extend([self.cache.get(key, "")])
        for url in candidates:
            if self._remote(url) and self._probe(url):
                self._remember(key, url)
                return url
        if not self.enabled or not track.title:
            return None
        for url, album in self._catalog(track):
            if self._probe(url):
                self._remember(key, url)
                return url
        self.no_art_until[key] = time.monotonic() + 60
        return None

    def _probe(self, url: str) -> bool:
        cached = self.probes.get(url)
        if cached and cached[1] > time.monotonic():
            return cached[0]
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Range": "bytes=0-2047"})
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                content_type = response.headers.get("Content-Type", "")
                sample = response.read(32)
                result = response.status < 400 and content_type.lower().startswith("image/") and bool(sample)
        except Exception:
            result = False
        self.probes[url] = (result, time.monotonic() + 900)
        return result

    def _catalog(self, track: Track):
        term = " ".join(p for p in (track.artist, track.title, track.album) if p)
        url = "https://itunes.apple.com/search?" + urllib.parse.urlencode({"term": term, "entity": "song", "limit": 8})
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=6) as response:
                results = json.loads(response.read(1_000_000)).get("results", [])
        except Exception:
            results = []
        target = re.sub(r"\W+", "", track.title.casefold())
        for item in results:
            name = re.sub(r"\W+", "", str(item.get("trackName", "")).casefold())
            if name != target:
                continue
            art = str(item.get("artworkUrl100", ""))
            yield (re.sub(r"\d+x\d+bb", "600x600bb", art), item.get("collectionName", ""))

        # Deezer is the second permanent CDN source used by the Windows artwork resolver.
        query = " ".join(p for p in (track.artist, track.title) if p)
        deezer = "https://api.deezer.com/search?" + urllib.parse.urlencode({"q": query, "limit": 5})
        try:
            with urllib.request.urlopen(urllib.request.Request(deezer, headers={"User-Agent": USER_AGENT}), timeout=6) as response:
                items = json.loads(response.read(1_000_000)).get("data", [])
        except Exception:
            items = []
        for item in items:
            name = re.sub(r"\W+", "", str(item.get("title", "")).casefold())
            album = item.get("album") or {}
            art = album.get("cover_xl") or album.get("cover_big")
            if name == target and art:
                yield (str(art), album.get("title", ""))

        # Last permanent fallback: derive a public YouTube thumbnail from search results.
        search = "https://www.youtube.com/results?" + urllib.parse.urlencode({
            "search_query": query, "hl": "en", "gl": "US"})
        try:
            with urllib.request.urlopen(urllib.request.Request(search, headers={"User-Agent": USER_AGENT}), timeout=7) as response:
                page = response.read(3_000_000).decode("utf-8", "replace")
        except Exception:
            page = ""
        candidates = re.findall(r'"videoRenderer":\{"videoId":"([A-Za-z0-9_-]{11})"', page)
        for video_id in dict.fromkeys(candidates[:3]):
            yield (f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg", "")

    def _remember(self, key: str, url: str) -> None:
        self.cache[key] = url
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.path.with_suffix(".tmp")
            temp.write_text(json.dumps(self.cache, indent=2), encoding="utf-8")
            temp.replace(self.path)
            self.path.chmod(0o600)
        except OSError:
            pass
