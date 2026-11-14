"""Audio data types and PCM helpers shared by every part of the voice pipeline.

The whole TTS engine speaks one audio "language" internally:
16-bit signed little-endian PCM, mono, at SAMPLE_RATE (22 050 Hz).
Every backend must hand back audio in this format, so the player, the cache,
the Gradio app and the avatar never need to know which backend produced it.
"""

from __future__ import annotations

import io
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

SAMPLE_RATE = 22050   # Hz. ElevenLabs "pcm_22050" output and eSpeak/SAPI both support it.
SAMPLE_WIDTH = 2      # bytes per sample (int16)
CHANNELS = 1          # mono


@dataclass
class AudioChunk:
    """One piece of synthesized speech, as yielded by ``synthesize_speech``.

    ``start_s`` is the position of this chunk on the turn's audio timeline,
    i.e. how many seconds of audio came before it. The avatar engine can use
    it, together with the player's playback clock, to line mouth movement up
    with the sound the listener is actually hearing.
    """

    pcm: bytes                 # int16 little-endian mono PCM
    sample_rate: int
    turn_id: int
    phrase_index: int          # which phrase of the answer this belongs to (0 = first)
    text: str                  # the phrase being spoken
    backend: str               # "elevenlabs", "system" or "cache:<backend>"
    start_s: float             # offset of this chunk in the turn's audio
    is_phrase_end: bool = False

    @property
    def duration_s(self) -> float:
        return pcm_duration(self.pcm, self.sample_rate)

    def as_numpy(self) -> np.ndarray:
        return np.frombuffer(self.pcm, dtype="<i2")


def pcm_duration(pcm: bytes, sample_rate: int = SAMPLE_RATE) -> float:
    return len(pcm) / float(SAMPLE_WIDTH * sample_rate)


def split_pcm(pcm: bytes, sample_rate: int = SAMPLE_RATE, piece_s: float = 0.2):
    """Cut a block of PCM into short pieces so playback and cancellation stay responsive."""
    step = max(SAMPLE_WIDTH, int(sample_rate * piece_s) * SAMPLE_WIDTH)
    for i in range(0, len(pcm), step):
        yield pcm[i:i + step]


def resample_pcm16(pcm: bytes, src_rate: int, dst_rate: int = SAMPLE_RATE) -> bytes:
    """Linear-interpolation resampler. Adequate for speech; avoids a SciPy dependency."""
    if src_rate == dst_rate or not pcm:
        return pcm
    x = np.frombuffer(pcm, dtype="<i2").astype(np.float32)
    n_out = int(round(len(x) * dst_rate / src_rate))
    if n_out <= 0:
        return b""
    src_t = np.arange(len(x), dtype=np.float64) / src_rate
    dst_t = np.arange(n_out, dtype=np.float64) / dst_rate
    y = np.interp(dst_t, src_t, x)
    return np.clip(np.round(y), -32768, 32767).astype("<i2").tobytes()


def to_mono_pcm16(frames: bytes, channels: int, sample_width: int) -> bytes:
    """Convert raw WAV frames of any common width/channel count to int16 mono."""
    if sample_width == 1:          # unsigned 8-bit
        a = (np.frombuffer(frames, dtype=np.uint8).astype(np.int32) - 128) << 8
    elif sample_width == 2:
        a = np.frombuffer(frames, dtype="<i2").astype(np.int32)
    elif sample_width == 3:        # packed 24-bit
        b = np.frombuffer(frames, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        a = (b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16))
        a = np.where(a & 0x800000, a - 0x1000000, a) >> 8
    elif sample_width == 4:
        a = np.frombuffer(frames, dtype="<i4").astype(np.int64) >> 16
    else:
        raise ValueError(f"Unsupported WAV sample width: {sample_width}")
    if channels > 1:
        a = a.reshape(-1, channels).mean(axis=1)
    return np.clip(a, -32768, 32767).astype("<i2").tobytes()


def read_wav(source) -> tuple[bytes, int]:
    """Read a WAV file (path or bytes) and return (int16 mono PCM, sample_rate)."""
    fh = io.BytesIO(source) if isinstance(source, (bytes, bytearray)) else open(source, "rb")
    with fh, wave.open(fh, "rb") as w:
        frames = w.readframes(w.getnframes())
        pcm = to_mono_pcm16(frames, w.getnchannels(), w.getsampwidth())
        return pcm, w.getframerate()


def wav_bytes(pcm: bytes, sample_rate: int = SAMPLE_RATE) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(CHANNELS)
        w.setsampwidth(SAMPLE_WIDTH)
        w.setframerate(sample_rate)
        w.writeframes(pcm)
    return buf.getvalue()


def write_wav(path, pcm: bytes, sample_rate: int = SAMPLE_RATE) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(wav_bytes(pcm, sample_rate))
    return path


def streaming_wav_header(sample_rate: int = SAMPLE_RATE) -> bytes:
    """WAV header with 'unknown' length, so a browser can start playing a live stream."""
    data_size = 0x7FFFFFFF - 36
    byte_rate = sample_rate * CHANNELS * SAMPLE_WIDTH
    return (b"RIFF" + (data_size + 36).to_bytes(4, "little") + b"WAVE"
            + b"fmt " + (16).to_bytes(4, "little") + (1).to_bytes(2, "little")
            + CHANNELS.to_bytes(2, "little") + sample_rate.to_bytes(4, "little")
            + byte_rate.to_bytes(4, "little") + (CHANNELS * SAMPLE_WIDTH).to_bytes(2, "little")
            + (SAMPLE_WIDTH * 8).to_bytes(2, "little")
            + b"data" + data_size.to_bytes(4, "little"))
