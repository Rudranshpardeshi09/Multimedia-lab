"""
Task 04: Voice Transformer — Web Server
Multimedia Systems Laboratory
Author: Rudranshpardeshi09

Flask application that serves the single-page web UI from ``web/`` and
exposes two JSON/audio endpoints:

    GET  /api/config   -> public configuration (voices, limits, formats)
    POST /api/convert  -> multipart upload in, MP3 bytes out

Audio is handled entirely in memory: nothing is written to disk and no
request data is logged. Error responses always use the shape
``{"error": {"code": str, "message": str}}`` and never include internals.
"""

import logging
import os
import time
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from vt.audio import SUPPORTED_FORMATS
from vt.config import load_settings
from vt.errors import AppError
from vt.service import convert
from vt.voices import list_configured_voices

TASK_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = TASK_DIR / "web"

# Multipart framing and the voiceSlug field add a little on top of
# the audio file itself; allow that much before Flask rejects the body.
UPLOAD_MARGIN_BYTES = 1024 * 1024

logger = logging.getLogger("vt.server")


def error_response(code: str, message: str, status: int):
    """Build the standard JSON error response."""
    response = jsonify({"error": {"code": code, "message": message}})
    response.status_code = status
    response.headers["Cache-Control"] = "no-store"
    return response


def _too_large_message(max_size_mb) -> str:
    return (
        "This file is too large for the server to accept (maximum {} MB). "
        "Try a shorter recording or a compressed format such as MP3.".format(format(float(max_size_mb), "g"))
    )


def create_app() -> Flask:
    """Create the Flask application serving the UI and the conversion API."""
    settings = load_settings()

    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = int(float(settings.max_size_mb) * 1024 * 1024) + UPLOAD_MARGIN_BYTES

    # ------------------------------------------------------------------ pages

    @app.get("/")
    def index():
        response = send_from_directory(str(WEB_DIR), "index.html")
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/<path:filename>")
    def static_files(filename):
        # Only serve the front-end assets; send_from_directory guards traversal.
        if filename.startswith("api/"):
            return error_response("not-found", "This endpoint does not exist.", 404)
        response = send_from_directory(str(WEB_DIR), filename)
        response.headers["Cache-Control"] = "no-cache"
        return response

    # -------------------------------------------------------------------- api

    @app.get("/api/config")
    def api_config():
        # Re-read per request so edited environment variables never serve a
        # stale voice list (mirrors the original force-dynamic page).
        current = load_settings()
        voices = list_configured_voices()
        body = {
            "configured": bool(current.is_configured),
            "provider_configured": bool(current.api_key),
            "voices": [
                {"slug": v["slug"], "name": v["name"], "description": v.get("description", "")}
                for v in voices
            ],
            "limits": {
                "max_duration_s": current.max_duration_s,
                "max_size_mb": current.max_size_mb,
            },
            "formats": [
                {
                    "extension": f["extension"],
                    "label": f["label"],
                    "mime_types": list(f["mime_types"]),
                }
                for f in SUPPORTED_FORMATS
            ],
        }
        response = jsonify(body)
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.post("/api/convert")
    def api_convert():
        started = time.perf_counter()
        current = load_settings()

        upload = request.files.get("audio")
        if upload is None:
            return error_response("missing-audio", "No audio was received. Record or choose a file and try again.", 400)

        voice_slug = (request.form.get("voiceSlug") or "").strip()
        if not voice_slug:
            return error_response("invalid-voice", "Choose a target voice and try again.", 400)

        data = upload.read()
        filename = upload.filename or "audio"
        mime = upload.mimetype or None

        result = convert(data, filename, mime, voice_slug, settings=current)

        timing = result.get("timing") or {}
        source = result.get("source") or {}
        server_ms = timing.get("server_ms")
        if server_ms is None:
            server_ms = round((time.perf_counter() - started) * 1000)

        response = app.response_class(result["audio"], mimetype=result.get("mime") or "audio/mpeg")
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Server-Ms"] = str(int(round(server_ms)))
        if timing.get("provider_ms") is not None:
            response.headers["X-Provider-Ms"] = str(int(round(timing["provider_ms"])))
        if source.get("duration_s") is not None:
            response.headers["X-Source-Duration"] = "{:.2f}".format(float(source["duration_s"]))
        response.headers["Access-Control-Expose-Headers"] = "X-Server-Ms, X-Provider-Ms, X-Source-Duration"
        return response

    # ----------------------------------------------------------------- errors

    @app.errorhandler(AppError)
    def handle_app_error(error):
        return error_response(error.code, error.message, int(getattr(error, "status", 400) or 400))

    @app.errorhandler(RequestEntityTooLarge)
    def handle_too_large(_error):
        return error_response("file-too-large", _too_large_message(settings.max_size_mb), 413)

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        if request.path.startswith("/api/"):
            messages = {
                404: "This endpoint does not exist.",
                405: "This method is not allowed for this endpoint.",
            }
            message = messages.get(error.code, "The request could not be processed.")
            return error_response("http-{}".format(error.code), message, error.code or 400)
        return error

    @app.errorhandler(Exception)
    def handle_unexpected(error):
        # Log the type only: the message could echo request data.
        logger.error("Unhandled %s on %s", type(error).__name__, request.path)
        return error_response("unexpected", "Something went wrong on the server. Please try again.", 500)

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "microphone=(self)")
        return response

    return app


if __name__ == "__main__":  # pragma: no cover - convenience for local runs
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")))
