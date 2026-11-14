"""Settings loader: configs/settings.yaml + .env, with safe defaults.

Secrets (the ElevenLabs API key) are read only from the environment or a
local ``.env`` file, never from the YAML, so they cannot be committed to the
team's public repository by accident.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SETTINGS_PATH = PROJECT_ROOT / "configs" / "settings.yaml"
DEFAULT_VOICES_PATH = PROJECT_ROOT / "configs" / "voices.yaml"

DEFAULTS: dict = {
    "principal_name": "Walter",
    "default_voice": "stock_warm_male",
    "mode": "auto",                       # auto | elevenlabs | offline
    "elevenlabs": {
        "base_url": "https://api.elevenlabs.io",
        "model_id": "eleven_flash_v2_5",
        "connect_timeout_s": 3.0,
        "read_timeout_s": 5.0,
        "chunk_bytes": 2048,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
            "speed": 0.95,
        },
    },
    "offline": {"rate_wpm": 165, "timeout_s": 20.0},
    "chunking": {"first_min_chars": 30, "min_chars": 40,
                 "soft_max_chars": 160, "hard_max_chars": 260},
    "fallback": {"retry_cloud_after_s": 10.0},
    "cache": {"mode": "all", "dir": ".tts_cache", "max_mb": 200},
    "disclosure": {
        "enabled": True,
        "text": ("Hello. You are talking with an AI representation of {principal_name}. "
                 "It answers only from memories {principal_name} recorded and approved."),
    },
    "metrics": {"log_path": "logs/tts_metrics.jsonl", "first_audio_target_ms": 500,
                "end_to_end_target_ms": 2000},
}

VALID_MODES = ("auto", "elevenlabs", "offline")


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_dotenv_file(root: Path = PROJECT_ROOT) -> None:
    """Load .env without overriding variables that are already set."""
    env = root / ".env"
    if not env.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env, override=False)
    except ImportError:  # minimal parser if python-dotenv is missing
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_settings(path=None, overrides: dict | None = None) -> dict:
    """Return the ``tts`` settings block, merged over DEFAULTS."""
    load_dotenv_file()
    path = Path(path) if path else DEFAULT_SETTINGS_PATH
    data = {}
    if path.exists():
        data = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("tts", {})
    s = _deep_merge(DEFAULTS, data)
    if overrides:
        s = _deep_merge(s, overrides)
    env_mode = os.environ.get("TTS_MODE")
    if env_mode:
        s["mode"] = env_mode
    if s["mode"] not in VALID_MODES:
        raise ValueError(f"tts.mode must be one of {VALID_MODES}, got {s['mode']!r}")
    s["elevenlabs"]["api_key"] = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    return s


def resolve_path(p) -> Path:
    p = Path(p)
    return p if p.is_absolute() else PROJECT_ROOT / p
