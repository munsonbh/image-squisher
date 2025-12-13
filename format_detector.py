"""Format detection and image file scanning."""

import os
from pathlib import Path
from typing import List, Set, Tuple
from PIL import Image

# Common image extensions
IMAGE_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.jpe', '.jfif',
    '.tiff', '.tif', '.bmp', '.gif', '.webp',
    '.heic', '.heif', '.avif', '.jxl', '.jp2',
    '.ico', '.icns', '.tga', '.dds'
}


def is_image_file(filepath: Path) -> bool:
    """Check if a file is a valid image by attempting to open it."""
    try:
        # Try to open and load a small portion to verify it's a valid image
        with Image.open(filepath) as img:
            # Load a small portion to verify the image is valid
            # (verify() closes the image, so we just try to access properties)
            img.load()
        return True
    except Exception:
        return False


def scan_folder(folder_path: Path, recursive: bool = False) -> List[Path]:
    """
    Scan a folder for image files.
    
    Args:
        folder_path: Path to the folder to scan
        recursive: If True, scan subdirectories recursively
        
    Returns:
        List of paths to valid image files
    """
    image_files = []
    
    if recursive:
        pattern = '**/*'
    else:
        pattern = '*'
    
    for filepath in folder_path.glob(pattern):
        if filepath.is_file() and filepath.suffix.lower() in IMAGE_EXTENSIONS:
            if is_image_file(filepath):
                image_files.append(filepath)
    
    return sorted(image_files)


def detect_formats(image_files: List[Path]) -> Set[str]:
    """
    Detect which image formats are present in the file list.
    
    Args:
        image_files: List of image file paths
        
    Returns:
        Set of file extensions (lowercase, with dot) found
    """
    formats = set()
    for filepath in image_files:
        formats.add(filepath.suffix.lower())
    return formats

