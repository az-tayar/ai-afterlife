"""Latency instrumentation for the voice pipeline.

The blueprint's Phase 3 exit criterion is "acceptable P50/P95 first-audio
latency", with an engineering target of < 500 ms for TTS first audio and
< 2 s from end of turn to first audible speech. Every call to the engine
produces one TurnMetrics record, appended as one JSON line to
logs/tts_metrics.jsonl, and ``summarize`` turns the log into P50/P95 figures.

Definitions (all times from time.perf_counter, reported in milliseconds):
  first_audio_ms   first phrase handed to the TTS  -> first audio sample produced.
                   This is the blueprint's "TTS first audio" metric.
  text_to_audio_ms first text received from the chatbot -> first audio sample.
                   Includes waiting for the chunker to release the first phrase.
  total_ms         call start -> last audio sample produced.
  rtf              real-time factor = synthesis time / audio duration
                   (below 1.0 means speech is generated faster than it plays).
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


def _ms(a, b):
    return None if a is None or b is None else round((b - a) * 1000.0, 1)


@dataclass
class PhraseMetrics:
    index: int
    text: str
    backend: str
    chars: int
    queued_ms: float | None = None      # call start -> phrase released by the chunker
    first_audio_ms: float | None = None  # phrase sent to backend -> first audio
    synth_ms: float | None = None        # phrase sent to backend -> last audio
    audio_s: float = 0.0
    cache_hit: bool = False


@dataclass
class TurnMetrics:
    turn_id: int
    voice: str
    mode: str
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))
    t_start: float = field(default_factory=time.perf_counter)
    t_first_text: float | None = None
    t_first_phrase: float | None = None
    t_first_audio: float | None = None
    t_end: float | None = None
    phrases: list = field(default_factory=list)
    fallbacks: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    cancelled: bool = False
    audio_s: float = 0.0

    # -- derived values ----------------------------------------------------
    @property
    def first_audio_ms(self):
        return _ms(self.t_first_phrase, self.t_first_audio)

    @property
    def text_to_audio_ms(self):
        return _ms(self.t_first_text, self.t_first_audio)

    @property
    def total_ms(self):
        return _ms(self.t_start, self.t_end)

    @property
    def rtf(self):
        synth = sum((p.synth_ms or 0) for p in self.phrases if not p.cache_hit) / 1000.0
        audio = sum(p.audio_s for p in self.phrases if not p.cache_hit)
        return round(synth / audio, 3) if audio > 0 else None

    @property
    def backends(self) -> list[str]:
        seen = []
        for p in self.phrases:
            if p.backend not in seen:
                seen.append(p.backend)
        return seen

    def to_dict(self) -> dict:
        d = {k: v for k, v in asdict(self).items() if not k.startswith("t_")}
        d.update(first_audio_ms=self.first_audio_ms, text_to_audio_ms=self.text_to_audio_ms,
                 total_ms=self.total_ms, rtf=self.rtf, backends=self.backends,
                 audio_s=round(self.audio_s, 3))
        return d


def percentile(values, p: float):
    """Linear-interpolated percentile (same as numpy's default)."""
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    k = (len(vals) - 1) * p / 100.0
    lo, hi = int(k), min(int(k) + 1, len(vals) - 1)
    return round(vals[lo] + (vals[hi] - vals[lo]) * (k - lo), 1)


class MetricsLog:
    def __init__(self, path):
        self.path = Path(path)
        self._lock = threading.Lock()

    def append(self, turn: TurnMetrics) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(turn.to_dict(), ensure_ascii=False)
        with self._lock, open(self.path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def load(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()


def summarize(records: list[dict], target_ms: float = 500.0) -> list[dict]:
    """P50/P95 "TTS first audio", grouped by voice engine.

    For each turn the first phrase that was really synthesized (not replayed
    from the cache) is used, and its own first-audio time - phrase sent to the
    engine -> first audio sample - is the measurement. This is the blueprint's
    "TTS first audio" metric. Turns made only of cached phrases are skipped
    because they say nothing about how fast the provider responds.
    """
    groups: dict[str, list[tuple[dict, dict]]] = {}
    for r in records:
        fresh = [p for p in r.get("phrases", [])
                 if not p.get("cache_hit") and p.get("first_audio_ms") is not None]
        if fresh:
            groups.setdefault(fresh[0]["backend"], []).append((r, fresh[0]))
    rows = []
    for backend, items in sorted(groups.items()):
        fa = [p["first_audio_ms"] for _, p in items]
        p50, p95 = percentile(fa, 50), percentile(fa, 95)
        rows.append({
            "backend": backend, "turns": len(items),
            "first_audio_p50_ms": p50, "first_audio_p95_ms": p95,
            "text_to_audio_p50_ms": percentile([r.get("text_to_audio_ms") for r, _ in items], 50),
            "rtf_p50": percentile([r.get("rtf") for r, _ in items], 50),
            "target_ms": target_ms,
            "p50_meets_target": None if p50 is None else p50 < target_ms,
            "p95_meets_target": None if p95 is None else p95 < target_ms,
        })
    return rows
