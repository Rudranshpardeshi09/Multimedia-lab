"""
Task 04: Voice Transformer - audio validation & FFmpeg helpers
Multimedia Systems Laboratory
Author: Rudranshpardeshi09

Port of lib/audio/{constants,validation,format,server-metadata}.ts. The real
container is identified from magic bytes and the duration is measured with
FFprobe before any provider is contacted.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Optional, Union

from .config import SERVER_DURATION_TOLERANCE_SECONDS, TASK_DIR
from .errors import (AppError, AUDIO_TOO_LONG, FILE_TOO_LARGE, INTERNAL, INVALID_AUDIO,
                     MISSING_AUDIO, UNSUPPORTED_FORMAT)

REPO_ROOT = TASK_DIR.parent
PORTABLE_FFMPEG_DIR = REPO_ROOT / "tools" / "ffmpeg" / "bin"

SUPPORTED_FORMATS = [
    {"extension": "mp3", "label": "MP3", "mime_types": ["audio/mpeg", "audio/mp3", "audio/mpeg3"]},
    {"extension": "wav", "label": "WAV", "mime_types": ["audio/wav", "audio/x-wav", "audio/wave", "audio/vnd.wave"]},
    {"extension": "m4a", "label": "M4A", "mime_types": ["audio/mp4", "audio/x-m4a", "audio/m4a", "audio/aac"]},
    {"extension": "ogg", "label": "OGG", "mime_types": ["audio/ogg", "application/ogg"]},
    {"extension": "oga", "label": "OGA", "mime_types": ["audio/ogg"]},
    {"extension": "flac", "label": "FLAC", "mime_types": ["audio/flac", "audio/x-flac"]},
    {"extension": "webm", "label": "WebM", "mime_types": ["audio/webm", "video/webm"]},
]

SUPPORTED_FORMAT_LABELS = list(dict.fromkeys(f["label"] for f in SUPPORTED_FORMATS))

UNSUPPORTED_FORMAT_MESSAGE = (
    "This audio format is not supported. Please use " + ", ".join(SUPPORTED_FORMAT_LABELS) + "."
)
UNREADABLE_AUDIO_MESSAGE = (
    "We couldn't read this audio file. Make sure it is a valid MP3, WAV, M4A, OGG, FLAC or WebM recording."
)
NO_DURATION_MESSAGE = (
    "We couldn't determine how long this audio is. Try exporting it as MP3 or WAV and upload it again."
)
EMPTY_FILE_MESSAGE = "This file is empty. Please choose a recording that contains audio."


@dataclass
class AudioInfo:
    """Facts about a validated upload."""
    format: str
    size: int
    duration_s: float
    mime: str


# --- small helpers ------------------------------------------------------------

def find_tool(name: str) -> Optional[str]:
    """Locate ffmpeg/ffprobe on PATH, else in the repo's portable tools/ffmpeg/bin."""
    found = shutil.which(name)
    if found:
        return found
    for candidate in (PORTABLE_FFMPEG_DIR / (name + ".exe"), PORTABLE_FFMPEG_DIR / name):
        if candidate.is_file():
            return str(candidate)
    return None


def normalize_mime(mime: Optional[str]) -> str:
    """Strip parameters (e.g. ;codecs=opus) and lower-case a MIME type."""
    return (mime or "").split(";")[0].strip().lower()


def get_extension(name: Optional[str]) -> str:
    """Lower-cased file extension without the dot, or ''."""
    trimmed = (name or "").strip()
    dot = trimmed.rfind(".")
    if dot == -1 or dot == len(trimmed) - 1:
        return ""
    return trimmed[dot + 1:].lower()


def is_supported_audio(filename: Optional[str], mime: Optional[str]) -> bool:
    """Extension OR declared MIME type must match a supported format."""
    ext = get_extension(filename)
    m = normalize_mime(mime)
    return any(f["extension"] == ext or m in f["mime_types"] for f in SUPPORTED_FORMATS)


