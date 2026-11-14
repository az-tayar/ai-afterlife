"""The interface every speech-synthesis backend implements.

Keeping providers behind this one interface is the blueprint's "modular
architecture" rule: the engine, player, cache and UI never call ElevenLabs or
the operating-system voice directly, so a provider can be swapped without
touching anything else.
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from typing import Iterator, Optional


class BackendError(Exception):
    """A backend could not produce (all of) the audio for a phrase.

    ``retryable`` is True for problems that may clear by themselves (network,
    timeouts, rate limits) and False for configuration problems (bad key).
    """

    def __init__(self, message: str, *, status: Optional[int] = None, retryable: bool = True):
        super().__init__(message)
        self.status = status
        self.retryable = retryable


class TTSBackend(ABC):
    name: str = "base"
    streaming: bool = False        # True if audio arrives before the whole phrase is synthesized

    @abstractmethod
    def is_available(self) -> tuple[bool, str]:
        """(available?, human-readable reason). Must be fast and must not spend credits."""

    @abstractmethod
    def synthesize(self, text: str, voice, cancel: threading.Event,
                   previous_text: str = "") -> Iterator[bytes]:
        """Yield int16 mono PCM at audio.SAMPLE_RATE for ``text``.

        Must stop promptly when ``cancel`` is set and must raise BackendError
        (never anything else) when synthesis fails.
        """

    def voice_id_for(self, voice) -> str:
        """The provider-specific voice identifier, used in cache keys."""
        return voice.key

    def model_id(self) -> str:
        return ""

    def close(self) -> None:  # pragma: no cover - optional hook
        pass
