"""Latency benchmark - produces the P50/P95 numbers the blueprint and test plan ask for.

    python scripts/benchmark_tts.py --mode elevenlabs --runs 5
    python scripts/benchmark_tts.py --mode offline --runs 5

Speaks a fixed set of test answers (no audio playback, so the measurement is
the engine only), with the phrase cache switched off so every run really
calls the provider. Prints a results table and saves it to results/*.csv.
Use the CSV in the Deliverable D/E test results (first-audio target < 500 ms).
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from evaluation.latency_metrics import percentile            # noqa: E402
from voice.cache import PhraseCache                          # noqa: E402
from voice.config import load_settings                       # noqa: E402
from voice.tts import TTSEngine                              # noqa: E402

TEST_ANSWERS = [
    "Yes, I remember that day very clearly.",
    "Oh, the summer of 1974! Your grandmother and I drove all the way to Halifax in that old "
    "blue Volkswagen. It broke down twice, and we laughed the whole way there.",
    "I'm sorry, that isn't something I recorded in my memories, so I can't tell you about it.",
    "My advice? Work hard, but never miss Sunday dinner with your family. "
    "That is what my own father told me, and he was right.",
    "I worked at the paper mill for thirty-one years. The work was hard, but the people "
    "there became like a second family to me, and I still miss them.",
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="auto", choices=["auto", "elevenlabs", "offline"])
    ap.add_argument("--runs", type=int, default=5, help="repetitions of the answer set")
    ap.add_argument("--voice", default=None)
    a = ap.parse_args(argv)

    s = load_settings()
    s["disclosure"]["enabled"] = False
    engine = TTSEngine(settings=s, cache=PhraseCache(ROOT / ".tts_cache", mode="off"))
    target = s["metrics"]["first_audio_target_ms"]
    rows = []
    for run in range(1, a.runs + 1):
        for i, text in enumerate(TEST_ANSWERS, 1):
            list(engine.synthesize_speech(text, mode=a.mode, voice=a.voice))
            m = engine.last_metrics
            rows.append({"run": run, "answer": i, "chars": len(text),
                         "backend": "+".join(m.backends), "first_audio_ms": m.first_audio_ms,
                         "total_ms": m.total_ms, "audio_s": round(m.audio_s, 2), "rtf": m.rtf,
                         "fallbacks": " | ".join(m.fallbacks + m.errors)})
            print(f"run {run} answer {i}: {rows[-1]['backend']:<11} first audio "
                  f"{m.first_audio_ms} ms, total {m.total_ms} ms, audio {m.audio_s:.2f} s")
            time.sleep(0.2)

    fa = [r["first_audio_ms"] for r in rows if r["first_audio_ms"] is not None]
    p50, p95 = percentile(fa, 50), percentile(fa, 95)
    rtf = percentile([r["rtf"] for r in rows], 50)
    print("\nSummary")
    print(f"  turns: {len(rows)}   backend(s): {sorted({r['backend'] for r in rows})}")
    print(f"  first audio P50: {p50} ms   P95: {p95} ms   (target < {target} ms)")
    print(f"  P50 {'MEETS' if p50 is not None and p50 < target else 'MISSES'} target, "
          f"P95 {'MEETS' if p95 is not None and p95 < target else 'MISSES'} target")
    print(f"  real-time factor P50: {rtf}  (below 1.0 = faster than real time)")

    out = ROOT / "results" / f"benchmark_{a.mode}_{datetime.now():%Y%m%d_%H%M%S}.csv"
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"  saved {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
