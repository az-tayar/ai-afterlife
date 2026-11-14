"""Tests for the TTS engine.   Run:  python -m pytest -q

Cloud behaviour is tested against tests/mock_elevenlabs.py (no key or credits
needed). The offline voice tests use the real system voice and are skipped if
the computer has none.
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from evaluation.latency_metrics import MetricsLog, percentile, summarize  # noqa: E402
from mock_elevenlabs import MockElevenLabs                                # noqa: E402
from voice.audio import (SAMPLE_RATE, read_wav, resample_pcm16, to_mono_pcm16,  # noqa: E402
                         wav_bytes)
from voice.backends import BackendError, ElevenLabsBackend, SystemVoiceBackend, TTSBackend  # noqa: E402
from voice.cache import PhraseCache                                       # noqa: E402
from voice.config import load_settings                                    # noqa: E402
from voice.playback import LocalPlayer                                    # noqa: E402
from voice.text_chunker import PhraseChunker, normalize_text, split_text  # noqa: E402
from voice.tts import TTSEngine, TTSError                                 # noqa: E402
from voice.voice_registry import ConsentError, VoiceRegistry              # noqa: E402

ANSWER = ("Oh, the summer of 1974! Your grandmother and I drove all the way to Halifax in "
          "that old blue Volkswagen. It broke down twice, and we laughed the whole way there.")


# ---------------------------------------------------------------- helpers
class FakeBackend(TTSBackend):
    """Deterministic backend: 0.1 s of audio per 10 characters."""

    def __init__(self, name="fake", fail=None, delay_s=0.0):
        self.name, self.fail, self.delay_s, self.calls = name, fail, delay_s, []

    def is_available(self):
        return True, "fake"

    def synthesize(self, text, voice, cancel, previous_text=""):
        self.calls.append(text)
        if self.fail == "before":
            raise BackendError("simulated outage")
        n = max(1, len(text) // 10)
        for i in range(n):
            if cancel.is_set():
                return
            time.sleep(self.delay_s)
            if self.fail == "middle" and i == 1:
                raise BackendError("simulated drop")
            yield b"\x01\x00" * int(SAMPLE_RATE * 0.1)


def make_engine(tmp_path, backends, mode="auto", cache_mode="off", **over):
    s = load_settings(overrides={"mode": mode, "disclosure": {"enabled": False}, **over})
    return TTSEngine(settings=s, backends=backends,
                     cache=PhraseCache(tmp_path / "cache", mode=cache_mode),
                     metrics_log=MetricsLog(tmp_path / "m.jsonl"))


def tokens(text, delay=0.0):
    import re
    for t in re.findall(r"\S+\s*", text):
        if delay:
            time.sleep(delay)
        yield t


# ---------------------------------------------------------- text handling
def test_normalize_removes_markdown_citations_urls():
    t = normalize_text("**My advice?** Visit [our page](https://x.org) [2] or www.site.com. ## Done")
    assert "*" not in t and "[2]" not in t and "https" not in t and "#" not in t
    assert "our page" in t and "a link" in t


def test_bullets_become_sentences():
    assert normalize_text("# Memories\n- Fishing\n- The blue car") == "Memories. Fishing. The blue car."


def test_chunker_first_phrase_is_short_and_later_are_sentences():
    parts = split_text(ANSWER)
    assert parts[0] == "Oh, the summer of 1974!"
    assert all(p[-1] in ".!?" for p in parts)
    assert " ".join(parts) == normalize_text(ANSWER)


def test_chunker_ignores_abbreviations_and_initials():
    parts = split_text("Yes. Dr. Patel lived on Elm St. near J. Smith, our old friend from work.")
    assert parts == ["Yes.", "Dr. Patel lived on Elm St. near J. Smith, our old friend from work."]


def test_streamed_tokens_give_same_phrases_as_whole_text():
    c = PhraseChunker()
    out = []
    for t in tokens(ANSWER):
        out += c.feed(t)
    out += c.flush()
    assert out == split_text(ANSWER)


def test_citation_split_across_tokens_is_removed_whole():
    c = PhraseChunker()
    out = []
    for piece in ["We fished every Sunday [", "source: interview", " 3]. It was our time."]:
        out += c.feed(piece)
    out += c.flush()
    assert all("source" not in p and "[" not in p for p in out)


def test_hard_limit_never_exceeded():
    long = "word " * 200
    assert all(len(p) <= 260 for p in split_text(long))


# ------------------------------------------------------------------ audio
def test_resample_and_wav_roundtrip():
    pcm = (np.sin(np.arange(16000) / 10) * 9000).astype("<i2").tobytes()
    up = resample_pcm16(pcm, 16000, SAMPLE_RATE)
    assert abs(len(up) // 2 - SAMPLE_RATE) <= 1
    back, sr = read_wav(wav_bytes(up))
    assert sr == SAMPLE_RATE and back == up


def test_stereo_to_mono():
    stereo = np.array([[1000, 3000], [-1000, -3000]], dtype="<i2").tobytes()
    assert np.frombuffer(to_mono_pcm16(stereo, 2, 2), dtype="<i2").tolist() == [2000, -2000]


# ------------------------------------------------------------- ElevenLabs
@pytest.fixture
def mock_el():
    with MockElevenLabs() as m:
        yield m


def el_backend(url, key="test-key", read_timeout=1.0):
    return ElevenLabsBackend(api_key=key, base_url=url, read_timeout_s=read_timeout,
                             connect_timeout_s=1.0, voice_settings={"stability": 0.5})


def test_elevenlabs_request_shape(mock_el, tmp_path):
    eng = make_engine(tmp_path, {"elevenlabs": el_backend(mock_el.url)}, mode="elevenlabs")
    chunks = list(eng.synthesize_speech(ANSWER))
    assert sum(len(c.pcm) for c in chunks) > 0
    r0, r1 = mock_el.requests[0], mock_el.requests[1]
    assert r0["path"] == "/v1/text-to-speech/JBFqnCBsd6RMkjVDRZzb/stream"
    assert r0["query"]["output_format"] == ["pcm_22050"]
    assert r0["key"] == "test-key"
    assert r0["body"]["model_id"] == "eleven_flash_v2_5"
    assert "previous_text" not in r0["body"]
    assert r1["body"]["previous_text"].endswith("1974!")      # prosody continuity
    assert all(len(c.pcm) % 2 == 0 for c in chunks)            # whole 16-bit samples only


def test_elevenlabs_streams_before_phrase_finishes(mock_el, tmp_path):
    eng = make_engine(tmp_path, {"elevenlabs": el_backend(mock_el.url)}, mode="elevenlabs")
    chunks = [c for c in eng.synthesize_speech("Your grandmother and I drove all the way to "
                                               "Halifax in that old blue Volkswagen.") if c.pcm]
    assert len(chunks) > 3                       # many network chunks for one phrase
    assert eng.last_metrics.first_audio_ms < 500


@pytest.mark.parametrize("behaviour", ["401", "429", "hang", "drop"])
def test_cloud_failure_falls_back_to_offline_voice(mock_el, tmp_path, behaviour):
    mock_el.behaviour = behaviour
    backup = FakeBackend("system")
    eng = make_engine(tmp_path, {"elevenlabs": el_backend(mock_el.url, read_timeout=0.5),
                                 "system": backup})
    chunks = list(eng.synthesize_speech(ANSWER))
    m = eng.last_metrics
    assert sum(len(c.pcm) for c in chunks) > 0             # never silence
    assert "system" in m.backends and m.fallbacks
    assert len(mock_el.requests) == 1                      # failed cloud is not retried in the same turn
    assert len(backup.calls) == len(m.phrases)             # whole answer spoken by the backup


def test_missing_key_uses_offline_without_network(tmp_path):
    backup = FakeBackend("system")
    eng = make_engine(tmp_path, {"elevenlabs": ElevenLabsBackend(api_key=""), "system": backup})
    list(eng.synthesize_speech("Hello there, my dear."))
    assert eng.last_metrics.backends == ["system"]
    assert "no ELEVENLABS_API_KEY" in eng.last_metrics.fallbacks[0]


def test_cloud_is_retried_after_cooldown(mock_el, tmp_path):
    mock_el.behaviour = "429"
    eng = make_engine(tmp_path, {"elevenlabs": el_backend(mock_el.url), "system": FakeBackend("system")},
                      fallback={"retry_cloud_after_s": 0.3})
    list(eng.synthesize_speech("First question answer."))
    list(eng.synthesize_speech("Second answer, during cooldown."))
    assert len(mock_el.requests) == 1                      # skipped while cooling down
    mock_el.behaviour = "ok"
    time.sleep(0.35)
    list(eng.synthesize_speech("Third answer, after recovery."))
    assert eng.last_metrics.backends == ["elevenlabs"]     # recovered within the T9 target


def test_cloud_only_mode_reports_error_instead_of_silence(tmp_path):
    eng = make_engine(tmp_path, {"elevenlabs": ElevenLabsBackend(api_key="")}, mode="elevenlabs")
    with pytest.raises(TTSError):
        list(eng.synthesize_speech("Hello."))


# --------------------------------------------------- engine behaviour
def test_mid_phrase_failure_repeats_phrase_on_backup(tmp_path):
    primary, backup = FakeBackend("elevenlabs", fail="middle"), FakeBackend("system")
    eng = make_engine(tmp_path, {"elevenlabs": primary, "system": backup})
    list(eng.synthesize_speech(ANSWER))
    m = eng.last_metrics
    assert "partial audio" in m.fallbacks[0]
    assert backup.calls[0] == primary.calls[0]             # same phrase spoken again in full


def test_new_turn_cancels_previous_turn(tmp_path):
    slow = FakeBackend("system", delay_s=0.05)
    eng = make_engine(tmp_path, {"system": slow}, mode="offline")
    first = eng.synthesize_speech(ANSWER)
    next(first)                                            # first answer starts speaking
    list(eng.synthesize_speech("New question answer."))    # visitor asks something new
    rest = list(first)
    assert len(rest) < 5                                   # stale answer stopped almost at once


def test_interrupt_stops_quickly(tmp_path):
    eng = make_engine(tmp_path, {"system": FakeBackend("system", delay_s=0.05)}, mode="offline")
    got = []

    def consume():
        for c in eng.synthesize_speech(ANSWER * 3):
            got.append(c)

    t = threading.Thread(target=consume)
    t.start()
    time.sleep(0.2)
    t0 = time.perf_counter()
    assert eng.interrupt()
    t.join(2)
    assert not t.is_alive() and time.perf_counter() - t0 < 0.3
    assert eng.last_metrics.cancelled


def test_llm_token_stream_overlaps_with_speech(tmp_path):
    eng = make_engine(tmp_path, {"system": FakeBackend("system")}, mode="offline")
    t0 = time.perf_counter()
    gen = eng.synthesize_speech(tokens(ANSWER, delay=0.02))
    next(gen)
    first = time.perf_counter() - t0
    list(gen)
    assert first < 0.3                                     # spoke before the LLM finished (~0.6 s)


def test_audio_chunks_have_continuous_timeline(tmp_path):
    eng = make_engine(tmp_path, {"system": FakeBackend("system")}, mode="offline")
    chunks = [c for c in eng.synthesize_speech(ANSWER) if c.pcm]
    for a, b in zip(chunks, chunks[1:]):
        assert b.start_s == pytest.approx(a.start_s + a.duration_s)


def test_disclosure_spoken_once_per_session(tmp_path):
    s = load_settings(overrides={"mode": "offline", "disclosure": {"enabled": True}})
    fake = FakeBackend("system")
    eng = TTSEngine(settings=s, backends={"system": fake},
                    cache=PhraseCache(tmp_path / "c", mode="off"), metrics_log=False)
    list(eng.synthesize_speech("First answer.", session_id="visitor-1"))
    list(eng.synthesize_speech("Second answer.", session_id="visitor-1"))
    list(eng.synthesize_speech("Hello.", session_id="visitor-2"))
    disclosures = [c for c in fake.calls if "AI representation" in c]
    assert len(disclosures) == 2


def test_cache_replays_without_calling_backend(tmp_path):
    fake = FakeBackend("system")
    eng = make_engine(tmp_path, {"system": fake}, mode="offline", cache_mode="all")
    a = eng.synthesize("A short memory about fishing.")
    b = eng.synthesize("A short memory about fishing.")
    assert a == b and len(fake.calls) == 1
    assert eng.last_metrics.phrases[0].cache_hit


def test_cancelled_audio_is_not_cached(tmp_path):
    fake = FakeBackend("system", delay_s=0.02)
    eng = make_engine(tmp_path, {"system": fake}, mode="offline", cache_mode="all")
    gen = eng.synthesize_speech("A long memory about the old house by the lake shore.")
    next(gen)
    gen.close()
    assert len(eng.cache) == 0


def test_metrics_logged_and_summarized(tmp_path):
    eng = make_engine(tmp_path, {"system": FakeBackend("system")}, mode="offline")
    for _ in range(3):
        list(eng.synthesize_speech(ANSWER))
    recs = eng.metrics_log.load()
    assert len(recs) == 3 and recs[0]["first_audio_ms"] is not None
    row = summarize(recs, 500)[0]
    assert row["backend"] == "system" and row["turns"] == 3 and row["p95_meets_target"]


def test_percentile():
    assert percentile([1, 2, 3, 4, 5], 50) == 3
    assert percentile([10, 20], 95) == 19.5
    assert percentile([], 50) is None


# --------------------------------------------------------------- consent
def test_cloned_voice_without_consent_is_refused(tmp_path):
    reg = VoiceRegistry.load(ROOT / "configs" / "voices.yaml")
    with pytest.raises(ConsentError):
        reg.get("principal_clone")
    voice, warn = reg.resolve("principal_clone")
    assert voice.kind == "stock" and "consent" in warn


def test_cloned_voice_with_consent_is_allowed(tmp_path):
    p = tmp_path / "v.yaml"
    p.write_text("default_voice: s\nvoices:\n  s: {kind: stock, elevenlabs_voice_id: a}\n"
                 "  c: {kind: cloned, elevenlabs_voice_id: b, consent: {granted: true, record_id: C-1}}\n")
    assert VoiceRegistry.load(p).get("c").elevenlabs_voice_id == "b"


def test_engine_falls_back_to_stock_voice_and_warns(tmp_path):
    fake = FakeBackend("system")
    eng = make_engine(tmp_path, {"system": fake}, mode="offline")
    list(eng.synthesize_speech("Hello.", voice="principal_clone"))
    assert eng.last_metrics.voice == "stock_warm_male" and eng.last_metrics.warnings


# ---------------------------------------------------------------- player
class FakeStream:
    """Pretends to be a sound card: pulls blocks from the callback at 20x real time."""

    def __init__(self, cb, sr, block):
        self.cb, self.sr, self.block, self.run = cb, sr, block, False

    def start(self):
        self.run = True
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while self.run:
            buf = bytearray(self.block * 2)
            self.cb(memoryview(buf), self.block, None, None)
            time.sleep(self.block / self.sr / 20)

    def stop(self):
        self.run = False

    def close(self):
        pass


def test_player_plays_everything_and_tracks_clock(tmp_path):
    eng = make_engine(tmp_path, {"system": FakeBackend("system")}, mode="offline")
    p = LocalPlayer(stream_factory=FakeStream)
    stats = p.play(eng.synthesize_speech(ANSWER))
    assert stats["played_s"] == pytest.approx(eng.last_metrics.audio_s, abs=0.05)


def test_player_stop_discards_buffer():
    p = LocalPlayer(stream_factory=FakeStream)
    p.start()
    p.feed(b"\x00\x00" * SAMPLE_RATE * 5)
    time.sleep(0.05)
    p.stop()
    assert p.position_s < 5


# ------------------------------------------------------ real offline voice
def _system_voice_ok():
    try:
        return SystemVoiceBackend().is_available()[0]
    except Exception:
        return False


@pytest.mark.skipif(not _system_voice_ok(), reason="no system speech engine on this computer")
def test_real_offline_voice_produces_speech(tmp_path):
    eng = make_engine(tmp_path, {"system": SystemVoiceBackend()}, mode="offline")
    pcm = eng.synthesize("Hello, this is the offline backup voice.")
    a = np.frombuffer(pcm, dtype="<i2")
    assert len(a) > SAMPLE_RATE * 0.5 and np.abs(a).max() > 1000   # real, audible speech


# -------------------------------------------------------------- HTTP API
def test_http_api(tmp_path, monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    sys.path.insert(0, str(ROOT / "app"))
    import api
    api._engine = make_engine(tmp_path, {"system": FakeBackend("system")}, mode="offline")
    c = TestClient(api.app)
    assert c.get("/health").json()["backends"]["system"]["available"]
    r = c.post("/tts", json={"text": "Hello there."})
    assert r.status_code == 200 and r.content[:4] == b"RIFF"
    assert r.headers["x-tts-backends"] == "system"
    assert c.post("/tts", json={"text": "x", "mode": "bad"}).status_code == 422
    r = c.post("/tts/stream", json={"text": "Hello there, streaming."})
    assert r.status_code == 200 and r.content[:4] == b"RIFF" and len(r.content) > 1000


def test_warm_up_prerenders_the_notice_for_real_sessions(tmp_path):
    s = load_settings(overrides={"mode": "offline", "disclosure": {"enabled": True}})
    fake = FakeBackend("system")
    eng = TTSEngine(settings=s, backends={"system": fake},
                    cache=PhraseCache(tmp_path / "c", mode="fixed"), metrics_log=False)
    eng.warm_up(background=False)
    list(eng.synthesize_speech("Hi.", session_id="visitor-1"))
    assert eng.last_metrics.phrases[0].cache_hit            # notice replayed instantly
    assert eng.last_metrics.text_to_audio_ms >= 0


# ------------------------------------------- Windows SAPI path (simulated COM)
def test_windows_sapi_voice_speaks_every_phrase(tmp_path, monkeypatch):
    """Regression: on Windows only the first sentence was spoken (pyttsx3 run-once bug).

    COM is simulated, so this checks the engine's use of SAPI - a fresh file
    stream per phrase, synchronous Speak, voice selection - on any OS.
    """
    import types
    import wave as _wave
    from voice.backends import system_backend as sb

    spoken, chosen = [], []

    class Token:
        def __init__(self, i, name):
            self.Id, self._name = f"TOKEN_{i}", name

        def GetDescription(self):
            return self._name

    class Tokens:
        def __init__(self):
            self._t = [Token(0, "Microsoft David Desktop - English (United States)"),
                       Token(1, "Microsoft Zira Desktop - English (United States)")]
            self.Count = len(self._t)

        def Item(self, i):
            return self._t[i]

    class FileStream:
        def Open(self, path, mode, do_events):
            assert mode == 3
            self.path = path

        def Close(self):
            pass

    class Voice:
        Rate = 0

        def __init__(self):
            self.AudioOutputStream = None
            self._voice = None

        @property
        def Voice(self):
            return self._voice

        @Voice.setter
        def Voice(self, token):
            self._voice = token
            chosen.append(token.Id)

        def GetVoices(self):
            return Tokens()

        def Speak(self, text, flags):
            assert flags == 16                       # never parsed as XML
            spoken.append(text)
            with _wave.open(self.AudioOutputStream.path, "wb") as w:   # SAPI writes 16 kHz here
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
                w.writeframes(b"\x10\x00" * (160 * len(text)))
            return 1

    client = types.ModuleType("comtypes.client")
    client.CreateObject = lambda progid: {"SAPI.SpVoice": Voice,
                                          "SAPI.SpFileStream": FileStream}[progid]()
    comtypes = types.ModuleType("comtypes")
    comtypes.CoInitialize = lambda: None
    comtypes.client = client
    monkeypatch.setitem(sys.modules, "comtypes", comtypes)
    monkeypatch.setitem(sys.modules, "comtypes.client", client)
    monkeypatch.setattr(sb, "sys", types.SimpleNamespace(platform="win32"))

    backend = sb.SystemVoiceBackend()
    ok, detail = backend.is_available()
    assert ok and "sapi5" in detail and "2 system voice" in detail
    eng = make_engine(tmp_path, {"system": backend}, mode="offline")
    list(eng.synthesize_speech(ANSWER))
    m = eng.last_metrics
    assert len(spoken) == len(m.phrases) == 3              # every phrase, not just the first
    assert all(p.audio_s > 0 for p in m.phrases) and not m.errors
    assert chosen == ["TOKEN_0"]                           # "David" hint from voices.yaml
    backend.close()
