"""
Task 04: Voice Transformer - conversion pipeline
Multimedia Systems Laboratory
Author: Rudranshpardeshi09

Port of lib/api/convert.ts. Both the CLI and the web server call `convert()`.
Every check runs before the provider is contacted, in this order:
    configuration -> voice slug -> size -> declared format -> real container -> duration
Structured JSON log lines go to stderr; audio bytes and keys are never logged.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from typing import Optional

from . import audio as audio_mod
from .config import Settings, load_settings
from .errors import AppError, GENERIC_INTERNAL_MESSAGE, INTERNAL, PROVIDER_NOT_CONFIGURED
from .providers import ElevenLabsProvider
from .voices import resolve_voice


def log_event(level: str, event: str, **fields) -> None:
    """Write one JSON log line to stderr. Pass only safe fields (sizes, timings, codes)."""
    record = {"ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
              "level": level, "event": event}
    record.update(fields)
    try:
        sys.stderr.write(json.dumps(record, default=str) + "\n")
        sys.stderr.flush()
    except Exception:
        pass


def _elapsed_ms(started: float) -> int:
    return int(round((time.perf_counter() - started) * 1000))


def convert(data: bytes, filename: str, mime: Optional[str], voice_slug: str,
            settings: Optional[Settings] = None) -> dict:
    """Validate and convert audio; returns the result dict or raises AppError."""
    started = time.perf_counter()
    try:
        return _convert(data, filename, mime, voice_slug, settings, started)
    except AppError as error:
        log_event("warn", "convert.rejected", status=error.status, code=error.code,
                  totalMs=_elapsed_ms(started))
        raise
    except Exception as error:  # never leak details to the caller
        log_event("error", "convert.unexpected", totalMs=_elapsed_ms(started),
                  errorType=type(error).__name__)
        raise AppError(500, INTERNAL, GENERIC_INTERNAL_MESSAGE)


def _convert(data, filename, mime, voice_slug, settings, started) -> dict:
    settings = settings or load_settings()
    impl = ElevenLabsProvider(settings)
    provider_name = impl.name

    # 1. configuration
    if not settings.is_configured:
        raise AppError(500, PROVIDER_NOT_CONFIGURED,
                       "The voice service is not configured on this server. "
                       "Set ELEVENLABS_API_KEY and restart.")

    # 2. voice allowlist
    voice, voice_id = resolve_voice(voice_slug, settings.env)

    # 3-5. size, format, container, duration
    info = audio_mod.validate_audio(data, filename, mime, settings)

    log_event("info", "convert.start", provider=provider_name, voiceSlug=voice["slug"],
              sourceBytes=info.size, sourceDurationSeconds=info.duration_s, container=info.format)

    try:
        result = impl.convert(bytes(data), filename or "recording", info.mime, voice_id)
    except AppError as error:
        log_event("warn", "convert.provider_failed", provider=provider_name,
                  voiceSlug=voice["slug"],
                  providerCode=error.detail.get("provider_code"),
                  providerStatus=error.detail.get("provider_status"),
                  providerDetail=error.detail.get("provider_detail"),
                  providerMessage=error.detail.get("provider_message"),
                  sourceDurationSeconds=info.duration_s, totalMs=_elapsed_ms(started))
        raise

    total_ms = _elapsed_ms(started)
    log_event("info", "convert.success", provider=provider_name, voiceSlug=voice["slug"],
              sourceDurationSeconds=info.duration_s, providerMs=result.latency_ms,
              totalMs=total_ms, outputBytes=len(result.audio))

    return {
        "audio": result.audio,
        "mime": result.mime or "audio/mpeg",
        "voice": {"slug": voice["slug"], "name": voice["name"]},
        "source": {"format": info.format, "size": info.size, "duration_s": info.duration_s},
        "timing": {"server_ms": total_ms, "provider_ms": result.latency_ms},
        "provider": provider_name,
    }
