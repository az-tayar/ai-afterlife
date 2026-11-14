"""Command-line entry point.

    python -m voice "Hello there"                 speak on this computer's speakers
    python -m voice "Hello" --out hello.wav       save a WAV instead
    python -m voice "Hello" --mode offline        force the offline backup voice
    python -m voice --check                       show what is available
"""

from __future__ import annotations

import argparse
import json
import sys

from .playback import LocalPlayer
from .tts import TTSEngine


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m voice", description="Team 4 TTS engine")
    ap.add_argument("text", nargs="?", help="text to speak")
    ap.add_argument("--mode", choices=["auto", "elevenlabs", "offline"])
    ap.add_argument("--voice", help="voice key from configs/voices.yaml")
    ap.add_argument("--out", help="write a WAV file instead of playing")
    ap.add_argument("--check", action="store_true", help="print backend / speaker status")
    a = ap.parse_args(argv)

    engine = TTSEngine()
    if a.check or not a.text:
        st = engine.status()
        st["speakers"] = LocalPlayer.available()[1]
        print(json.dumps(st, indent=2))
        if not a.text:
            return 0
    if a.out:
        engine.synthesize_to_wav(a.text, a.out, mode=a.mode, voice=a.voice)
        print(f"wrote {a.out}")
    else:
        ok, why = LocalPlayer.available()
        if not ok:
            print(f"Cannot play: {why}. Use --out file.wav instead.", file=sys.stderr)
            return 2
        engine.speak(a.text, mode=a.mode, voice=a.voice)
    m = engine.last_metrics
    print(f"backend(s): {', '.join(m.backends) or '-'} | first audio: {m.first_audio_ms} ms | "
          f"audio: {m.audio_s:.2f} s | total: {m.total_ms} ms")
    for note in m.fallbacks + m.warnings + m.errors:
        print("  note:", note)
    return 0


if __name__ == "__main__":
    sys.exit(main())
