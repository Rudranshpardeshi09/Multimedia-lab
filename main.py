"""
Multimedia Systems Lab - Unified CLI Launcher & Suite Runner
Author: Rudranshpardeshi09
"""

import sys
import subprocess
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

TASK_MAP = {
    "1": ("Task 01: Image Spatial & EXIF Metadata Analyzer", ROOT_DIR / "task-01-image-analyser" / "image_analyser.py"),
    "2": ("Task 02: Video Stream Demuxer & Metadata Analyzer", ROOT_DIR / "task-02-video-analyser" / "video_analyser.py"),
    "3": ("Task 03: Audio Signal & Stream Properties Analyzer", ROOT_DIR / "task-03-audio-analyser" / "audio_analyser.py"),
    "d": ("Diagnostics: Environment & Toolchain Check", ROOT_DIR / "tools" / "env_checker.py"),
}


def run_script(script_path: Path, extra_args=None):
    """Execute a python script in a subprocess."""
    if not script_path.exists():
        print(f"[Error] Target script not found: {script_path}")
        return

    cmd = [sys.executable, str(script_path)]
    if extra_args:
        cmd.extend(extra_args)

    print(f"\n[Executing] {' '.join(cmd)}\n")
    subprocess.run(cmd)


def interactive_menu():
    """Display interactive terminal selection menu."""
    while True:
        print("\n" + "=" * 65)
        print("          MULTIMEDIA SYSTEMS LAB - CLI TASK RUNNER          ")
        print("                 Author: Rudranshpardeshi09                 ")
        print("=" * 65)
        print("Select a task or tool to execute:\n")
        print(f"  [1] {TASK_MAP['1'][0]}")
        print(f"  [2] {TASK_MAP['2'][0]}")
        print(f"  [3] {TASK_MAP['3'][0]}")
        print(f"  [D] {TASK_MAP['d'][0]}")
        print("  [A] Run All 3 Tasks & Diagnostics")
        print("  [Q] Exit")
        print("-" * 65)

        choice = input("Enter choice (1, 2, 3, D, A, Q): ").strip().lower()

        if choice == "q":
            print("Exiting launcher. Goodbye!")
            break
        elif choice == "a":
            for k in ["d", "1", "2", "3"]:
                _, path = TASK_MAP[k]
                run_script(path)
        elif choice in TASK_MAP:
            _, path = TASK_MAP[choice]
            run_script(path)
        else:
            print("[Warning] Invalid selection. Please enter 1, 2, 3, D, A, or Q.")


def main():
    parser = argparse.ArgumentParser(
        description="Multimedia Systems Lab - Central Task Runner (Rudranshpardeshi09)"
    )
    parser.add_argument(
        "-t", "--task",
        choices=["1", "2", "3", "d", "all"],
        help="Task number to execute directly (1: Image, 2: Video, 3: Audio, d: Diagnostics, all: All)"
    )
    parser.add_argument(
        "-f", "--file",
        help="Optional custom media file path to pass to the analyzer"
    )

    args = parser.parse_args()

    if args.task:
        if args.task == "all":
            for k in ["d", "1", "2", "3"]:
                _, path = TASK_MAP[k]
                run_script(path)
        else:
            _, path = TASK_MAP[args.task.lower()]
            extra = ["--file", args.file] if args.file else []
            run_script(path, extra)
    else:
        interactive_menu()


if __name__ == "__main__":
    main()
