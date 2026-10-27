"""
Task 01: Image Metadata & Spatial Properties Analyzer
Multimedia Systems Laboratory
Author: Rudranshpardeshi09
"""

import os
import sys
import argparse
from pathlib import Path
from PIL import Image, ExifTags


def format_file_size(size_in_bytes: int) -> str:
    """Convert file size from bytes to human-readable units."""
    units = ["Bytes", "KB", "MB", "GB", "TB"]
    size = float(size_in_bytes)

    for unit in units:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024

    return f"{size:.2f} PB"


def get_exif_data(image: Image.Image) -> dict:
    """Extract EXIF metadata dictionary from the image."""
    exif_data = {}
    try:
        raw_exif = image.getexif()
        if raw_exif:
            for tag_id, value in raw_exif.items():
                tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                exif_data[tag_name] = value
    except Exception:
        pass
    return exif_data


def get_dpi(image: Image.Image):
    """Return the DPI stored in the file, or None if there is none."""
    dpi = image.info.get("dpi")
    if dpi:
        return round(dpi[0]), round(dpi[1])
    return None


def get_resolution(image: Image.Image) -> str:
    """Pixel resolution with its common name where there is one."""
    names = {
        (1280, 720): "HD", (1920, 1080): "Full HD", (2560, 1440): "QHD",
        (3840, 2160): "4K UHD", (7680, 4320): "8K UHD",
    }
    size = tuple(sorted(image.size, reverse=True))
    label = names.get(size)
    return f"{image.width} x {image.height} px" + (f" ({label})" if label else "")


def get_print_size(image: Image.Image) -> str:
    """Physical print size using the stored DPI (300 DPI if none is stored)."""
    dpi = get_dpi(image)[0] if get_dpi(image) else 300
    width_in = image.width / dpi
    height_in = image.height / dpi
    return f"{width_in:.2f} x {height_in:.2f} in ({width_in * 2.54:.1f} x {height_in * 2.54:.1f} cm) @ {dpi} DPI"


def print_exif_metadata(exif_data: dict):
    """Print important and additional EXIF metadata cleanly."""
    print("\nEXIF Metadata")
    print("-" * 45)

    if not exif_data:
        print("No EXIF metadata embedded in this file.")
        return

    important_fields = {
        "Camera Make": "Make",
        "Camera Model": "Model",
        "Date Taken": "DateTimeOriginal",
        "Date Modified": "DateTime",
        "Orientation": "Orientation",
        "Software": "Software",
    }

    for display_name, exif_key in important_fields.items():
        value = exif_data.get(exif_key, "Not Available")
        print(f"{display_name:<20}: {value}")

    other_exif = {
        key: value
        for key, value in exif_data.items()
        if key not in important_fields.values()
    }

    if other_exif:
        print("\nAdditional EXIF Tags")
        print("-" * 45)
        for key, value in other_exif.items():
            print(f"{str(key):<20}: {str(value)[:50]}")


def analyze_image(image_path: str) -> bool:
    """Analyze image and print comprehensive metadata report."""
    resolved_path = Path(image_path).resolve()

    if not resolved_path.exists():
        print(f"[Error] File not found: {resolved_path}")
        return False

    supported_extensions = {
        ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".webp", ".bmp", ".gif"
    }

    if resolved_path.suffix.lower() not in supported_extensions:
        print(f"[Error] Unsupported image format: {resolved_path.suffix}")
        print(f"Supported formats: {', '.join(sorted(supported_extensions))}")
        return False

    try:
        with Image.open(resolved_path) as img:
            file_name = resolved_path.name
            file_size = resolved_path.stat().st_size
            width, height = img.size
            megapixels = (width * height) / 1_000_000

            print("=" * 55)
            print("     TASK 01: IMAGE METADATA & ANALYSIS REPORT    ")
            print("=" * 55)

            print(f"\n[File Information]")
            print("-" * 45)
            print(f"File Name           : {file_name}")
            print(f"File Path           : {resolved_path}")
            print(f"File Size           : {format_file_size(file_size)}")
            print(f"File Format         : {img.format} ({img.format_description if hasattr(img, 'format_description') else ''})")

            print(f"\n[Spatial & Color Properties]")
            print("-" * 45)
            print(f"Dimensions          : {width} x {height} px")
            print(f"Megapixels          : {megapixels:.2f} MP")
            print(f"Aspect Ratio        : {width / height:.2f}:1")
            dpi = get_dpi(img)
            print(f"Resolution          : {get_resolution(img)}")
            print(f"DPI                 : {f'{dpi[0]} x {dpi[1]} DPI' if dpi else 'Not stored in file (viewers assume 72 DPI)'}")
            print(f"Print Size          : {get_print_size(img)}")
            print(f"Color Mode          : {img.mode}")
            print(f"Number of Bands     : {len(img.getbands())} ({', '.join(img.getbands())})")

            exif_data = get_exif_data(img)
            print_exif_metadata(exif_data)

            print("\n" + "=" * 55)
            print("                 REPORT COMPLETED                 ")
            print("=" * 55)
            return True

    except Exception as error:
        print(f"[Error] Failed to analyze image: {error}")
        return False


def find_default_sample() -> str:
    """Locate sample image from the datasets folder."""
    candidates = [
        Path(__file__).resolve().parent / "input" / "bike.png",
        Path(__file__).resolve().parent.parent / "datasets" / "images" / "flower.jpg",
        Path(__file__).resolve().parent.parent / "datasets" / "images" / "flower2.jpg",
        Path("datasets/images/flower.jpg"),
        Path("../datasets/images/flower.jpg"),
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return ""


def main():
    parser = argparse.ArgumentParser(
        description="Multimedia Systems Lab - Image Analyzer (Task 01)"
    )
    parser.add_argument(
        "image_path",
        nargs="?",
        default=None,
        help="Path to the image file to analyze (optional)"
    )
    parser.add_argument(
        "-f", "--file",
        dest="file_path",
        default=None,
        help="Path to the image file (alternative flag)"
    )

    args = parser.parse_args()
    target_path = args.file_path or args.image_path

    if not target_path:
        default_sample = find_default_sample()
        if default_sample:
            print(f"[Info] No image path provided. Using sample: {default_sample}\n")
            target_path = default_sample
        else:
            target_path = input("Enter path to image file: ").strip().strip('"').strip("'")

    if target_path:
        analyze_image(target_path)
    else:
        print("[Error] No valid image file specified.")


if __name__ == "__main__":
    main()