"""
Task 03: Audio Stream & Metadata Analyzer
Multimedia Systems Laboratory
Author: Rudranshpardeshi09
"""

import os
import sys
import json
import shutil
import argparse
import subprocess
from pathlib import Path


def format_file_size(size_in_bytes: int) -> str:
    """Convert bytes into readable file size units."""
    size = float(size_in_bytes)
    units = ["Bytes", "KB", "MB", "GB", "TB"]

    for unit in units:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024

    return f"{size:.2f} PB"


def format_duration(seconds) -> str:
    """Convert duration in seconds to HH:MM:SS.mmm format."""
    try:
        sec = float(seconds)
        hours = int(sec // 3600)
        minutes = int((sec % 3600) // 60)
        remaining_secs = sec % 60
        return f"{hours:02d}:{minutes:02d}:{remaining_secs:06.3f}"
    except (ValueError, TypeError):
        return "Not Available"


def check_ffprobe() -> bool:
    """Check whether FFprobe is installed and available on PATH."""
    return shutil.which("ffprobe") is not None


def get_audio_metadata(audio_path: str) -> dict:
    """Extract audio container and stream metadata using FFprobe."""
    command = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        "-count_packets",
        audio_path
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr or "FFprobe exited with an error.")

    return json.loads(result.stdout)


def get_audio_stream(streams: list) -> dict:
    """Find and return the primary audio stream."""
    for stream in streams:
        if stream.get("codec_type") == "audio":
            return stream
    return {}


def print_tag(label: str, value):
    """Print key-value pair formatted with alignment."""
    if value is None or str(value).strip() == "":
        value = "Not Available"
    print(f"{label:<22}: {value}")


def print_tags(tags: dict):
    """Print all available metadata tags."""
    if not tags:
        print("No additional tags available.")
        return

    for key, value in tags.items():
        print(f"{key:<22}: {value}")


def analyze_audio(audio_path: str) -> bool:
    """Analyze an audio file and generate comprehensive metadata report."""
    resolved_path = Path(audio_path).resolve()

    if not resolved_path.exists():
        print(f"\n[Error] Audio file not found: {resolved_path}")
        return False

    if not resolved_path.is_file():
        print(f"\n[Error] Provided path is not a file: {resolved_path}")
        return False

    if not check_ffprobe():
        print("\n[Notice] 'ffprobe' is required for complete stream analysis.")
        print("To install FFmpeg/FFprobe:")
        print(" - Windows: winget install Gyan.FFmpeg")
        print(" - macOS  : brew install ffmpeg")
        print(" - Linux  : sudo apt install ffmpeg")
        
        # Display basic file info fallback
        file_size = resolved_path.stat().st_size
        print("\n" + "=" * 50)
        print("   BASIC AUDIO FILE INFORMATION (FALLBACK)   ")
        print("=" * 50)
        print_tag("File Name", resolved_path.name)
        print_tag("File Extension", resolved_path.suffix.upper())
        print_tag("File Size", format_file_size(file_size))
        print_tag("Full Path", str(resolved_path))
        print("=" * 50)
        return False

    try:
        metadata = get_audio_metadata(str(resolved_path))
        file_size = resolved_path.stat().st_size

        format_data = metadata.get("format", {})
        streams = metadata.get("streams", [])
        audio_stream = get_audio_stream(streams)

        print("\n" + "=" * 55)
        print("     TASK 03: AUDIO METADATA & ANALYSIS REPORT    ")
        print("=" * 55)

        # Basic File Information
        print("\n[Basic File Information]")
        print("-" * 45)
        print_tag("File Name", resolved_path.name)
        print_tag("File Extension", resolved_path.suffix.upper())
        print_tag("File Size", format_file_size(file_size))

        # Format Information
        print("\n[Container & Format Properties]")
        print("-" * 45)
        print_tag("Format Long Name", format_data.get("format_long_name"))
        print_tag("Format Identifier", format_data.get("format_name"))
        print_tag("Duration", format_duration(format_data.get("duration")))
        bit_rate = format_data.get("bit_rate")
        print_tag(
            "Overall Bitrate",
            f"{int(bit_rate) / 1000:.2f} kbps" if bit_rate else "Not Available"
        )
        print_tag("Start Time", format_data.get("start_time", "0.000000"))

        # Audio Stream Properties
        print("\n[Audio Stream Properties]")
        print("-" * 45)
        if audio_stream:
            print_tag("Codec", audio_stream.get("codec_long_name"))
            print_tag("Codec Name", audio_stream.get("codec_name"))
            sr = audio_stream.get("sample_rate")
            print_tag("Sample Rate", f"{sr} Hz" if sr else "Not Available")
            print_tag("Channels", audio_stream.get("channels"))
            print_tag("Channel Layout", audio_stream.get("channel_layout"))
            print_tag("Sample Format", audio_stream.get("sample_fmt"))
            s_br = audio_stream.get("bit_rate")
            if s_br:
                print_tag("Stream Bitrate", f"{int(s_br) / 1000:.2f} kbps")
            elif bit_rate:
                print_tag("Stream Bitrate", f"~{int(bit_rate) / 1000:.2f} kbps (estimated from file size)")
            else:
                print_tag("Stream Bitrate", "Not Available")

            bits = audio_stream.get("bits_per_sample") or audio_stream.get("bits_per_raw_sample")
            if bits and str(bits) not in ("0", "N/A"):
                print_tag("Bits Per Sample", f"{bits} bit")
            else:
                print_tag("Bits Per Sample", "N/A (compressed format, no fixed bit depth)")

            frames = audio_stream.get("nb_frames") or audio_stream.get("nb_read_packets")
            duration = format_data.get("duration")
            if frames and duration:
                frame_ms = float(duration) / int(frames) * 1000
                print_tag("Frame Count", f"{frames} (~{frame_ms:.0f} ms per frame)")
            else:
                print_tag("Frame Count", frames)
        else:
            print("No audio stream detected in container.")

        # Tags
        format_tags = format_data.get("tags", {})
        if format_tags:
            print("\n[Audio Metadata / ID3 Tags]")
            print("-" * 45)
            print_tags(format_tags)

        print("\n" + "=" * 55)
        print("                 REPORT COMPLETED                 ")
        print("=" * 55)
        return True

    except Exception as error:
        print(f"\n[Error] While processing audio: {error}")
        return False


def find_default_sample() -> str:
    """Use the first audio file in this task's input/ folder, else the dataset sample."""
    input_dir = Path(__file__).resolve().parent / "input"
    if input_dir.is_dir():
        files = sorted(f for f in input_dir.iterdir()
                       if f.suffix.lower() in {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".opus", ".wma"})
        if files:
            return str(files[0])

    candidates = [
        Path(__file__).resolve().parent.parent / "datasets" / "audio" / "Afternoon_Window.mp3",
        Path("datasets/audio/Afternoon_Window.mp3"),
        Path("../datasets/audio/Afternoon_Window.mp3"),
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return ""


def main():
    parser = argparse.ArgumentParser(
        description="Multimedia Systems Lab - Audio Analyzer (Task 03)"
    )
    parser.add_argument(
        "audio_path",
        nargs="?",
        default=None,
        help="Path to the audio file to analyze (optional)"
    )
    parser.add_argument(
        "-f", "--file",
        dest="file_path",
        default=None,
        help="Path to audio file (alternative flag)"
    )

    args = parser.parse_args()
    target_path = args.file_path or args.audio_path

    if not target_path:
        default_sample = find_default_sample()
        if default_sample:
            print(f"[Info] No audio path provided. Using sample: {default_sample}")
            target_path = default_sample
        else:
            target_path = input("Enter path to audio file: ").strip().strip('"').strip("'")

    if target_path:
        analyze_audio(target_path)
    else:
        print("[Error] No valid audio file specified.")


if __name__ == "__main__":
    main()