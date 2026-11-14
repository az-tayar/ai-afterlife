"""A local stand-in for the ElevenLabs streaming endpoint, used only by the tests.

It checks that requests have the shape ElevenLabs expects and can simulate
normal streaming, a bad key (401), exhausted credits (429), a server that
never answers (timeout) and a connection that drops in the middle of a phrase.
"""

from __future__ import annotations

import json
import math
import socket
import struct
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

SR = 22050


def tone_pcm(seconds: float, freq: float = 220.0) -> bytes:
    n = int(SR * seconds)
    return b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * freq * i / SR)))
                    for i in range(n))


class MockElevenLabs:
    def __init__(self):
        self.behaviour = "ok"        # ok | 401 | 429 | hang | drop
        self.ttfb_s = 0.05           # delay before the first audio byte
        self.requests: list[dict] = []
        self.chunk = 2048
        outer = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):
                pass

            def setup(self):
                super().setup()
                # Without this, Nagle's algorithm + delayed ACK add ~40 ms on localhost,
                # which would be wrongly counted as engine latency.
                self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length) or b"{}")
                u = urlparse(self.path)
                outer.requests.append({"path": u.path, "query": parse_qs(u.query),
                                       "key": self.headers.get("xi-api-key"), "body": body})
                b = outer.behaviour
                if b in ("401", "429"):
                    msg = json.dumps({"detail": {"status": "error", "message": b}}).encode()
                    self.send_response(int(b))
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(msg)))
                    self.end_headers()
                    self.wfile.write(msg)
                    return
                if b == "hang":
                    time.sleep(3)
                    return
                audio = tone_pcm(0.06 * max(1, len(body.get("text", "")) // 4 + 1) / 1.5)
                time.sleep(outer.ttfb_s)
                self.send_response(200)
                self.send_header("Content-Type", "audio/pcm")
                self.send_header("Content-Length", str(len(audio)))
                self.end_headers()
                send = audio if b == "ok" else audio[: len(audio) // 3]
                for i in range(0, len(send), outer.chunk):
                    self.wfile.write(send[i:i + outer.chunk])
                    self.wfile.flush()
                    time.sleep(0.002)
                if b == "drop":
                    self.close_connection = True
                    try:
                        self.connection.shutdown(2)
                    except OSError:
                        pass

        class QuietServer(ThreadingHTTPServer):
            def handle_error(self, request, client_address):
                pass       # client hung up early (e.g. a cancelled turn): expected in tests

        self.server = QuietServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self._t = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self._t.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()
