"""
Task 04: Voice Transformer - target voice allowlist
Multimedia Systems Laboratory
Author: Rudranshpardeshi09

Port of lib/voices/config.ts. Clients only ever see slugs; voice IDs stay in
environment variables so the API key can never be pointed at an arbitrary voice.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, Optional, Tuple

from .errors import AppError, INVALID_VOICE, VOICE_NOT_CONFIGURED

VOICE_DEFINITIONS = [
    {
        "slug": "warm-narrator",
        "name": "Warm Narrator",
        "description": "Natural, calm and expressive.",
        "env_var": "ELEVENLABS_VOICE_WARM_ID",
    },
    {
        "slug": "deep-studio",
        "name": "Deep Studio",
        "description": "Lower, cinematic delivery.",
        "env_var": "ELEVENLABS_VOICE_DEEP_ID",
    },
    {
        "slug": "bright-conversational",
        "name": "Bright Conversational",
        "description": "Friendly, energetic tone.",
        "env_var": "ELEVENLABS_VOICE_BRIGHT_ID",
    },
]

VOICE_SLUGS = [v["slug"] for v in VOICE_DEFINITIONS]

VOICE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def _default_env() -> Dict[str, str]:
    from .config import load_env
    return load_env()


def is_voice_slug(value: Any) -> bool:
    """True only for one of the allowlisted slugs."""
    return isinstance(value, str) and value in VOICE_SLUGS


def get_voice_definition(slug: str) -> Optional[dict]:
    """Return the definition for a slug, or None."""
    for definition in VOICE_DEFINITIONS:
        if definition["slug"] == slug:
            return definition
    return None


def read_voice_id(definition: dict, env: Mapping[str, str]) -> Optional[str]:
    """Return the trimmed, well-formed voice ID for a definition, or None."""
    raw = (env.get(definition["env_var"]) or "").strip()
    if not raw or not VOICE_ID_PATTERN.match(raw):
        return None
    return raw


def public_voice(definition: dict) -> dict:
    """The client-safe view of a voice: slug, name, description."""
    return {k: definition[k] for k in ("slug", "name", "description")}


def list_configured_voices(env: Optional[Mapping[str, str]] = None) -> List[dict]:
    """List voices that have a valid ID configured, in declared order, without IDs."""
    source = _default_env() if env is None else env
    return [public_voice(d) for d in VOICE_DEFINITIONS if read_voice_id(d, source) is not None]


def resolve_voice(slug: Any, env: Optional[Mapping[str, str]] = None) -> Tuple[dict, str]:
    """Resolve a slug to (definition, voice_id) or raise AppError (invalid / not configured)."""
    source = _default_env() if env is None else env
    if not is_voice_slug(slug):
        raise AppError(400, INVALID_VOICE,
                       "That target voice is not available. Please choose a voice from the list.")
    definition = get_voice_definition(slug)
    voice_id = read_voice_id(definition, source)
    if not voice_id:
        raise AppError(400, VOICE_NOT_CONFIGURED,
                       "That target voice is not configured on this server. Please choose another voice.")
    return definition, voice_id
