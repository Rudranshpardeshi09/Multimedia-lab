from __future__ import annotations

from typing import Any, Dict, Optional

# --- API error codes (mirror types/api.ts) -----------------------------------
MISSING_AUDIO = "missing-audio"
INVALID_VOICE = "invalid-voice"
VOICE_NOT_CONFIGURED = "voice-not-configured"
FILE_TOO_LARGE = "file-too-large"
UNSUPPORTED_FORMAT = "unsupported-format"
INVALID_AUDIO = "invalid-audio"
AUDIO_TOO_LONG = "audio-too-long"
QUOTA_EXHAUSTED = "quota-exhausted"
RATE_LIMITED = "rate-limited"
PROVIDER_NOT_CONFIGURED = "provider-not-configured"
PROVIDER_AUTH = "provider-auth"
PROVIDER_VOICE_MISSING = "provider-voice-missing"
PROVIDER_PERMISSION = "provider-permission"
PROVIDER_PLAN_REQUIRED = "provider-plan-required"
PROVIDER_ERROR = "provider-error"
PROVIDER_TIMEOUT = "provider-timeout"
INTERNAL = "internal"

# --- Provider-neutral failure codes (mirror lib/elevenlabs/types.ts) ---------
P_AUTH = "auth"
P_PERMISSION = "permission"
P_PLAN_REQUIRED = "plan-required"
P_QUOTA = "quota"
P_RATE_LIMIT = "rate-limit"
P_VOICE_NOT_FOUND = "voice-not-found"
P_INVALID_AUDIO = "invalid-audio"
P_INVALID_REQUEST = "invalid-request"
P_TIMEOUT = "timeout"
P_NETWORK = "network"
P_UPSTREAM = "upstream"

PLAN_REQUIRED_MESSAGE = (
    "ElevenLabs says this request needs a paid plan. On the free plan that almost always "
    "means the configured target voice is a Voice Library voice, which free accounts can't "
    "use through the API. Configure a voice you created with Voice Design, or one of "
    "ElevenLabs' current built-in default voices, and restart."
)

QUOTA_EXHAUSTED_MESSAGE = (
    "Demo usage limit reached. The free AI processing quota has been exhausted. "
    "Please try again after the quota resets."
)

GENERIC_INTERNAL_MESSAGE = "Something went wrong on our side. Please try again."

# provider code -> (HTTP status, API code, human message)
PROVIDER_ERROR_MAP = {
    P_QUOTA: (429, QUOTA_EXHAUSTED, QUOTA_EXHAUSTED_MESSAGE),
    P_RATE_LIMIT: (429, RATE_LIMITED,
                   "The voice service is busy right now. Wait a few seconds and try again."),
    P_AUTH: (500, PROVIDER_AUTH,
             "The voice service rejected this application's credentials. "
             "The server's ELEVENLABS_API_KEY needs to be checked."),
    P_PLAN_REQUIRED: (500, PROVIDER_PLAN_REQUIRED, PLAN_REQUIRED_MESSAGE),
    P_PERMISSION: (500, PROVIDER_PERMISSION,
                   "The voice service refused this request for the current account or plan. "
                   "The server configuration needs to be checked."),
    P_VOICE_NOT_FOUND: (500, PROVIDER_VOICE_MISSING,
                        "The selected target voice is not available at the voice service. "
                        "The configured voice ID needs to be checked."),
    P_INVALID_AUDIO: (422, INVALID_AUDIO,
                      "The voice service could not process this audio. "
                      "Try a clearer recording or a different file format."),
    P_INVALID_REQUEST: (502, PROVIDER_ERROR,
                        "The voice service rejected the request. "
                        "Please try again with a different recording."),
    P_TIMEOUT: (504, PROVIDER_TIMEOUT,
                "The voice service took too long to respond. "
                "Please try again, ideally with a shorter recording."),
    P_NETWORK: (502, PROVIDER_ERROR,
                "We couldn't reach the voice service. Please try again in a moment."),
    P_UPSTREAM: (502, PROVIDER_ERROR,
                 "The voice service returned an unexpected response. Please try again in a moment."),
}


class AppError(Exception):
    """A user-facing failure with an HTTP status, a stable code and a safe message."""

    def __init__(self, status: int, code: str, message: str,
                 detail: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.detail = dict(detail or {})

    def __repr__(self) -> str:
        return f"AppError(status={self.status}, code={self.code!r})"

    @classmethod
    def from_provider(cls, provider_code: str, log_message: str = "",
                      provider_status: Optional[int] = None,
                      provider_detail: Optional[str] = None,
                      provider_message: Optional[str] = None) -> "AppError":
        """Build the user-facing error for a provider failure code."""
        status, code, message = PROVIDER_ERROR_MAP.get(provider_code, PROVIDER_ERROR_MAP[P_UPSTREAM])
        detail = {
            "provider_code": provider_code,
            "provider_status": provider_status,
            "provider_detail": provider_detail,
            "provider_message": (provider_message or "")[:200] or None,
            "log_message": log_message or None,
        }
        return cls(status, code, message, detail)
