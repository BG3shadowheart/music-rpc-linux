from __future__ import annotations
import asyncio
import io
import json
import struct
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from music_rpc_linux.artwork import ArtworkResolver
from music_rpc_linux.bridge import BrowserBridge
from music_rpc_linux.config import DEFAULTS, load_config, save_config, validate_config
from music_rpc_linux.models import Track, choose_track, parse_browser_track, parse_mpris_metadata
from music_rpc_linux.native_host import read_packet, serve, write_packet
from music_rpc_linux.presence import DiscordPresence


class Variant:
    def __init__(self, value): self.value = value


class MetadataTests(unittest.TestCase):
    def test_mpris_metadata_and_variant_unwrap(self):
        track = parse_mpris_metadata({
            "xesam:title": Variant("  Chameleon "),
            "xesam:artist": Variant(["Olivia Addams"]),
            "xesam:album": Variant("Never Say Never"),
            "mpris:length": Variant(153_000_000),
            "mpris:trackid": Variant("/track/12"),
            "mpris:artUrl": Variant("file:///home/test/cover.jpg"),
        }, "Playing", 12_500_000, "fooyin")
        self.assertEqual((track.title, track.artist, track.album), ("Chameleon", "Olivia Addams", "Never Say Never"))
        self.assertEqual((track.duration_ms, track.position_ms), (153_000, 12_500))
        self.assertEqual(track.track_id, "/track/12")
        self.assertTrue(track.playing)

    def test_missing_mpris_title_and_artist_is_ignored(self):
        self.assertIsNone(parse_mpris_metadata({}, "Playing"))
        self.assertIsNone(parse_mpris_metadata({"xesam:title": "Song"}, "Stopped"))

    def test_browser_track_validation_and_timing(self):
        track = parse_browser_track({"site": "youtube_music", "title": "Song", "artist": "Singer",
            "status": "playing", "duration_ms": "120000", "position_ms": 3000,
            "artwork": "https://i.ytimg.com/vi/abcdefghijk/maxresdefault.jpg"})
        self.assertEqual(track.duration_ms, 120000)
        self.assertEqual(track.position_ms, 3000)
        self.assertEqual(track.kind, "youtube")
        self.assertIsNone(parse_browser_track({"site": "youtube", "title": "random video"}))
        self.assertIsNone(parse_browser_track({"site": "youtube_music", "title": "", "artist": "Singer"}))
        self.assertIsNone(parse_browser_track({"site": "youtube_music", "title": "Song", "artwork": "file:///tmp/cover"}).image_url)


class SelectionTests(unittest.TestCase):
    def test_fooyin_wins_when_multiple_players_are_playing(self):
        web = Track("Browser song", "Artist", "", True, "YouTube Music", kind="youtube")
        fooyin = Track("Local song", "Artist", "Album", True, "fooyin")
        self.assertEqual(choose_track([web, fooyin], ["fooyin", "youtube music"]).title, "Local song")

    def test_play_pause_stop_and_stale_track_selection(self):
        playing = Track("Song", "Artist", "", True, "fooyin")
        paused = Track("Song", "Artist", "", False, "fooyin")
        self.assertIsNone(choose_track([paused], ["fooyin"]))
        self.assertIs(choose_track([paused], ["fooyin"], show_paused=True), paused)
        self.assertIs(choose_track([playing], ["fooyin"]), playing)
        self.assertNotEqual(playing.identity, Track("Next", "Artist", "", True, "fooyin").identity)


class ArtworkTests(unittest.TestCase):
    def test_player_art_and_cache_are_used_only_when_https(self):
        with tempfile.TemporaryDirectory() as tmp:
            resolver = ArtworkResolver(Path(tmp) / "cache.json", lookup_enabled=False)
            resolver._probe = lambda _url: True
            track = Track("Song", "Artist", "", True, "YouTube Music", image_url="https://cdn.example/song.jpg", kind="youtube")
            self.assertEqual(resolver.resolve(track), "https://cdn.example/song.jpg")
            local = Track("Local only", "Different artist", "", True, "fooyin", image_url="file:///home/user/private-cover.jpg")
            self.assertIsNone(resolver.resolve(local))

    def test_missing_or_broken_artwork_is_nonfatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            resolver = ArtworkResolver(Path(tmp) / "cache.json", lookup_enabled=False)
            resolver._probe = lambda _url: False
            self.assertIsNone(resolver.resolve(Track("Unknown", "", "", True, "fooyin")))


