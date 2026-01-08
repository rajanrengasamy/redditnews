"""
Image Resizer Utility

Resizes existing Stage 6 images to exact Instagram dimensions.
Useful for fixing images from previous sessions without re-running Stage 6.

Usage:
    python -m utils.resize_images /path/to/session/images/

Instagram Specs:
    - Portrait (4:5): 1080x1350 - recommended for maximum screen real estate
    - Square (1:1): 1080x1080
    - Landscape (1.91:1): 1080x566
"""

import argparse
import os
import sys
from io import BytesIO
from PIL import Image


# Instagram dimension presets
INSTAGRAM_PRESETS = {
    "portrait": (1080, 1350),  # 4:5 - default/recommended
    "square": (1080, 1080),    # 1:1
    "landscape": (1080, 566),  # 1.91:1
}


def resize_to_instagram(
    input_path: str,
    output_path: str = None,
    preset: str = "portrait"
) -> str:
    """
    Resize an image to exact Instagram dimensions.

    Args:
        input_path: Path to input image
        output_path: Path for output (defaults to overwriting input)
        preset: One of "portrait", "square", "landscape"

    Returns:
        Path to resized image
    """
    target_width, target_height = INSTAGRAM_PRESETS.get(preset, INSTAGRAM_PRESETS["portrait"])

    # Open image
    img = Image.open(input_path)
    orig_width, orig_height = img.size

    # Already correct dimensions?
    if orig_width == target_width and orig_height == target_height:
        print(f"  ✓ {os.path.basename(input_path)}: Already {target_width}x{target_height}")
        return input_path

    # Calculate aspect ratios
    target_ratio = target_width / target_height
    orig_ratio = orig_width / orig_height

    # Resize strategy: scale to fill, then crop to exact dimensions
    if orig_ratio > target_ratio:
        # Image is wider - scale by height, crop width
        new_height = target_height
        new_width = int(orig_width * (target_height / orig_height))
    else:
        # Image is taller - scale by width, crop height
        new_width = target_width
        new_height = int(orig_height * (target_width / orig_width))

    # Resize with high-quality resampling
    img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Crop to exact target dimensions (center crop)
    left = (new_width - target_width) // 2
    top = (new_height - target_height) // 2
    right = left + target_width
    bottom = top + target_height

    img_cropped = img_resized.crop((left, top, right, bottom))

    # Save
    output = output_path or input_path
    img_cropped.save(output, format='PNG', optimize=True)

    print(f"  ✓ {os.path.basename(input_path)}: {orig_width}x{orig_height} → {target_width}x{target_height}")
    return output


def resize_directory(
    directory: str,
    preset: str = "portrait",
    backup: bool = True
) -> int:
    """
    Resize all PNG images in a directory.

    Args:
        directory: Path to directory containing images
        preset: Instagram dimension preset
        backup: If True, save originals with .bak suffix

    Returns:
        Number of images processed
    """
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a directory")
        return 0

    png_files = [f for f in os.listdir(directory) if f.lower().endswith('.png')]

    if not png_files:
        print(f"No PNG files found in {directory}")
        return 0

    print(f"Resizing {len(png_files)} images to {preset} ({INSTAGRAM_PRESETS[preset][0]}x{INSTAGRAM_PRESETS[preset][1]})")
    print()

    count = 0
    for filename in sorted(png_files):
        filepath = os.path.join(directory, filename)

        # Create backup if requested
        if backup:
            backup_path = filepath + ".bak"
            if not os.path.exists(backup_path):
                import shutil
                shutil.copy2(filepath, backup_path)

        try:
            resize_to_instagram(filepath, preset=preset)
            count += 1
        except Exception as e:
            print(f"  ✗ {filename}: {e}")

    print()
    print(f"Done! Resized {count}/{len(png_files)} images.")
    return count


def main():
    parser = argparse.ArgumentParser(
        description="Resize images to Instagram dimensions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Resize all images in session folder to portrait (4:5)
    python -m utils.resize_images ../output/session_20260107_224303/images/

    # Resize to square format
    python -m utils.resize_images --preset square ../output/session_*/images/

    # No backup (overwrite originals)
    python -m utils.resize_images --no-backup ../output/session_*/images/
        """
    )
    parser.add_argument("directory", help="Directory containing PNG images")
    parser.add_argument(
        "--preset", "-p",
        choices=list(INSTAGRAM_PRESETS.keys()),
        default="portrait",
        help="Instagram dimension preset (default: portrait)"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Don't create backup of original images"
    )

    args = parser.parse_args()

    resize_directory(
        args.directory,
        preset=args.preset,
        backup=not args.no_backup
    )


if __name__ == "__main__":
    main()
