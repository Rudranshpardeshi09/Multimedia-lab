"""
Task 04: AI Speech-to-Speech Voice Transformer
Multimedia Systems Laboratory
Author: Rudranshpardeshi09

Converts a short recording (<= 30 s, <= 15 MB; MP3/WAV/M4A/OGG/OGA/FLAC/WebM)
into one of three allowlisted target voices using the ElevenLabs
Speech-to-Speech API.
"""

import os
import sys
import shutil
import argparse
import mimetypes
from pathlib import Path

TASK_DIR = Path(__file__).resolve().parent
if str(TASK_DIR) not in sys.path:
    sys.path.insert(0, str(TASK_DIR))

from vt.audio import format_bytes, trim_audio  # noqa: E402
from vt.config import load_settings  # noqa: E402
from vt.errors import AUDIO_TOO_LONG, AppError  # noqa: E402
from vt.service import convert  # noqa: E402
from vt.voices import VOICE_DEFINITIONS, list_configured_voices, read_voice_id  # noqa: E402

REPO_ROOT = TASK_DIR.parent
DEFAULT_INPUT = REPO_ROOT / "datasets" / "audio" / "Afternoon_Window.mp3"
OUTPUT_DIR = TASK_DIR / "outputs"

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_NOT_CONFIGURED = 2


def print_header(title: str):
    """Print a section banner."""
    print("\n" + "=" * 65)
    print(f" {title}")
    print("=" * 65)


def print_tag(label: str, value):
    """Print a labelled value aligned like the other lab tasks."""
    print(f"  {label:<24}: {value}")


def ensure_ffmpeg_on_path():
    """Add the portable tools/ffmpeg/bin to PATH if FFmpeg is not already there."""
    portable = REPO_ROOT / "tools" / "ffmpeg" / "bin"
    if shutil.which("ffprobe") is None and portable.is_dir():
        os.environ["PATH"] = str(portable) + os.pathsep + os.environ.get("PATH", "")


def print_setup_checklist(settings, configured_voices):
    """Explain what is missing from the ElevenLabs configuration."""
    print_header("Setup required - finish the ElevenLabs configuration")
    env_path = TASK_DIR / ".env"
    print(f"  Add the values below to {env_path}")
    print("  (copy .env.example to .env), then run again.\n")
    key_state = "configured" if settings.is_configured else "MISSING"
    mark = "[x]" if settings.is_configured else "[ ]"
    print(f"  {mark} ELEVENLABS_API_KEY - a dedicated ElevenLabs API key ({key_state})")
    voices_ok = bool(configured_voices)
    mark = "[x]" if voices_ok else "[ ]"
    print(f"  {mark} At least one target voice ID ({'configured' if voices_ok else 'none configured'}):")
    for voice in VOICE_DEFINITIONS:
        state = "set" if read_voice_id(voice, settings.env) else "not set"
        print(f"        {voice['env_var']:<28} - {voice['name']} ({state})")
    print("\n  Create the voices with ElevenLabs Voice Design (free plan) or use a current")
    print("  built-in default voice and copy their voice IDs.")


def cmd_list_voices(settings):
    """Print the voice allowlist and which voices are usable."""
    print_header("Target Voices")
    configured = {v["slug"] for v in list_configured_voices(settings.env)}
    for voice in VOICE_DEFINITIONS:
        state = "configured" if voice["slug"] in configured else f"not configured ({voice['env_var']})"
        print(f"  {voice['slug']:<24} {voice['name']:<24} {state}")
        print(f"  {'':<24} {voice['description']}")
    if not configured:
        print("\n  No ElevenLabs voices configured.")
    return EXIT_OK


