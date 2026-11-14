"""Phrase cache: keeps audio for phrases that have already been spoken.

Why: the disclosure sentence and common answers are spoken again and again
during testing and on Design Day. Replaying them from disk gives near-zero
first-audio latency, saves ElevenLabs credits (the project budget is
$100-$200), and still works if the network drops.

The key is a SHA-256 of (backend, voice, model, text), so a different voice,
model or wording never reuses the wrong audio. Files are raw int16 PCM at
SAMPLE_RATE, stored only on the local machine (the folder is git-ignored).
"""

from __future__ import annotations

import hashlib
import os
import threading
from pathlib import Path

from .audio import SAMPLE_RATE


class PhraseCache:
    MODES = ("off", "fixed", "all")   # fixed = only the disclosure / system phrases

    def __init__(self, directory, mode: str = "all", max_mb: float = 200):
        if mode not in self.MODES:
            raise ValueError(f"cache mode must be one of {self.MODES}")
        self.dir = Path(directory)
        self.mode = mode
        self.max_bytes = int(max_mb * 1024 * 1024)
        self._lock = threading.Lock()
        if mode != "off":
            self.dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def make_key(backend: str, voice_id: str, model: str, text: str) -> str:
        raw = "\x1f".join([backend, voice_id, model, str(SAMPLE_RATE), text.strip().lower()])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def allows(self, fixed_phrase: bool) -> bool:
        return self.mode == "all" or (self.mode == "fixed" and fixed_phrase)

    def get(self, key: str) -> bytes | None:
        if self.mode == "off":
            return None
        p = self.dir / f"{key}.pcm"
        try:
            data = p.read_bytes()
            os.utime(p, None)          # mark as recently used
            return data or None
        except OSError:
            return None

    def put(self, key: str, pcm: bytes) -> None:
        if self.mode == "off" or not pcm:
            return
        with self._lock:
            tmp = self.dir / f"{key}.tmp"
            tmp.write_bytes(pcm)
            os.replace(tmp, self.dir / f"{key}.pcm")
            self._prune()

    def _prune(self) -> None:
        files = sorted(self.dir.glob("*.pcm"), key=lambda f: f.stat().st_mtime)
        total = sum(f.stat().st_size for f in files)
        while files and total > self.max_bytes:
            f = files.pop(0)
            total -= f.stat().st_size
            f.unlink(missing_ok=True)

    def clear(self) -> int:
        n = 0
        for f in self.dir.glob("*.pcm"):
            f.unlink(missing_ok=True)
            n += 1
        return n

    def __len__(self) -> int:
        return 0 if self.mode == "off" else len(list(self.dir.glob("*.pcm")))
