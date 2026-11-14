"""TTS engine - turns the chatbot's answer into speech, phrase by phrase.

Public interface (as named in the team blueprint, section 5):

    synthesize_speech(text_stream) -> Iterator[AudioChunk]

``text_stream`` may be a complete string or any iterable of strings, such as
the token stream of a streaming LLM. Audio comes back as AudioChunk objects
(int16 mono PCM at 22 050 Hz) as soon as each piece is ready, so playback and
the avatar can start before the answer is finished.

Inside one call ("a turn") the engine:
  1. cancels any turn that is still speaking (a new question interrupts the old answer);
  2. resolves the voice and enforces the consent rule for cloned voices;
  3. optionally speaks the AI-identity disclosure once per visitor session;
  4. reads the text on a background thread and cuts it into phrases (PhraseChunker);
  5. speaks each phrase with the first healthy backend - ElevenLabs first, the
     offline system voice as backup - replaying from the phrase cache when possible;
  6. records timings for every phrase and appends them to the latency log.
"""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Iterable, Iterator, Optional, Union

import numpy as np

from evaluation.latency_metrics import MetricsLog, PhraseMetrics, TurnMetrics

from .audio import SAMPLE_RATE, AudioChunk, pcm_duration, split_pcm, write_wav
from .backends import BackendError, ElevenLabsBackend, SystemVoiceBackend, TTSBackend
from .cache import PhraseCache
from .config import DEFAULT_VOICES_PATH, load_settings, resolve_path
from .text_chunker import PhraseChunker
from .voice_registry import VoiceRegistry

TextStream = Union[str, Iterable[str]]

# Order in which backends are tried for each mode.
MODE_ORDER = {
    "auto": ["elevenlabs", "system"],     # cloud voice, offline backup
    "elevenlabs": ["elevenlabs"],         # cloud only (for testing the provider)
    "offline": ["system"],                # no internet needed
}


class TTSError(Exception):
    """No backend could produce any audio for the request."""


@dataclass
class _TurnState:
    avoid: set = field(default_factory=set)      # backends that already failed in this turn
    skipped_logged: set = field(default_factory=set)


