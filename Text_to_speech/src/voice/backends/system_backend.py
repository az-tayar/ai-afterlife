"""Offline backup voice: the computer's own speech synthesizer.

* Windows: Microsoft SAPI5 voices (e.g. "Microsoft David", "Microsoft Zira"),
  driven directly through COM (comtypes).
* Linux:   eSpeak NG via pyttsx3.   * macOS: NSSpeechSynthesizer via pyttsx3.

It needs no internet, no account and no money, so the demo keeps talking
when ElevenLabs is unreachable or out of credits (test T9: network failure
must never leave the visitor with silence or a crash).

Why Windows does not use pyttsx3: pyttsx3's SAPI5 driver has a long-standing
bug where only the first runAndWait() produces speech; later calls return
without writing any audio, so only the first sentence of an answer was spoken.
Calling SAPI directly (SpVoice speaking into an SpFileStream) has no such state
and renders every phrase reliably.

SAPI is a COM component and must be used from the thread that created it,
so all synthesis runs on one dedicated worker thread fed by a job queue.
Each phrase is rendered to a temporary WAV, converted to the pipeline format
(int16 mono, 22 050 Hz) and then released in 0.2 s pieces.
"""

from __future__ import annotations

import math
import os
import queue
import sys
import tempfile
import threading
import time
import wave
from concurrent.futures import Future
from typing import Iterator

from ..audio import SAMPLE_RATE, read_wav, resample_pcm16, split_pcm
from .base import BackendError, TTSBackend


def _wait_for_file(path: str, timeout_s: float = 1.0) -> None:
    """Some drivers return before the WAV is fully on disk; give it a moment."""
    end = time.monotonic() + timeout_s
    while time.monotonic() < end:
        if os.path.exists(path) and os.path.getsize(path) > 44:
            return
        time.sleep(0.025)


class _SapiRenderer:
    """Windows SAPI5 through COM. One SpVoice; a fresh SpFileStream per phrase."""

    kind = "sapi5"
    SSFM_CREATE_FOR_WRITE = 3    # SpeechStreamFileMode.SSFMCreateForWrite
    SVSF_IS_NOT_XML = 16         # synchronous Speak; never parse the text as SSML/XML

    def __init__(self, rate_wpm: int):
        import comtypes.client as cc
        self._cc = cc
        self.voice = cc.CreateObject("SAPI.SpVoice")
        # SAPI Rate runs -10..10 (0 = the voice's normal pace, about 200 words/min);
        # each step is roughly 10 % faster or slower.
        rate = int(round(math.log(max(rate_wpm, 50) / 200.0, 1.1)))
        self.voice.Rate = max(-10, min(10, rate))
        tokens = self.voice.GetVoices()
        self._tokens = [tokens.Item(i) for i in range(tokens.Count)]

    def voices(self) -> list[tuple[str, str]]:
        return [(t.Id, t.GetDescription()) for t in self._tokens]

    def set_voice(self, voice_id: str) -> None:
        for t in self._tokens:
            if t.Id == voice_id:
                self.voice.Voice = t
                return

    def render(self, text: str, path: str):
        stream = self._cc.CreateObject("SAPI.SpFileStream")
        stream.Open(path, self.SSFM_CREATE_FOR_WRITE, False)
        try:
            self.voice.AudioOutputStream = stream
            self.voice.Speak(text, self.SVSF_IS_NOT_XML)     # returns when the phrase is done
        finally:
            stream.Close()
        _wait_for_file(path)
        return read_wav(path)


class _Pyttsx3Renderer:
    """pyttsx3 for Linux (eSpeak NG) and macOS, and a last resort on Windows."""

    kind = "pyttsx3"

    def __init__(self, rate_wpm: int):
        import pyttsx3
        self._pyttsx3 = pyttsx3
        self.rate_wpm = rate_wpm
        self.voice_id = None
        self.engine = self._new_engine()

    def _new_engine(self):
        engine = self._pyttsx3.init()
        engine.setProperty("rate", self.rate_wpm)
        if self.voice_id:
            engine.setProperty("voice", self.voice_id)
        return engine

    def voices(self) -> list[tuple[str, str]]:
        return [(v.id, v.name) for v in self.engine.getProperty("voices")]

    def set_voice(self, voice_id: str) -> None:
        self.voice_id = voice_id
        self.engine.setProperty("voice", voice_id)

    def render(self, text: str, path: str):
        if sys.platform == "win32":
            # Work around pyttsx3's run-once bug on Windows: a fresh engine per phrase.
            try:
                self.engine.stop()
            except Exception:
                pass
            self.engine = None
            self.engine = self._new_engine()
        self.engine.save_to_file(text, path)
        self.engine.runAndWait()
        _wait_for_file(path)
        return read_wav(path)


