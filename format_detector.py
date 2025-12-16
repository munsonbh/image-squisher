"""Format detection and image file scanning."""

import os
from pathlib import Path
from typing import List, Set, Tuple, Optional
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


def scan_folder(folder_path: Path, recursive: bool = False, skip_extensions: Optional[List[str]] = None) -> List[Path]:
    """
    Scan a folder for image files.
    Skips file types specified in skip_extensions (defaults to .webp and .jxl).
    
    Args:
        folder_path: Path to the folder to scan
        recursive: If True, scan subdirectories recursively
        skip_extensions: List of extensions to skip (e.g., ['.webp', '.jxl']). 
                        If None, uses default from config.
        
    Returns:
        List of paths to valid image files
    """
    image_files = []
    
    # Use provided skip_extensions or default
    if skip_extensions is None:
        try:
            from config_loader import load_config
            config = load_config()
            skip_extensions_set = set(config.skip_extensions)
        except Exception:
            # Fallback to default if config can't be loaded
            skip_extensions_set = {'.webp', '.jxl'}
    else:
        skip_extensions_set = {ext.lower() for ext in skip_extensions}
    
    if recursive:
        pattern = '**/*'
    else:
        pattern = '*'
    
    for filepath in folder_path.glob(pattern):
        if filepath.is_file() and filepath.suffix.lower() in IMAGE_EXTENSIONS:
            # Skip specified file types
            if filepath.suffix.lower() in skip_extensions_set:
                continue
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

