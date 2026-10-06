"""
Task 04: Voice Transformer - server configuration
Multimedia Systems Laboratory
Author: Rudranshpardeshi09

Port of lib/server/config.ts. Values come from the process environment and,
if present, task-04-voice-transformer/.env (process environment wins).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Mapping, Optional

TASK_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = TASK_DIR / ".env"

DEFAULT_MODEL_ID = "eleven_multilingual_sts_v2"
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"
DEFAULT_TIMEOUT_MS = 45000
DEFAULT_MAX_DURATION_SECONDS = 30
DEFAULT_MAX_SIZE_MB = 15

# A recording stopped at exactly 30.0 s can probe as 30.05 s once the encoder
# pads the final frame; allow that much overshoot on the server.
SERVER_DURATION_TOLERANCE_SECONDS = 0.5


def _parse_env_file(path: Path) -> Dict[str, str]:
    """Read KEY=VALUE lines from a .env file (python-dotenv if available)."""
    if not path.is_file():
        return {}
    try:
        from dotenv import dotenv_values  # type: ignore
        return {k: v for k, v in dotenv_values(str(path)).items() if v is not None}
    except ImportError:
        pass

    values = {}
    pattern = re.compile(r"^\s*([A-Za-z0-9_]+)\s*=\s*(.*?)\s*$")
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("#"):
            continue
        match = pattern.match(line)
        if not match:
            continue
        value = re.sub(r"\s+#.*$", "", match.group(2)).strip()
        value = re.sub(r"^([\"'])(.*)\1$", r"\2", value)
        values[match.group(1)] = value
    return values


def load_env(env_file: Optional[Path] = None) -> Dict[str, str]:
    """Merge the .env file with os.environ (os.environ takes precedence)."""
    merged = _parse_env_file(env_file or ENV_FILE)
    merged.update(os.environ)
    return merged


def _read_number(value: Optional[str], fallback: float, lo: float, hi: float) -> float:
    """Parse a number and clamp it into [lo, hi]; fall back if missing/invalid."""
    if value is None or str(value).strip() == "":
        return fallback
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    if parsed != parsed or parsed in (float("inf"), float("-inf")):
        return fallback
    return min(hi, max(lo, parsed))


def _read_bool(value: Optional[str], fallback: bool) -> bool:
    """Parse 1/true/yes/on as True; anything else non-empty as False."""
    if value is None or value == "":
        return fallback
    return value.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Settings:
    """Runtime configuration for the voice transformer."""
    api_key: Optional[str] = None
    model_id: str = DEFAULT_MODEL_ID
    remove_background_noise: bool = False
    timeout_s: float = DEFAULT_TIMEOUT_MS / 1000.0
    max_duration_s: float = float(DEFAULT_MAX_DURATION_SECONDS)
    max_size_mb: float = float(DEFAULT_MAX_SIZE_MB)
    output_format: str = DEFAULT_OUTPUT_FORMAT
    # The merged environment, kept so voice IDs can be resolved. Never printed.
    env: Dict[str, str] = field(default_factory=dict, repr=False)

    @property
    def is_configured(self) -> bool:
        """True when an ElevenLabs API key is present."""
        return bool(self.api_key)

    @property
    def max_size_bytes(self) -> int:
        """Maximum upload size in bytes."""
        return int(round(self.max_size_mb * 1024 * 1024))

    def __repr__(self) -> str:
        key = "set" if self.api_key else "missing"
        return (f"Settings(api_key=<{key}>, model_id={self.model_id!r}, "
                f"remove_background_noise={self.remove_background_noise}, "
                f"timeout_s={self.timeout_s}, max_duration_s={self.max_duration_s}, "
                f"max_size_mb={self.max_size_mb}, output_format={self.output_format!r})")


def load_settings(env: Optional[Mapping[str, str]] = None) -> Settings:
    """Build Settings from `env`, or from os.environ + the task .env file when None."""
    source = dict(env) if env is not None else load_env()
    api_key = (source.get("ELEVENLABS_API_KEY") or "").strip() or None
    model_id = (source.get("ELEVENLABS_MODEL_ID") or "").strip() or DEFAULT_MODEL_ID
    timeout_ms = _read_number(source.get("ELEVENLABS_TIMEOUT_MS"), DEFAULT_TIMEOUT_MS, 5000, 120000)
    return Settings(
        api_key=api_key,
        model_id=model_id,
        remove_background_noise=_read_bool(source.get("ELEVENLABS_REMOVE_BACKGROUND_NOISE"), False),
        timeout_s=timeout_ms / 1000.0,
        max_duration_s=_read_number(source.get("MAX_AUDIO_DURATION_SECONDS"),
                                    DEFAULT_MAX_DURATION_SECONDS, 1, 300),
        max_size_mb=_read_number(source.get("MAX_AUDIO_SIZE_MB"), DEFAULT_MAX_SIZE_MB, 0.1, 100),
        output_format=DEFAULT_OUTPUT_FORMAT,
        env=source,
    )
