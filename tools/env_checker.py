"""
Environment & Multimedia Toolchain Diagnostic Utility
Multimedia Systems Laboratory
Author: Rudranshpardeshi09
"""

import sys
import os
import shutil
import platform
import subprocess


def get_status_symbol(is_ok: bool) -> str:
    """Return status marker."""
    return "[OK]" if is_ok else "[MISSING]"


def check_python_version():
    """Verify Python runtime version."""
    v = sys.version_info
    ver_str = f"{v.major}.{v.minor}.{v.micro}"
    is_supported = (v.major == 3 and v.minor >= 8)
    return is_supported, ver_str


def check_python_package(pkg_name: str, import_name: str = None):
    """Check if a Python package is installed and fetch its version."""
    if import_name is None:
        import_name = pkg_name
    try:
        mod = __import__(import_name)
        ver = getattr(mod, "__version__", "Installed")
        return True, str(ver)
    except ImportError:
        return False, "Not Installed"


def check_cli_tool(tool_name: str):
    """Check if a CLI binary (like ffmpeg or ffprobe) is available on PATH."""
    path = shutil.which(tool_name)
    if path:
        try:
            res = subprocess.run([tool_name, "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            first_line = res.stdout.splitlines()[0] if res.stdout else "Available"
            return True, first_line[:40]
        except Exception:
            return True, path
    return False, "Not Found in PATH"


def run_diagnostics():
    """Execute complete environment diagnostic check."""
    print("=" * 65)
    print("   MULTIMEDIA SYSTEMS LAB - ENVIRONMENT & TOOLCHAIN CHECK   ")
    print("=" * 65)
    print(f"OS Platform     : {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"Working Dir     : {os.getcwd()}")
    print("-" * 65)

    py_ok, py_ver = check_python_version()
    print(f"{get_status_symbol(py_ok):<10} Python Runtime       : {py_ver} (Req: >= 3.8)")

    print("\n[Core Python Libraries]")
    print("-" * 65)
    core_packages = [
        ("Pillow", "PIL"),
        ("tabulate", "tabulate"),
        ("colorama", "colorama"),
    ]

    all_core_ok = True
    for display_name, mod_name in core_packages:
        ok, ver = check_python_package(display_name, mod_name)
        if not ok:
            all_core_ok = False
        print(f"{get_status_symbol(ok):<10} {display_name:<20}: {ver}")

    print("\n[Optional / Advanced Libraries]")
    print("-" * 65)
    opt_packages = [
        ("numpy", "numpy"),
        ("opencv-python", "cv2"),
        ("matplotlib", "matplotlib"),
        ("scipy", "scipy"),
    ]

    for display_name, mod_name in opt_packages:
        ok, ver = check_python_package(display_name, mod_name)
        print(f"{get_status_symbol(ok):<10} {display_name:<20}: {ver}")

    print("\n[Multimedia System Binaries]")
    print("-" * 65)
    binaries = ["ffmpeg", "ffprobe"]
    all_binaries_ok = True
    for b in binaries:
        ok, detail = check_cli_tool(b)
        if not ok:
            all_binaries_ok = False
        print(f"{get_status_symbol(ok):<10} {b:<20}: {detail}")

    print("=" * 65)
    if all_core_ok:
        print("Status: Core multimedia environment is ready!")
    else:
        print("Action Required: Install dependencies via:")
        print("   pip install -r requirements.txt")

    if not all_binaries_ok:
        print("\nNote on FFmpeg/FFprobe:")
        print("   FFmpeg is recommended for Audio and Video analysis.")
        print("   - Windows: winget install Gyan.FFmpeg (or download from ffmpeg.org)")
        print("   - macOS: brew install ffmpeg")
        print("   - Linux: sudo apt install ffmpeg")
    print("=" * 65)


if __name__ == "__main__":
    run_diagnostics()
