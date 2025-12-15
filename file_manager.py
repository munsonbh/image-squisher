"""Safe file operations and size comparison."""

import os
from pathlib import Path
from typing import Optional, Tuple


def get_file_size(filepath: Path) -> int:
    """Get file size in bytes."""
    return filepath.stat().st_size


def verify_file(filepath: Path) -> bool:
    """
    Verify that a file is valid and readable.
    
    Args:
        filepath: Path to the file to verify
        
    Returns:
        True if file is valid, False otherwise
    """
    try:
        if not filepath.exists():
            return False
        # Try to open and read a small portion
        with open(filepath, 'rb') as f:
            f.read(1)
        return True
    except Exception:
        return False


def compare_and_keep_smallest(
    original_path: Path,
    jxl_path: Optional[Path],
    webp_path: Optional[Path],
    jxl_size: Optional[int],
    webp_size: Optional[int],
    min_improvement_pct: float = 5.0
) -> Tuple[Path, str]:
    """
    Compare file sizes and determine which file to keep.
    Only keeps a converted file if it's at least min_improvement_pct% smaller than original.
    
    Args:
        original_path: Path to the original image
        jxl_path: Path to JPEG XL version (if conversion succeeded)
        webp_path: Path to WebP version (if conversion succeeded)
        jxl_size: Size of JPEG XL file in bytes
        webp_size: Size of WebP file in bytes
        min_improvement_pct: Minimum percentage improvement required to keep converted file (default: 5.0)
        
    Returns:
        Tuple of (path_to_keep, format_name)
        format_name will be 'original', 'jxl', or 'webp'
    """
    original_size = get_file_size(original_path)
    
    # Build list of available options
    options = [('original', original_path, original_size)]
    
    if jxl_path and jxl_size is not None:
        options.append(('jxl', jxl_path, jxl_size))
    
    if webp_path and webp_size is not None:
        options.append(('webp', webp_path, webp_size))
    
    # Find the smallest
    smallest = min(options, key=lambda x: x[2])
    format_name, path_to_keep, size = smallest
    
    # If we're keeping a converted file, check if improvement meets threshold
    if format_name != 'original':
        savings = original_size - size
        improvement_pct = (savings / original_size * 100) if original_size > 0 else 0
        
        # If improvement is less than threshold, keep original
        if improvement_pct < min_improvement_pct:
            return original_path, 'original'
    
    return path_to_keep, format_name


def safely_replace_file(original_path: Path, new_path: Path, target_extension: str) -> Path:
    """
    Safely replace the original file with a new file using atomic operations.
    Updates the file extension to match the format.
    
    Args:
        original_path: Path to the original file
        new_path: Path to the new file that should replace it
        target_extension: Extension to use for the final file (e.g., '.webp', '.jxl')
        
    Returns:
        Path to the final file (with correct extension), or original_path if replacement failed
    """
    try:
        # Verify the new file is valid
        if not verify_file(new_path):
            return original_path
        
        # Create the target path with the correct extension
        target_path = original_path.parent / f"{original_path.stem}{target_extension}"
        
        # If target path is same as original (same extension), just replace directly
        if target_path == original_path:
            os.replace(new_path, original_path)
            return original_path
        
        # Different extension: rename temp file to target path, then delete original
        # First, rename temp file to target path (with correct extension)
        if new_path != target_path:
            os.replace(new_path, target_path)
        
        # Delete the original file (it's been replaced by the converted version)
        if original_path.exists() and original_path != target_path:
            original_path.unlink()
        
        return target_path
    except Exception:
        return original_path


def cleanup_temp_files(*filepaths: Optional[Path]) -> None:
    """
    Delete temporary files, ignoring errors.
    
    Args:
        *filepaths: Variable number of file paths to delete (None values are ignored)
    """
    for filepath in filepaths:
        if filepath and filepath.exists():
            try:
                filepath.unlink()
            except Exception:
                pass


def process_image(image_path: Path) -> Tuple[bool, str, int, int]:
    """
    Process a single image: convert, compare, and keep smallest.
    
    Args:
        image_path: Path to the image to process
        
    Returns:
        Tuple of (success, format_kept, original_size, final_size)
        success: True if processing completed successfully
        format_kept: 'original', 'jxl', or 'webp'
        original_size: Size of original file in bytes
        final_size: Size of final file in bytes
    """
    from processor import convert_image, is_animated_gif
    
    # Animated GIFs are now handled by convert_to_webp (converts to animated WebP)
    # JPEG XL doesn't support animation, so it will return None for animated GIFs
    
    # Skip files already in optimized formats (JXL or WebP)
    suffix_lower = image_path.suffix.lower()
    if suffix_lower in ('.jxl', '.webp'):
        # Already optimized, skip processing
        original_size = get_file_size(image_path)
        format_name = 'jxl' if suffix_lower == '.jxl' else 'webp'
        return True, format_name, original_size, original_size
    
    original_size = get_file_size(image_path)
    temp_dir = image_path.parent
    
    # Convert to both formats (in parallel)
    jxl_path, webp_path, jxl_size, webp_size = convert_image(image_path, temp_dir, original_size)
    
    try:
        # Compare and determine which to keep
        path_to_keep, format_name = compare_and_keep_smallest(
            image_path, jxl_path, webp_path, jxl_size, webp_size
        )
        
        # If we're keeping a converted file, replace the original
        final_path = image_path
        if format_name != 'original':
            # Determine the correct extension for the format
            if format_name == 'jxl':
                target_extension = '.jxl'
            elif format_name == 'webp':
                target_extension = '.webp'
            else:
                target_extension = image_path.suffix  # Fallback to original extension
            
            final_path = safely_replace_file(image_path, path_to_keep, target_extension)
            # Check if replacement failed
            # If we expected a different extension but got original_path back, it failed
            expected_path = image_path.parent / f"{image_path.stem}{target_extension}"
            if target_extension != image_path.suffix and final_path == image_path:
                # Replacement failed - keep original
                format_name = 'original'
                path_to_keep = image_path
                final_path = image_path
                cleanup_temp_files(jxl_path, webp_path)
            elif not final_path.exists():
                # File doesn't exist - replacement failed
                format_name = 'original'
                path_to_keep = image_path
                final_path = image_path
                cleanup_temp_files(jxl_path, webp_path)
            else:
                # Successfully kept a converted file - clean up the other converted file
                if format_name == 'jxl':
                    # We kept JXL, delete WebP
                    cleanup_temp_files(webp_path)
                elif format_name == 'webp':
                    # We kept WebP, delete JXL
                    cleanup_temp_files(jxl_path)
        else:
            # We're keeping the original, clean up converted files
            cleanup_temp_files(jxl_path, webp_path)
        
        final_size = get_file_size(final_path)
        
        return True, format_name, original_size, final_size
    
    except Exception as e:
        # On any error, clean up and keep original
        cleanup_temp_files(jxl_path, webp_path)
        return False, 'original', original_size, original_size

