"""Local speaker output with true streaming, instant stop and a playback clock.

The player owns a small byte buffer. ``feed`` appends audio as it arrives
from the engine; the sound card pulls from the buffer in its own callback
thread. That gives:

* streaming - the first phrase is heard while later phrases are still being made;
* instant interruption - ``stop`` empties the buffer, so stale audio never plays;
* a playback clock - ``position_s`` counts the samples that really reached the
  speaker, which is what the blueprint says the avatar should synchronize to.

Uses the ``sounddevice`` package (PortAudio). On Windows and macOS the wheel
includes PortAudio, so nothing else needs installing.
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Iterable, Optional

from .audio import SAMPLE_RATE, SAMPLE_WIDTH, AudioChunk


class LocalPlayer:
    def __init__(self, sample_rate: int = SAMPLE_RATE, device=None, blocksize: int = 1024,
                 stream_factory: Optional[Callable] = None):
        self.sample_rate = sample_rate
        self.device = device
        self.blocksize = blocksize
        self._stream_factory = stream_factory
        self._lock = threading.Lock()
        self._buf = bytearray()
        self._done = threading.Event()
        self._finished = False
        self._stream = None
        self.frames_played = 0
        self.underruns = 0
        self.t_first_feed: Optional[float] = None
        self.t_first_sound: Optional[float] = None

    @staticmethod
    def available() -> tuple[bool, str]:
        try:
            import sounddevice as sd
            dev = sd.query_devices(kind="output")
            return True, str(dev.get("name", "default output"))
        except Exception as e:
            return False, f"no speaker output ({e.__class__.__name__}: {e})"

    @property
    def position_s(self) -> float:
        """Seconds of audio that have actually been sent to the speaker."""
        return self.frames_played / float(self.sample_rate)

    @property
    def first_sound_latency_ms(self) -> Optional[float]:
        if self.t_first_feed is None or self.t_first_sound is None:
            return None
        return round((self.t_first_sound - self.t_first_feed) * 1000, 1)

    def start(self) -> None:
        with self._lock:
            self._buf.clear()
        self._done.clear()
        self._finished = False
        self.frames_played = 0
        self.underruns = 0
        self.t_first_feed = self.t_first_sound = None
        if self._stream_factory:
            self._stream = self._stream_factory(self._callback, self.sample_rate, self.blocksize)
        else:
            import sounddevice as sd
            self._stream = sd.RawOutputStream(samplerate=self.sample_rate, channels=1,
                                              dtype="int16", blocksize=self.blocksize,
                                              device=self.device, callback=self._callback)
        self._stream.start()

    def _callback(self, outdata, frames, time_info, status) -> None:
        need = frames * SAMPLE_WIDTH
        with self._lock:
            data = bytes(self._buf[:need])
            del self._buf[:need]
            empty_now = not self._buf
        if data and self.t_first_sound is None:
            self.t_first_sound = time.perf_counter()
        self.frames_played += len(data) // SAMPLE_WIDTH
        if len(data) < need:
            if data or (not self._finished and self.t_first_sound is not None):
                self.underruns += 1        # the engine fell behind the speaker
            data += b"\x00" * (need - len(data))
        outdata[:] = data
        if self._finished and empty_now:
            self._done.set()

    def feed(self, pcm: bytes) -> None:
        if not pcm:
            return
        with self._lock:
            if self.t_first_feed is None:
                self.t_first_feed = time.perf_counter()
            self._buf.extend(pcm)

    def finish(self, timeout: Optional[float] = None) -> None:
        """No more audio is coming: wait until the buffer has played out, then close."""
        self._finished = True
        with self._lock:
            if not self._buf:
                self._done.set()
        self._done.wait(timeout)
        time.sleep(0.05)                   # let the last block leave the sound card
        self._close()

    def stop(self) -> None:
        """Silence immediately and discard anything not yet played."""
        with self._lock:
            self._buf.clear()
        self._finished = True
        self._done.set()
        self._close()

    def _close(self) -> None:
        s, self._stream = self._stream, None
        if s is not None:
            try:
                s.stop()
                s.close()
            except Exception:
                pass

    def play(self, chunks: Iterable[AudioChunk], on_chunk: Optional[Callable] = None) -> dict:
        """Play an AudioChunk stream from synthesize_speech; returns playback stats."""
        self.start()
        try:
            for c in chunks:
                self.feed(c.pcm)
                if on_chunk:
                    on_chunk(c, self)
            self.finish()
        except BaseException:
            self.stop()
            raise
        return {"played_s": round(self.position_s, 3), "underruns": self.underruns,
                "first_sound_latency_ms": self.first_sound_latency_ms}
