"""
Task 04: Voice Transformer - conversion providers
Multimedia Systems Laboratory
Author: Rudranshpardeshi09

ElevenLabsProvider is a port of lib/elevenlabs/{client,provider,errors}.ts:
    POST https://api.elevenlabs.io/v1/speech-to-speech/{voice_id}?output_format=mp3_44100_128
    multipart: audio, model_id, [remove_background_noise=true]; header xi-api-key
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote

from .errors import (AppError, P_AUTH, P_INVALID_AUDIO, P_INVALID_REQUEST, P_NETWORK,
                     P_PERMISSION, P_PLAN_REQUIRED, P_QUOTA, P_RATE_LIMIT, P_TIMEOUT, P_UPSTREAM,
                     P_VOICE_NOT_FOUND)

ELEVENLABS_API_BASE_URL = "https://api.elevenlabs.io"

# ElevenLabs errors carry a legacy `detail.status` (e.g. quota_exceeded) and a
# newer `detail.code` (e.g. insufficient_credits); both are matched.
QUOTA_IDENTIFIERS = {"quota_exceeded", "insufficient_credits", "character_limit_exceeded"}
RATE_LIMIT_IDENTIFIERS = {"too_many_concurrent_requests", "concurrent_limit_exceeded",
                          "rate_limit_exceeded", "system_busy"}
VOICE_IDENTIFIERS = {"voice_not_found", "invalid_voice_id", "voice_access_denied"}
# On the free plan this is almost always a Voice Library voice.
PLAN_IDENTIFIERS = {"paid_plan_required", "free_users_not_allowed", "subscription_required",
                    "feature_not_available"}
PERMISSION_IDENTIFIERS = {"missing_permissions", "insufficient_permissions",
                          "detected_unusual_activity", "model_access_denied", "forbidden"}
AUDIO_IDENTIFIERS = {"invalid_audio", "invalid_audio_format", "audio_too_long", "audio_too_short",
                     "invalid_file_type", "invalid_content"}


@dataclass
class ConversionResult:
    """Converted audio returned by a provider."""
    audio: bytes
    mime: str
    latency_ms: int


# --- ElevenLabs error parsing ----------------------------------------------------

def parse_error_body(body_text: str) -> dict:
    """Extract {status, code, message} from an ElevenLabs error body (tolerant)."""
    empty = {"status": None, "code": None, "message": None}
    if not body_text:
        return empty
    try:
        parsed = json.loads(body_text)
    except ValueError:
        return dict(empty, message=body_text[:200])
    if not isinstance(parsed, dict):
        return empty
    detail = parsed.get("detail")
    if isinstance(detail, str):
        return dict(empty, message=detail)
    if not isinstance(detail, dict):
        return empty

    def pick(key):
        value = detail.get(key)
        return value if isinstance(value, str) else None

    return {"status": pick("status"), "code": pick("code"), "message": pick("message")}


def classify_error(status: int, detail: dict) -> str:
    """Map an HTTP status + parsed detail to a provider error code."""
    identifiers = [v for v in (detail.get("code"), detail.get("status")) if v]

    def has(group):
        return any(i in group for i in identifiers)

    if has(QUOTA_IDENTIFIERS):
        return P_QUOTA
    if has(RATE_LIMIT_IDENTIFIERS):
        return P_RATE_LIMIT
    if has(VOICE_IDENTIFIERS):
        return P_VOICE_NOT_FOUND
    if has(PLAN_IDENTIFIERS):
        return P_PLAN_REQUIRED
    if has(PERMISSION_IDENTIFIERS):
        return P_PERMISSION
    if has(AUDIO_IDENTIFIERS):
        return P_INVALID_AUDIO

    if status == 401:
        return P_AUTH
    if status == 402:
        return P_QUOTA
    if status == 403:
        return P_PERMISSION
    if status == 404:
        return P_VOICE_NOT_FOUND
    if status == 429:
        return P_RATE_LIMIT
    if status in (400, 422):
        return P_INVALID_REQUEST
    if status in (408, 504):
        return P_TIMEOUT
    return P_UPSTREAM


def map_http_error(status: int, body_text: str) -> AppError:
    """Turn a non-2xx ElevenLabs response into an AppError (body never in .message)."""
    detail = parse_error_body(body_text)
    code = classify_error(status, detail)
    provider_detail = detail.get("code") or detail.get("status")
    summary = f"{status} {provider_detail}" if provider_detail else f"{status}"
    return AppError.from_provider(code, f"ElevenLabs request failed ({summary})",
                                  provider_status=status, provider_detail=provider_detail,
                                  provider_message=detail.get("message"))


def build_sts_url(voice_id: str, output_format: str, base_url: str = ELEVENLABS_API_BASE_URL) -> str:
    """URL for the speech-to-speech endpoint."""
    return (f"{base_url.rstrip('/')}/v1/speech-to-speech/{quote(voice_id, safe='')}"
            f"?output_format={quote(output_format, safe='')}")


# --- providers ------------------------------------------------------------------------

class ElevenLabsProvider:
    """ElevenLabs Speech-to-Speech (AI voice conversion)."""

    name = "elevenlabs"

    def __init__(self, settings, session=None, base_url: str = ELEVENLABS_API_BASE_URL):
        self.settings = settings
        self.base_url = base_url
        self._session = session

    def _http(self):
        if self._session is None:
            import requests
            self._session = requests.Session()
        return self._session

    def convert(self, audio_bytes: bytes, filename: str, mime: Optional[str],
                voice_id: str) -> ConversionResult:
        """Send audio to ElevenLabs and return MP3 bytes; raises AppError on failure."""
        import requests

        settings = self.settings
        url = build_sts_url(voice_id, settings.output_format, self.base_url)
        data = {"model_id": settings.model_id}
        if settings.remove_background_noise:
            data["remove_background_noise"] = "true"
        files = {"audio": (filename or "recording", audio_bytes, mime or "application/octet-stream")}
        headers = {"xi-api-key": settings.api_key or "", "Accept": "audio/mpeg"}

        started = time.perf_counter()
        try:
            response = self._http().post(url, headers=headers, data=data, files=files,
                                         timeout=settings.timeout_s)
        except requests.Timeout:
            raise AppError.from_provider(
                P_TIMEOUT, f"ElevenLabs request timed out after {int(settings.timeout_s * 1000)}ms")
        except requests.RequestException:
            raise AppError.from_provider(P_NETWORK, "Could not reach ElevenLabs")

        if not (200 <= response.status_code < 300):
            try:
                body = response.text
            except Exception:
                body = ""
            raise map_http_error(response.status_code, body)

        content_type = response.headers.get("content-type", "") or ""
        audio = response.content or b""
        if not audio:
            raise AppError.from_provider(P_UPSTREAM, "ElevenLabs returned an empty audio response",
                                         provider_status=response.status_code)
        if content_type and not content_type.startswith("audio/"):
            raise AppError.from_provider(
                P_UPSTREAM, f"ElevenLabs returned unexpected content-type {content_type}",
                provider_status=response.status_code)

        latency = int(round((time.perf_counter() - started) * 1000))
        return ConversionResult(audio=audio, mime=content_type.split(";")[0] or "audio/mpeg",
                                latency_ms=latency)