def cmd_convert(args, settings):
    """Run one conversion through the shared service pipeline."""
    configured = list_configured_voices(settings.env)

    if not settings.is_configured or not configured:
        print_setup_checklist(settings, configured)
        return EXIT_NOT_CONFIGURED

    slug = args.voice or configured[0]["slug"]

    source = Path(args.file).expanduser()
    if not source.is_absolute() and not source.exists():
        source = REPO_ROOT / args.file
    if not source.is_file():
        print(f"[Error] Input file not found: {args.file}")
        return EXIT_FAILED

    print_header("Task 04: AI Speech-to-Speech Voice Transformer")
    print_tag("Input File", source)
    print_tag("Target Voice", slug)
    print_tag("Provider", f"ElevenLabs Speech-to-Speech ({settings.model_id})")

    if args.trim is not None:
        if args.trim <= 0:
            print("[Error] --trim must be a positive number of seconds.")
            return EXIT_FAILED
        try:
            data = trim_audio(source, args.trim)
        except (AppError, RuntimeError) as error:
            print(f"[Error] {getattr(error, 'message', error)}")
            return EXIT_FAILED
        filename, mime = source.stem + ".mp3", "audio/mpeg"
        print_tag("Trimmed To", f"first {args.trim:g} s (re-encoded as MP3)")
    else:
        data = source.read_bytes()
        filename = source.name
        mime = mimetypes.guess_type(source.name)[0]

    try:
        result = convert(data, filename, mime, slug, settings=settings)
    except AppError as error:
        print_header("Conversion Rejected")
        print_tag("Error Code", f"{error.code} (HTTP {error.status})")
        print_tag("Message", error.message)
        if error.code == AUDIO_TOO_LONG:
            print(f"\n  Tip: re-run with --trim {int(settings.max_duration_s)} to convert only the "
                  f"first {int(settings.max_duration_s)} seconds.")
        return EXIT_FAILED

    out = Path(args.out) if args.out else OUTPUT_DIR / f"{Path(filename).stem}-{slug}.mp3"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(result["audio"])

    print_header("Conversion Result")
    print_tag("Voice", f"{result['voice']['name']} ({result['voice']['slug']})")
    print_tag("Provider", result["provider"])
    print_tag("Source Format", result["source"]["format"].upper())
    print_tag("Source Size", format_bytes(result["source"]["size"]))
    print_tag("Source Duration", f"{result['source']['duration_s']:.2f} s")
    print_tag("Provider Time", f"{result['timing']['provider_ms']} ms")
    print_tag("Total Time", f"{result['timing']['server_ms']} ms")
    print_tag("Output Size", format_bytes(len(result["audio"])))
    print_tag("Output File", out)
    return EXIT_OK


def cmd_serve(args):
    """Start the Flask web UI from vt.server."""
    try:
        from vt.server import create_app
    except ImportError as error:
        print(f"[Error] Web server unavailable: {error}. Install Flask: pip install flask")
        return EXIT_FAILED
    app = create_app()
    print(f"Voice Transformer web UI on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port)
    return EXIT_OK


def build_parser():
    """Command-line interface definition."""
    parser = argparse.ArgumentParser(
        description="Task 04: AI Speech-to-Speech Voice Transformer (Rudranshpardeshi09)"
    )
    parser.add_argument("--file", default=str(DEFAULT_INPUT),
                        help="Input audio file (default: datasets/audio/Afternoon_Window.mp3)")
    parser.add_argument("--voice", help="Target voice slug (default: first configured voice)")
    parser.add_argument("--out", help="Output MP3 path (default: outputs/<stem>-<voice>.mp3)")
    parser.add_argument("--trim", type=float, metavar="SECONDS",
                        help="Convert only the first N seconds (via FFmpeg)")
    parser.add_argument("--list-voices", action="store_true", help="List target voices and exit")
    parser.add_argument("--serve", action="store_true", help="Start the web UI")
    parser.add_argument("--host", default="127.0.0.1", help="Web UI host (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000, help="Web UI port (default 5000)")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    ensure_ffmpeg_on_path()
    settings = load_settings()

    if args.serve:
        return cmd_serve(args)
    if args.list_voices:
        return cmd_list_voices(settings)
    return cmd_convert(args, settings)


if __name__ == "__main__":
    sys.exit(main())