class NativeMessagingTests(unittest.TestCase):
    def test_length_prefixed_round_trip(self):
        output = io.BytesIO()
        write_packet(output, {"type": "ping"})
        output.seek(0)
        self.assertEqual(read_packet(output), {"type": "ping"})

    def test_partial_header_is_read(self):
        class Chunks:
            def __init__(self, data): self.data, self.i = data, 0
            def read(self, size=-1):
                if self.i >= len(self.data): return b""
                result = self.data[self.i:self.i + 1]
                self.i += 1
                return result
        body = b'{"type":"ping"}'
        self.assertEqual(read_packet(Chunks(struct.pack("<I", len(body)) + body)), {"type": "ping"})

    def test_ping_reply_protocol(self):
        incoming = io.BytesIO()
        write_packet(incoming, {"type": "ping"})
        incoming.seek(0)
        outgoing = io.BytesIO()
        self.assertEqual(serve(incoming, outgoing), 0)
        outgoing.seek(0)
        self.assertEqual(read_packet(outgoing), {"ok": True, "version": "1.0.0"})

    def test_browser_bridge_accepts_track_and_replies(self):
        class Writer:
            def __init__(self): self.output = bytearray()
            def write(self, data): self.output.extend(data)
            async def drain(self): pass
            def close(self): pass
            async def wait_closed(self): pass
        async def scenario():
            with tempfile.TemporaryDirectory() as tmp:
                bridge = BrowserBridge(None, Path(tmp) / "bridge.sock")
                raw = json.dumps({"type": "update", "track": {"site": "youtube_music", "title": "Song", "artist": "Singer", "status": "playing"}}).encode() + b"\n"
                reader = asyncio.StreamReader()
                reader.feed_data(raw)
                reader.feed_eof()
                writer = Writer()
                await bridge._handle(reader, writer)
                self.assertEqual(bridge.current().title, "Song")
                self.assertEqual(bytes(writer.output), b'{"ok":true}\n')
        asyncio.run(scenario())


class ConfigurationTests(unittest.TestCase):
    def test_defaults_and_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            self.assertEqual(load_config(path), DEFAULTS)
            saved = save_config({**DEFAULTS, "show_paused": True}, path)
            self.assertTrue(load_config(path)["show_paused"])
            self.assertEqual(saved["player_priority"][0], "fooyin")

    def test_bad_config_is_rejected(self):
        with self.assertRaises(ValueError): validate_config({"discord_app_id": "not-an-id"})
        with self.assertRaises(ValueError): validate_config({"player_priority": "fooyin"})

    def test_corrupt_config_falls_back_to_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text("{broken", encoding="utf-8")
            self.assertEqual(load_config(path), DEFAULTS)


class DiscordRecoveryTests(unittest.TestCase):
    def test_disconnect_and_reconnect_then_track_update(self):
        class FakePresence:
            instances = []
            def __init__(self, app_id): self.app_id, self.closed = app_id, False; self.instances.append(self)
            def connect(self): return None
            def update(self, **kwargs):
                if getattr(self, "fail", False): raise ConnectionError("gone")
                self.activity = kwargs
            def close(self): self.closed = True
            def clear(self): pass
        fake = types.ModuleType("pypresence")
        fake.Presence = FakePresence
        fake.ActivityType = types.SimpleNamespace(LISTENING=2)
        fake.StatusDisplayType = types.SimpleNamespace(DETAILS=0)
        track = Track("Song", "Artist", "Album", True, "fooyin", 100000, 2000)
        async def scenario():
            client = DiscordPresence("123456789012")
            with patch.dict(sys.modules, {"pypresence": fake}):
                await client.publish(track, "https://cdn.example/cover.jpg")
                self.assertIsNotNone(client.rpc)
                client.rpc.fail = True
                await client.publish(Track("Next", "Artist", "Album", True, "fooyin", 100000, 0), None)
                self.assertIsNone(client.rpc)
                client.retry_at = 0
                await client.publish(Track("Next", "Artist", "Album", True, "fooyin", 100000, 0), None)
                self.assertIsNotNone(client.rpc)
                self.assertEqual(client.rpc.activity["details"], "Next")
                await client.close()
        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
