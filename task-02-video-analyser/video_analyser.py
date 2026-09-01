"""
Task 02: Video Stream & Container Metadata Analyzer
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


def get_video_metadata(video_path: str) -> dict:
    """Extract video container and stream metadata using FFprobe."""
    command = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        video_path
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


def get_streams(streams: list):
    """Find and return the primary video and audio streams."""
    video_stream = None
    audio_stream = None
    for stream in streams:
        if stream.get("codec_type") == "video" and video_stream is None:
            video_stream = stream
        elif stream.get("codec_type") == "audio" and audio_stream is None:
            audio_stream = stream
    return video_stream, audio_stream


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


def analyze_video(video_path: str) -> bool:
    """Analyze a video file and generate comprehensive metadata report."""
    resolved_path = Path(video_path).resolve()

    if not resolved_path.exists():
        print(f"\n[Error] Video file not found: {resolved_path}")
        return False

    if not resolved_path.is_file():
        print(f"\n[Error] Provided path is not a file: {resolved_path}")
        return False

    if not check_ffprobe():
        print("\n[Notice] 'ffprobe' is required for full video & audio stream decoding.")
        print("To install FFmpeg/FFprobe:")
        print(" - Windows: winget install Gyan.FFmpeg")
        print(" - macOS  : brew install ffmpeg")
        print(" - Linux  : sudo apt install ffmpeg")

        # Fallback basic file info
        file_size = resolved_path.stat().st_size
        print("\n" + "=" * 50)
        print("   BASIC VIDEO FILE INFORMATION (FALLBACK)   ")
        print("=" * 50)
        print_tag("File Name", resolved_path.name)
        print_tag("File Extension", resolved_path.suffix.upper())
        print_tag("File Size", format_file_size(file_size))
        print_tag("Full Path", str(resolved_path))
        print("=" * 50)
        return False

    try:
        metadata = get_video_metadata(str(resolved_path))
        file_size = resolved_path.stat().st_size

        format_data = metadata.get("format", {})
        streams = metadata.get("streams", [])
        video_stream, audio_stream = get_streams(streams)

        print("\n" + "=" * 55)
        print("     TASK 02: VIDEO METADATA & ANALYSIS REPORT    ")
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

        # Video Stream Properties
        print("\n[Video Stream Properties]")
        print("-" * 45)
        if video_stream:
            print_tag("Codec", video_stream.get("codec_long_name"))
            print_tag("Codec Name", video_stream.get("codec_name"))
            w = video_stream.get("width")
            h = video_stream.get("height")
            print_tag("Resolution", f"{w} x {h} px" if (w and h) else "Not Available")
            
            fps = video_stream.get("avg_frame_rate")
            if fps and "/" in fps:
                num, den = fps.split("/")
                if den != "0":
                    fps_val = float(num) / float(den)
                    fps = f"{fps_val:.2f} fps"
                else:
                    fps = "Not Available"
            print_tag("Frame Rate (FPS)", fps)

            v_br = video_stream.get("bit_rate")
            print_tag("Video Bitrate", f"{int(v_br) / 1000:.2f} kbps" if v_br else "Not Available")
            print_tag("Aspect Ratio", video_stream.get("display_aspect_ratio"))
            print_tag("Pixel Format", video_stream.get("pix_fmt"))
        else:
            print("No video stream found.")

        # Audio Stream Properties
        print("\n[Audio Stream Properties]")
        print("-" * 45)
        if audio_stream:
            print_tag("Audio Codec", audio_stream.get("codec_long_name"))
            print_tag("Audio Codec Name", audio_stream.get("codec_name"))
            sr = audio_stream.get("sample_rate")
            print_tag("Sample Rate", f"{sr} Hz" if sr else "Not Available")
            print_tag("Channels", audio_stream.get("channels"))
            print_tag("Channel Layout", audio_stream.get("channel_layout"))
            print_tag("Sample Format", audio_stream.get("sample_fmt"))
            a_br = audio_stream.get("bit_rate")
            print_tag("Audio Bitrate", f"{int(a_br) / 1000:.2f} kbps" if a_br else "Not Available")
        else:
            print("No audio stream in video container.")

        # Tags
        tags = format_data.get("tags", {})
        if tags:
            print("\n[Container Metadata / Tags]")
            print("-" * 45)
            print_tags(tags)

        print("\n" + "=" * 55)
        print("                 REPORT COMPLETED                 ")
        print("=" * 55)
        return True

    except Exception as error:
        print(f"\n[Error] While processing video: {error}")
        return False


def find_default_sample() -> str:
    """Locate sample video from datasets/video directory."""
    candidates = [
        Path(__file__).resolve().parent.parent / "datasets" / "video" / "voiceover.mp4",
        Path("datasets/video/voiceover.mp4"),
        Path("../datasets/video/voiceover.mp4"),
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return ""


def main():
    parser = argparse.ArgumentParser(
        description="Multimedia Systems Lab - Video Analyzer (Task 02)"
    )
    parser.add_argument(
        "video_path",
        nargs="?",
        default=None,
        help="Path to the video file to analyze (optional)"
    )
    parser.add_argument(
        "-f", "--file",
        dest="file_path",
        default=None,
        help="Path to video file (alternative flag)"
    )

    args = parser.parse_args()
    target_path = args.file_path or args.video_path

    if not target_path:
        default_sample = find_default_sample()
        if default_sample:
            print(f"[Info] No video path provided. Using sample: {default_sample}")
            target_path = default_sample
        else:
            target_path = input("Enter path to video file: ").strip().strip('"').strip("'")

    if target_path:
        analyze_video(target_path)
    else:
        print("[Error] No valid video file specified.")


if __name__ == "__main__":
    main()
