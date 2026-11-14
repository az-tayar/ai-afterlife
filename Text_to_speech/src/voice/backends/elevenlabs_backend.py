"""ElevenLabs streaming backend - the team's chosen TTS provider (blueprint, Phase 3).

Calls ``POST /v1/text-to-speech/{voice_id}/stream`` with ``output_format=pcm_22050``.
The response body is raw 16-bit little-endian mono PCM that arrives while the
voice is still being generated, so the first sound can be played long before
the phrase is finished. ``eleven_flash_v2_5`` is ElevenLabs' low-latency model.

Each phrase also sends the end of the previous phrase as ``previous_text`` so
the intonation flows naturally from one phrase to the next.
"""

from __future__ import annotations

import threading
from typing import Iterator

import requests

from ..audio import SAMPLE_RATE
from .base import BackendError, TTSBackend

_ERRORS = {
    400: ("bad request (check voice settings)", False),
    401: ("API key rejected (check ELEVENLABS_API_KEY)", False),
    403: ("not allowed on this plan or voice", False),
    404: ("voice id not found", False),
    422: ("request rejected (text or parameters invalid)", False),
    429: ("rate limit or monthly credits exhausted", True),
}


class ElevenLabsBackend(TTSBackend):
    name = "elevenlabs"
    streaming = True

    def __init__(self, api_key: str, base_url: str = "https://api.elevenlabs.io",
                 model_id: str = "eleven_flash_v2_5", connect_timeout_s: float = 3.0,
                 read_timeout_s: float = 5.0, chunk_bytes: int = 2048,
                 voice_settings: dict | None = None, session: requests.Session | None = None,
                 **_ignored):
        self.api_key = (api_key or "").strip()
        self.base_url = base_url.rstrip("/")
        self._model_id = model_id
        self.timeout = (float(connect_timeout_s), float(read_timeout_s))
        self.chunk_bytes = int(chunk_bytes)
        self.voice_settings = dict(voice_settings or {})
        self._session = session or requests.Session()   # keep-alive saves a TLS handshake per phrase

    def model_id(self) -> str:
        return self._model_id

    def voice_id_for(self, voice) -> str:
        return voice.elevenlabs_voice_id

    def is_available(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "no ELEVENLABS_API_KEY set"
        return True, f"key set, model {self._model_id}"

    def build_request(self, text: str, voice, previous_text: str = ""):
        url = f"{self.base_url}/v1/text-to-speech/{voice.elevenlabs_voice_id}/stream"
        params = {"output_format": f"pcm_{SAMPLE_RATE}"}
        body = {"text": text, "model_id": self._model_id}
        if self.voice_settings:
            body["voice_settings"] = self.voice_settings
        if previous_text:
            body["previous_text"] = previous_text[-300:]
        headers = {"xi-api-key": self.api_key, "Content-Type": "application/json"}
        return url, params, body, headers

    def synthesize(self, text: str, voice, cancel: threading.Event,
                   previous_text: str = "") -> Iterator[bytes]:
        ok, why = self.is_available()
        if not ok:
            raise BackendError(why, retryable=False)
        if not voice.elevenlabs_voice_id:
            raise BackendError(f"voice '{voice.key}' has no ElevenLabs voice id", retryable=False)

        url, params, body, headers = self.build_request(text, voice, previous_text)
        try:
            resp = self._session.post(url, params=params, json=body, headers=headers,
                                      stream=True, timeout=self.timeout)
        except requests.Timeout as e:
            raise BackendError(f"ElevenLabs timed out ({e.__class__.__name__})") from e
        except requests.RequestException as e:
            raise BackendError(f"ElevenLabs unreachable ({e.__class__.__name__})") from e

        with resp:
            if resp.status_code != 200:
                msg, retry = _ERRORS.get(resp.status_code, (f"HTTP {resp.status_code}", True))
                detail = ""
                try:
                    detail = str(resp.json().get("detail", ""))[:160]
                except ValueError:
                    pass
                raise BackendError(f"ElevenLabs {resp.status_code}: {msg} {detail}".strip(),
                                   status=resp.status_code, retryable=retry)
            carry = b""
            try:
                for data in resp.iter_content(chunk_size=self.chunk_bytes):
                    if cancel.is_set():
                        return            # leaving the 'with' closes the connection
                    if not data:
                        continue
                    data = carry + data
                    even = len(data) - (len(data) % 2)   # never split a 16-bit sample
                    carry = data[even:]
                    if even:
                        yield data[:even]
            except requests.RequestException as e:
                raise BackendError(f"ElevenLabs stream broke ({e.__class__.__name__})") from e