class TTSEngine:
    def __init__(self, settings: Optional[dict] = None,
                 backends: Optional[dict[str, TTSBackend]] = None,
                 registry: Optional[VoiceRegistry] = None,
                 cache: Optional[PhraseCache] = None,
                 metrics_log: Union[MetricsLog, None, bool] = None):
        self.settings = s = settings or load_settings()
        self.registry = (registry if registry is not None
                         else VoiceRegistry.load(DEFAULT_VOICES_PATH, s["default_voice"]))
        if backends is None:
            backends = {"elevenlabs": ElevenLabsBackend(**s["elevenlabs"]),
                        "system": SystemVoiceBackend(**s["offline"])}
        self.backends = backends
        c = s["cache"]
        # "is not None": an empty cache has len() == 0 and would otherwise count as False
        self.cache = (cache if cache is not None
                      else PhraseCache(resolve_path(c["dir"]), c["mode"], c["max_mb"]))
        if metrics_log is None:
            metrics_log = MetricsLog(resolve_path(s["metrics"]["log_path"]))
        self.metrics_log = metrics_log or None
        self.last_metrics: Optional[TurnMetrics] = None
        self._lock = threading.Lock()
        self._turn = 0
        self._active_cancel: Optional[threading.Event] = None
        self._cooldown_until: dict[str, float] = {}
        self._disclosed_sessions: set = set()

    # ------------------------------------------------------------------ API
    def synthesize_speech(self, text_stream: TextStream, voice: Optional[str] = None,
                          mode: Optional[str] = None, session_id: Optional[str] = None,
                          cancel: Optional[threading.Event] = None,
                          on_metrics=None) -> Iterator[AudioChunk]:
        """Yield AudioChunks for ``text_stream``. See module docstring."""
        mode = mode or self.settings["mode"]
        if mode not in MODE_ORDER:
            raise ValueError(f"mode must be one of {list(MODE_ORDER)}")
        profile, warning = self.registry.resolve(voice)
        cancel_evt, turn_id = self._begin_turn(cancel)
        m = TurnMetrics(turn_id=turn_id, voice=profile.key, mode=mode)
        if warning:
            m.warnings.append(warning)

        phrases: "queue.Queue" = queue.Queue()
        disclose = self._needs_disclosure(session_id)
        producer = threading.Thread(
            target=self._produce_phrases, name=f"tts-text-{turn_id}", daemon=True,
            args=(text_stream, phrases, cancel_evt, m, disclose))
        producer.start()

        state = _TurnState()
        audio_pos = 0.0
        prev_text = ""
        idx = 0
        produced_audio = False
        finished = False
        try:
            while True:
                try:
                    kind, payload, fixed = phrases.get(timeout=0.05)
                except queue.Empty:
                    if cancel_evt.is_set():
                        break
                    continue
                if kind == "end" or cancel_evt.is_set():
                    break
                if kind == "error":
                    m.errors.append(f"text stream failed: {payload}")
                    break
                phrase = payload
                now = time.perf_counter()
                if m.t_first_phrase is None:
                    m.t_first_phrase = now
                pm = PhraseMetrics(index=idx, text=phrase, backend="", chars=len(phrase),
                                   queued_ms=round((now - m.t_start) * 1000, 1))
                for pcm, label in self._speak_phrase(phrase, profile, mode, cancel_evt,
                                                     prev_text, fixed, pm, m, state):
                    if m.t_first_audio is None:
                        m.t_first_audio = time.perf_counter()
                    chunk = AudioChunk(pcm=pcm, sample_rate=SAMPLE_RATE, turn_id=turn_id,
                                       phrase_index=idx, text=phrase, backend=label,
                                       start_s=audio_pos)
                    audio_pos += chunk.duration_s
                    produced_audio = True
                    yield chunk
                if pm.audio_s:
                    yield AudioChunk(pcm=b"", sample_rate=SAMPLE_RATE, turn_id=turn_id,
                                     phrase_index=idx, text=phrase, backend=pm.backend,
                                     start_s=audio_pos, is_phrase_end=True)
                m.phrases.append(pm)
                m.audio_s += pm.audio_s
                prev_text = (prev_text + " " + phrase).strip()[-300:]
                idx += 1
                if cancel_evt.is_set():
                    break
            finished = not cancel_evt.is_set()
            if finished and idx > 0 and not produced_audio:
                raise TTSError("No voice could speak: " + "; ".join(m.errors + m.fallbacks))
        finally:
            if not finished:
                m.cancelled = True
                cancel_evt.set()          # stops the text reader and any open download
            m.t_end = time.perf_counter()
            self.last_metrics = m
            if self.metrics_log:
                try:
                    self.metrics_log.append(m)
                except OSError:
                    pass
            if on_metrics:
                on_metrics(m)
            self._end_turn(cancel_evt)

    def interrupt(self) -> bool:
        """Stop the answer that is currently being spoken (barge-in / Stop button)."""
        with self._lock:
            if self._active_cancel and not self._active_cancel.is_set():
                self._active_cancel.set()
                return True
        return False

    def synthesize(self, text_stream: TextStream, **kw) -> bytes:
        """Return the whole answer as one block of PCM (no streaming)."""
        return b"".join(c.pcm for c in self.synthesize_speech(text_stream, **kw))

    def synthesize_to_numpy(self, text_stream: TextStream, **kw):
        """(sample_rate, int16 numpy array) - the format gr.Audio accepts."""
        return SAMPLE_RATE, np.frombuffer(self.synthesize(text_stream, **kw), dtype="<i2")

    def synthesize_to_wav(self, text_stream: TextStream, path, **kw):
        return write_wav(path, self.synthesize(text_stream, **kw), SAMPLE_RATE)

    def speak(self, text_stream: TextStream, player=None, **kw) -> TurnMetrics:
        """Speak on this computer's speakers, streaming, and block until finished."""
        from .playback import LocalPlayer
        player = player or LocalPlayer()
        player.play(self.synthesize_speech(text_stream, **kw))
        return self.last_metrics

    def disclosure_text(self) -> str:
        d = self.settings["disclosure"]
        return d["text"].format(principal_name=self.settings["principal_name"])

    def warm_up(self, background: bool = True):
        """Start the offline voice and pre-render the disclosure so the first answer is fast."""
        def _work():
            sysb = self.backends.get("system")
            if sysb:
                sysb.is_available()
            if self.settings["disclosure"]["enabled"]:
                try:   # same path as a real session, so the cached notice is reused
                    for _ in self.synthesize_speech("", session_id="__warm_up__"):
                        pass
                except Exception:
                    pass
        if background:
            threading.Thread(target=_work, name="tts-warmup", daemon=True).start()
        else:
            _work()

    def status(self) -> dict:
        out = {"mode": self.settings["mode"], "default_voice": self.registry.default_key,
               "cache_entries": len(self.cache), "backends": {}}
        now = time.monotonic()
        for name, b in self.backends.items():
            ok, why = b.is_available()
            cool = max(0.0, self._cooldown_until.get(name, 0) - now)
            out["backends"][name] = {"available": ok, "detail": why,
                                     "cooling_down_s": round(cool, 1)}
        return out

    # ------------------------------------------------------------ internals
    def _begin_turn(self, cancel):
        with self._lock:
            if self._active_cancel is not None:
                self._active_cancel.set()          # new question -> cancel the stale answer
            evt = cancel or threading.Event()
            self._active_cancel = evt
            self._turn += 1
            return evt, self._turn

    def _end_turn(self, evt):
        with self._lock:
            if self._active_cancel is evt:
                self._active_cancel = None

    def _needs_disclosure(self, session_id) -> bool:
        if not self.settings["disclosure"]["enabled"] or session_id is None:
            return False
        with self._lock:
            if session_id in self._disclosed_sessions:
                return False
            self._disclosed_sessions.add(session_id)
            return True

    def _produce_phrases(self, text_stream, q, cancel_evt, m: TurnMetrics, disclose: bool):
        chunker = PhraseChunker(**self.settings["chunking"])
        try:
            if disclose:
                m.t_first_text = time.perf_counter()      # the notice is the first text spoken
                q.put(("phrase", self.disclosure_text(), True))
            pieces = [text_stream] if isinstance(text_stream, str) else text_stream
            for piece in pieces:
                if cancel_evt.is_set():
                    return
                if not piece:
                    continue
                piece = str(piece)
                if m.t_first_text is None and piece.strip():
                    m.t_first_text = time.perf_counter()
                for ph in chunker.feed(piece):
                    q.put(("phrase", ph, False))
            if not cancel_evt.is_set():
                for ph in chunker.flush():
                    q.put(("phrase", ph, False))
        except Exception as e:  # the chatbot's stream failed: say what we have so far
            for ph in chunker.flush():
                q.put(("phrase", ph, False))
            q.put(("error", f"{e.__class__.__name__}: {e}", False))
        finally:
            q.put(("end", None, False))

    def _ready(self, name: str, backend: TTSBackend, mode: str):
        ok, why = backend.is_available()
        if not ok:
            return False, why
        if mode == "auto":
            left = self._cooldown_until.get(name, 0) - time.monotonic()
            if left > 0:
                return False, f"recent failure, retrying in {left:.0f} s"
        return True, why

    def _mark_failed(self, name: str, err: BackendError):
        wait = float(self.settings["fallback"]["retry_cloud_after_s"])
        if not err.retryable:
            wait = max(wait, 60.0)
        self._cooldown_until[name] = time.monotonic() + wait

    def _speak_phrase(self, phrase, profile, mode, cancel, prev_text, fixed,
                      pm: PhraseMetrics, m: TurnMetrics, state: _TurnState):
        """Yield (pcm, backend_label) for one phrase, trying backends in order."""
        last_err = None
        for name in MODE_ORDER[mode]:
            backend = self.backends.get(name)
            if backend is None or name in state.avoid:
                continue
            ok, why = self._ready(name, backend, mode)
            if not ok:
                if name not in state.skipped_logged:
                    m.fallbacks.append(f"{name} skipped: {why}")
                    state.skipped_logged.add(name)
                last_err = why
                continue
            t0 = time.perf_counter()
            key = self.cache.make_key(name, backend.voice_id_for(profile), backend.model_id(), phrase)

            if self.cache.allows(fixed):
                cached = self.cache.get(key)
                if cached:
                    pm.backend, pm.cache_hit = f"cache:{name}", True
                    pm.first_audio_ms = round((time.perf_counter() - t0) * 1000, 1)
                    for piece in split_pcm(cached):
                        if cancel.is_set():
                            return
                        yield piece, pm.backend
                    pm.synth_ms = round((time.perf_counter() - t0) * 1000, 1)
                    pm.audio_s = round(pcm_duration(cached), 3)
                    return

            pm.backend, got = name, []
            try:
                for pcm in backend.synthesize(phrase, profile, cancel, previous_text=prev_text):
                    if not got:
                        pm.first_audio_ms = round((time.perf_counter() - t0) * 1000, 1)
                    got.append(pcm)
                    yield pcm, name
            except BackendError as e:
                last_err = e
                self._mark_failed(name, e)
                state.avoid.add(name)
                note = " after partial audio; backup voice repeats the phrase" if got else ""
                m.fallbacks.append(f"{name} failed on phrase {pm.index}: {e}{note}")
                continue
            if cancel.is_set():
                return
            audio = b"".join(got)
            pm.synth_ms = round((time.perf_counter() - t0) * 1000, 1)
            pm.audio_s = round(pcm_duration(audio), 3)
            self._cooldown_until.pop(name, None)
            if audio and self.cache.allows(fixed):
                self.cache.put(key, audio)
            return
        m.errors.append(f"no voice could speak phrase {pm.index}: {last_err or 'no backend available'}")


# --------------------------------------------------------------------------
# Module-level convenience API (one shared engine per process)
_default_engine: Optional[TTSEngine] = None
_default_lock = threading.Lock()


def get_engine() -> TTSEngine:
    global _default_engine
    with _default_lock:
        if _default_engine is None:
            _default_engine = TTSEngine()
        return _default_engine


def synthesize_speech(text_stream: TextStream, **kw) -> Iterator[AudioChunk]:
    """Blueprint interface: stream text in, stream AudioChunks out."""
    return get_engine().synthesize_speech(text_stream, **kw)


def speak(text_stream: TextStream, **kw) -> TurnMetrics:
    """Say it out loud on this computer's speakers."""
    return get_engine().speak(text_stream, **kw)


def interrupt() -> bool:
    return get_engine().interrupt()