class SystemVoiceBackend(TTSBackend):
    name = "system"
    streaming = False

    def __init__(self, rate_wpm: int = 165, timeout_s: float = 20.0, default_hint: str = "",
                 **_ignored):
        self.rate_wpm = int(rate_wpm)
        self.timeout_s = float(timeout_s)
        self.default_hint = default_hint
        self._jobs: "queue.Queue" = queue.Queue()
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._init_error: str | None = None
        self._voices: list[tuple[str, str]] = []
        self._driver = ""
        self._start_lock = threading.Lock()

    # -- worker thread ----------------------------------------------------
    def _ensure_worker(self) -> None:
        with self._start_lock:
            if self._thread and self._thread.is_alive():
                self._ready.wait(timeout=15)       # may still be starting up
                return
            self._ready.clear()
            self._init_error = None
            self._jobs = queue.Queue()
            self._thread = threading.Thread(target=self._run, args=(self._jobs,),
                                            name="system-tts", daemon=True)
            self._thread.start()
        self._ready.wait(timeout=15)
        if not self._ready.is_set():
            self._init_error = "offline voice did not start within 15 s"

    def _make_renderer(self):
        if sys.platform == "win32":
            try:
                import comtypes
                comtypes.CoInitialize()       # COM must be initialized on this thread
            except Exception:
                pass
            try:
                return _SapiRenderer(self.rate_wpm)
            except Exception:
                pass                          # fall back to pyttsx3 below
        return _Pyttsx3Renderer(self.rate_wpm)

    def _run(self, jobs: "queue.Queue") -> None:
        try:
            renderer = self._make_renderer()
            self._voices = renderer.voices()
            self._driver = renderer.kind
        except Exception as e:  # missing driver / no speech engine installed
            self._init_error = f"offline voice unavailable: {e}"
            self._ready.set()
            return
        self._ready.set()
        current_hint = None
        while True:
            job = jobs.get()
            if job is None:
                return
            text, hint, fut = job
            if fut.cancelled():
                continue
            path = None
            try:
                if hint != current_hint:
                    vid = self._pick_voice(hint)
                    if vid:
                        renderer.set_voice(vid)
                    current_hint = hint
                fd, path = tempfile.mkstemp(suffix=".wav", prefix="tts_")
                os.close(fd)
                pcm, rate = self._render(renderer, text, path)
                fut.set_result(resample_pcm16(pcm, rate, SAMPLE_RATE))
            except Exception as e:
                if not fut.done():
                    fut.set_exception(e)
            finally:
                if path:
                    try:
                        os.remove(path)
                    except OSError:
                        pass

    @staticmethod
    def _render(renderer, text: str, path: str, attempts: int = 3):
        """Render one phrase, retrying if the driver left an empty or broken file."""
        last = None
        for _ in range(attempts):
            try:
                pcm, rate = renderer.render(text, path)
                if pcm:
                    return pcm, rate
                last = "empty audio"
            except (EOFError, wave.Error) as e:
                last = f"unreadable WAV ({e.__class__.__name__})"
        raise RuntimeError(f"system voice produced no audio: {last}")

    def _pick_voice(self, hint: str) -> str | None:
        hint = (hint or self.default_hint or "").lower()
        if hint:
            for vid, name in self._voices:
                if hint in (name or "").lower() or hint in (vid or "").lower():
                    return vid
        if sys.platform.startswith("linux"):       # eSpeak: prefer US English
            for vid, name in self._voices:
                if (vid or "").lower().endswith("en-us") or "english (america)" in (name or "").lower():
                    return vid
        return None   # keep the operating-system default voice

    # -- TTSBackend -----------------------------------------------------------
    def is_available(self) -> tuple[bool, str]:
        self._ensure_worker()
        if self._init_error:
            return False, self._init_error
        return True, f"{len(self._voices)} system voice(s), {self._driver}"

    def list_voices(self) -> list[tuple[str, str]]:
        self._ensure_worker()
        return list(self._voices)

    def voice_id_for(self, voice) -> str:
        return voice.offline_voice_hint or self.default_hint or "default"

    def model_id(self) -> str:
        # The renderer is part of the cache key, so audio cached by the old
        # driver is never mixed with audio from the new one.
        return f"system-{self._driver or 'unknown'}-{sys.platform}-{self.rate_wpm}wpm"

    def synthesize(self, text: str, voice, cancel: threading.Event,
                   previous_text: str = "") -> Iterator[bytes]:
        ok, why = self.is_available()
        if not ok:
            raise BackendError(why, retryable=False)
        fut: Future = Future()
        self._jobs.put((text, voice.offline_voice_hint, fut))
        deadline = time.monotonic() + self.timeout_s
        while not fut.done():
            if cancel.is_set():
                fut.cancel()
                return
            if time.monotonic() > deadline:
                fut.cancel()
                self._restart_worker()
                raise BackendError(f"offline voice took longer than {self.timeout_s:.0f} s")
            time.sleep(0.005)
        try:
            pcm = fut.result()
        except Exception as e:
            raise BackendError(f"offline voice failed: {e}") from e
        for piece in split_pcm(pcm, SAMPLE_RATE, 0.2):
            if cancel.is_set():
                return
            yield piece

    def _restart_worker(self) -> None:
        """A hung speech engine is abandoned and a fresh worker is started next time."""
        with self._start_lock:
            self._jobs.put(None)      # the old worker exits if it ever wakes up
            self._thread = None

    def close(self) -> None:
        self._jobs.put(None)
