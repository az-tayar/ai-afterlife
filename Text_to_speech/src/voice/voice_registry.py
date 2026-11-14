"""Voice profiles and the consent rule.

The client and the team blueprint both require that a person's voice is only
reproduced with their permission ("secure voice/photo assets", "consent-based").
Every voice therefore has a *kind*:

* ``stock``  - a ready-made provider voice that belongs to nobody in the family.
* ``cloned`` - a copy of the Principal's own voice. It may only be used when a
  consent record exists (granted = true and a record id). Otherwise the
  registry refuses it and the engine falls back to the default stock voice.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


class ConsentError(Exception):
    """Raised when a cloned voice is requested without a valid consent record."""


@dataclass
class ConsentRecord:
    granted: bool = False
    record_id: str = ""
    granted_by: str = ""
    date: str = ""

    @property
    def valid(self) -> bool:
        return bool(self.granted and self.record_id.strip())


@dataclass
class VoiceProfile:
    key: str
    display_name: str
    kind: str = "stock"                    # stock | cloned
    elevenlabs_voice_id: str = ""
    offline_voice_hint: str = ""           # e.g. "David" (Windows) or "en-us" (eSpeak)
    consent: ConsentRecord = field(default_factory=ConsentRecord)

    def check_consent(self) -> None:
        if self.kind == "cloned" and not self.consent.valid:
            raise ConsentError(
                f"Voice '{self.key}' is a cloned voice and has no valid consent record "
                f"(granted + record_id). It cannot be used.")


DEFAULT_STOCK = VoiceProfile(
    key="stock_warm_male", display_name="Warm older male (stock)", kind="stock",
    elevenlabs_voice_id="JBFqnCBsd6RMkjVDRZzb", offline_voice_hint="")


class VoiceRegistry:
    def __init__(self, voices: dict[str, VoiceProfile], default_key: str):
        if not voices:
            voices = {DEFAULT_STOCK.key: DEFAULT_STOCK}
        if default_key not in voices:
            default_key = next(iter(voices))
        if voices[default_key].kind != "stock":
            raise ValueError("The default voice must be a stock voice.")
        self.voices = voices
        self.default_key = default_key

    @classmethod
    def load(cls, path, default_key: str | None = None) -> "VoiceRegistry":
        path = Path(path)
        if not path.exists():
            return cls({DEFAULT_STOCK.key: DEFAULT_STOCK}, DEFAULT_STOCK.key)
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        voices = {}
        for key, v in (raw.get("voices") or {}).items():
            c = v.get("consent") or {}
            voices[key] = VoiceProfile(
                key=key,
                display_name=v.get("display_name", key),
                kind=v.get("kind", "stock"),
                elevenlabs_voice_id=str(v.get("elevenlabs_voice_id") or ""),
                offline_voice_hint=str(v.get("offline_voice_hint") or ""),
                consent=ConsentRecord(bool(c.get("granted", False)), str(c.get("record_id") or ""),
                                      str(c.get("granted_by") or ""), str(c.get("date") or "")),
            )
        return cls(voices, default_key or raw.get("default_voice", DEFAULT_STOCK.key))

    def get(self, key: str | None) -> VoiceProfile:
        """Return the voice, or raise ConsentError / KeyError."""
        v = self.voices[key or self.default_key]
        v.check_consent()
        return v

    def resolve(self, key: str | None) -> tuple[VoiceProfile, str | None]:
        """Like get(), but never fails: returns (voice, warning)."""
        try:
            return self.get(key), None
        except KeyError:
            return self.voices[self.default_key], f"Unknown voice '{key}'; using default voice."
        except ConsentError as e:
            return self.voices[self.default_key], f"{e} Using default stock voice instead."

    def choices(self) -> list[tuple[str, str]]:
        """(label, key) pairs for a dropdown; voices without consent are marked."""
        out = []
        for k, v in self.voices.items():
            label = v.display_name
            if v.kind == "cloned" and not v.consent.valid:
                label += " (blocked - no consent record)"
            out.append((label, k))
        return out
