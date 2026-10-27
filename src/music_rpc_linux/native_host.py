"""Chrome native messaging host and framed-protocol helpers."""
from __future__ import annotations
import json
import os
import socket
import struct
import sys
from pathlib import Path

SOCKET_PATH = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "music-rpc-linux" / "bridge.sock"
MAX_PACKET = 1_000_000


def read_packet(stream):
    header = bytearray()
    while len(header) < 4:
        chunk = stream.read(4 - len(header))
        if not chunk and not header:
            return None
        if not chunk:
            raise ValueError("incomplete native-message header")
        header.extend(chunk)
    if not header:
        return None
    size = struct.unpack("<I", header)[0]
    if size > MAX_PACKET:
        raise ValueError("native message exceeds 1 MB")
    body = bytearray()
    while len(body) < size:
        chunk = stream.read(size - len(body))
        if not chunk:
            raise ValueError("incomplete native-message body")
        body.extend(chunk)
    return json.loads(body.decode("utf-8"))


def write_packet(stream, value):
    body = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(body) > MAX_PACKET:
        raise ValueError("response exceeds 1 MB")
    stream.write(struct.pack("<I", len(body)) + body)
    stream.flush()


def forward(payload, socket_path=SOCKET_PATH):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(2.0)
        client.connect(str(socket_path))
        client.sendall(json.dumps(payload, ensure_ascii=False).encode("utf-8") + b"\n")
        data = bytearray()
        while len(data) <= MAX_PACKET:
            chunk = client.recv(65536)
            if not chunk or b"\n" in chunk:
                data.extend(chunk.split(b"\n", 1)[0])
                break
            data.extend(chunk)
        return json.loads(data.decode("utf-8")) if data else {"ok": False, "error": "empty app response"}


def serve(stdin=None, stdout=None, socket_path=SOCKET_PATH):
    source, sink = stdin or sys.stdin.buffer, stdout or sys.stdout.buffer
    while True:
        packet = read_packet(source)
        if packet is None:
            return 0
        if packet == {"type": "ping"}:
            write_packet(sink, {"ok": True, "version": "1.0.0"})
            continue
        try:
            reply = forward(packet, socket_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            reply = {"ok": False, "error": str(exc)[:240]}
        write_packet(sink, reply)


if __name__ == "__main__":
    raise SystemExit(serve())