def mime_for_format(fmt: str) -> str:
    """Canonical MIME type for a format extension."""
    for f in SUPPORTED_FORMATS:
        if f["extension"] == fmt:
            return f["mime_types"][0]
    return "application/octet-stream"


def _round_half_up(value: float, digits: int = 0) -> float:
    factor = 10 ** digits
    return math.floor(value * factor + 0.5) / factor


def _fmt_number(value: float) -> str:
    """Print 15.0 as '15' and 12.3 as '12.3' (JS Number formatting)."""
    return str(int(value)) if float(value).is_integer() else f"{value:.1f}"


def format_bytes(size: int) -> str:
    """512 B / 2 KB / 15.0 MB."""
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.0f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def format_duration_human(seconds: float) -> str:
    """'1 second', '12.3 seconds', '1 min 15 sec'."""
    if seconds is None or not math.isfinite(seconds) or seconds < 0:
        return "an unknown length"
    if seconds < 60:
        rounded = _round_half_up(seconds, 1)
        return f"{_fmt_number(rounded)} second{'' if rounded == 1 else 's'}"
    minutes = int(seconds // 60)
    rest = int(_round_half_up(seconds % 60))
    return f"{minutes} min {rest} sec"


# --- format detection -----------------------------------------------------------

def detect_format(filename: Optional[str], mime: Optional[str], head_bytes: bytes) -> Optional[str]:
    """Identify the real container from magic bytes; returns an extension or None."""
    head = bytes(head_bytes[:64])
    declared_ext = get_extension(filename)
    if len(head) < 4:
        return None
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "wav"
    if head[:4] == b"fLaC":
        return "flac"
    if head[:4] == b"OggS":
        return "oga" if declared_ext == "oga" else "ogg"
    if head[:4] == b"\x1a\x45\xdf\xa3":
        return "webm"
    if head[4:8] == b"ftyp":
        return "m4a"
    if head[:3] == b"ID3":
        return "mp3"
    # MPEG audio frame sync: 11 set bits, layer bits non-zero (excludes ADTS AAC).
    if head[0] == 0xFF and (head[1] & 0xE0) == 0xE0 and (head[1] & 0x06) != 0:
        return "mp3"
    return None


# --- FFprobe / FFmpeg -------------------------------------------------------------

class ProbeFailure(Exception):
    """FFprobe could not read the file. `reason` is 'unparseable' or 'no-duration'."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _require_tool(name: str) -> str:
    path = find_tool(name)
    if not path:
        raise AppError(500, INTERNAL,
                       f"{name} is not installed on this machine. Install FFmpeg "
                       f"(winget install Gyan.FFmpeg) or place it in tools/ffmpeg/bin.")
    return path


def _probe_file(path: str) -> float:
    ffprobe = _require_tool("ffprobe")
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration,format_name",
         "-of", "json", path],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    if result.returncode != 0:
        raise ProbeFailure("unparseable")
    try:
        fmt = json.loads(result.stdout or "{}").get("format", {})
    except ValueError:
        raise ProbeFailure("unparseable")
    if not fmt.get("format_name"):
        raise ProbeFailure("unparseable")

    try:
        duration = float(fmt.get("duration"))
    except (TypeError, ValueError):
        duration = float("nan")

    if not math.isfinite(duration) or duration <= 0:
        # Live-mode WebM (e.g. browser MediaRecorder) has no duration header:
        # scan the packets and take the end of the last one.
        packets = subprocess.run(
            [ffprobe, "-v", "error", "-select_streams", "a:0",
             "-show_entries", "packet=pts_time,duration_time", "-of", "csv=p=0", path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        end = 0.0
        for line in (packets.stdout or "").splitlines():
            parts = line.split(",")
            try:
                pts = float(parts[0])
                dur = float(parts[1]) if len(parts) > 1 and parts[1] else 0.0
            except (ValueError, IndexError):
                continue
            end = max(end, pts + dur)
        duration = end

    if not math.isfinite(duration) or duration <= 0:
        raise ProbeFailure("no-duration")
    return duration


def probe_duration(path_or_bytes: Union[str, os.PathLike, bytes, bytearray],
                   suffix: str = ".bin") -> float:
    """Measure duration in seconds with FFprobe (bytes go through a temp file).

    Raises ProbeFailure('unparseable' | 'no-duration') or AppError if FFprobe is missing.
    """
    if isinstance(path_or_bytes, (bytes, bytearray)):
        fd, tmp = tempfile.mkstemp(suffix=suffix, prefix="vt-probe-")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(path_or_bytes)
            return _probe_file(tmp)
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass
    return _probe_file(str(path_or_bytes))


def trim_audio(path: Union[str, os.PathLike], seconds: float) -> bytes:
    """Return the first `seconds` of a file re-encoded as MP3 (via FFmpeg)."""
    if seconds <= 0:
        raise ValueError("trim length must be positive")
    ffmpeg = _require_tool("ffmpeg")
    result = subprocess.run(
        [ffmpeg, "-v", "error", "-i", str(path), "-t", f"{seconds:g}", "-vn",
         "-c:a", "libmp3lame", "-b:a", "128k", "-f", "mp3", "pipe:1"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if result.returncode != 0 or not result.stdout:
        message = result.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(f"FFmpeg could not trim the audio: {message[:300]}")
    return result.stdout


# --- validation ---------------------------------------------------------------------

def file_too_large_error(limit_bytes: int) -> AppError:
    """413 with the limit in MB (one decimal, JS-style)."""
    limit_mb = _round_half_up(limit_bytes / (1024 * 1024), 1)
    return AppError(413, FILE_TOO_LARGE, f"This file is too large. The maximum is {_fmt_number(limit_mb)} MB.")


def duration_error(duration_s: float, max_duration_s: float) -> AppError:
    """422 audio-too-long with the measured length in the message."""
    return AppError(422, AUDIO_TOO_LONG,
                    f"This recording is {format_duration_human(duration_s)} long. "
                    f"The MVP currently supports up to {_fmt_number(max_duration_s)} seconds.")


def check_duration(duration_s: float, max_duration_s: float,
                   tolerance_s: float = SERVER_DURATION_TOLERANCE_SECONDS) -> None:
    """Raise AppError unless 0 < duration <= max + tolerance."""
    if duration_s is None or not math.isfinite(duration_s) or duration_s <= 0:
        raise AppError(422, INVALID_AUDIO, NO_DURATION_MESSAGE)
    if duration_s > max_duration_s + tolerance_s:
        raise duration_error(duration_s, max_duration_s)


def validate_audio(data: bytes, filename: Optional[str], mime: Optional[str], settings) -> AudioInfo:
    """Validate size -> declared format -> real container -> duration. Raises AppError."""
    size = len(data or b"")
    if size <= 0:
        raise AppError(400, MISSING_AUDIO, EMPTY_FILE_MESSAGE)
    if size > settings.max_size_bytes:
        raise file_too_large_error(settings.max_size_bytes)

    declared_mime = normalize_mime(mime)
    if not is_supported_audio(filename, declared_mime):
        raise AppError(415, UNSUPPORTED_FORMAT, UNSUPPORTED_FORMAT_MESSAGE)

    fmt = detect_format(filename, declared_mime, data[:64])
    if fmt is None:
        raise AppError(415, UNSUPPORTED_FORMAT, UNREADABLE_AUDIO_MESSAGE)

    try:
        duration = probe_duration(data, suffix="." + fmt)
    except ProbeFailure as failure:
        if failure.reason == "no-duration":
            raise AppError(422, INVALID_AUDIO, NO_DURATION_MESSAGE)
        raise AppError(415, UNSUPPORTED_FORMAT, UNREADABLE_AUDIO_MESSAGE)

    check_duration(duration, settings.max_duration_s)
    known = any(declared_mime in f["mime_types"] for f in SUPPORTED_FORMATS)
    return AudioInfo(format=fmt, size=size, duration_s=round(duration, 2),
                     mime=declared_mime if known else mime_for_format(fmt))
