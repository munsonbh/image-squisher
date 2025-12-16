"""Image conversion to JPEG XL and WebP formats."""

import io
import subprocess
import shutil
import platform
import threading
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image


def is_animated_gif(image_path: Path) -> bool:
    """
    Check if a GIF file is animated (has multiple frames).
    
    Args:
        image_path: Path to the image file
        
    Returns:
        True if the file is an animated GIF, False otherwise
    """
    if image_path.suffix.lower() != '.gif':
        return False
    
    try:
        with Image.open(image_path) as img:
            # Check if it's a GIF and has multiple frames
            if hasattr(img, 'is_animated'):
                return img.is_animated
            # Fallback: try to seek to frame 1
            try:
                img.seek(1)
                return True
            except EOFError:
                return False
    except Exception:
        return False


def _check_cjxl_available() -> Optional[str]:
    """Check if cjxl command is available and return its path."""
    # First try shutil.which (cross-platform)
    cjxl_path = shutil.which('cjxl')
    if cjxl_path and Path(cjxl_path).exists():
        return cjxl_path
    
    # Platform-specific paths
    system = platform.system()
    if system == 'Darwin':  # macOS
        cjxl_paths = [
            '/opt/homebrew/bin/cjxl',
            '/usr/local/bin/cjxl',
        ]
    elif system == 'Windows':
        # Windows: check common installation locations
        cjxl_paths = [
            Path.home() / 'AppData' / 'Local' / 'Programs' / 'cjxl.exe',
            Path('C:/Program Files/libjxl/bin/cjxl.exe'),
            Path('C:/Program Files (x86)/libjxl/bin/cjxl.exe'),
        ]
    else:  # Linux
        cjxl_paths = [
            '/usr/local/bin/cjxl',
            '/usr/bin/cjxl',
        ]
    
    for path in cjxl_paths:
        if isinstance(path, str):
            path = Path(path)
        if path.exists():
            return str(path)
    
    return None


def convert_to_jpegxl(image_path: Path, output_path: Path, quality: Optional[int] = None, effort: Optional[int] = None, timeout: Optional[int] = None) -> Optional[int]:
    """
    Convert an image to JPEG XL format (lossless, highest compression).
    Uses libjxl's cjxl command-line tool instead of Pillow.
    
    Note: JPEG XL doesn't support animation, so animated GIFs are skipped.
    
    Args:
        image_path: Path to the source image
        output_path: Path where the JPEG XL file should be saved
        quality: JPEG XL quality (1-100, 100 = lossless). If None, uses config value.
        effort: JPEG XL effort (0-9, 9 = highest compression). If None, uses config value.
        timeout: Conversion timeout in seconds. If None, uses config value.
        
    Returns:
        File size in bytes if successful, None if conversion failed
    """
    # Get settings from config if not provided
    if quality is None or effort is None or timeout is None:
        try:
            from config_loader import load_config
            config = load_config()
            if quality is None:
                quality = config.jpegxl_quality
            if effort is None:
                effort = config.jpegxl_effort
            if timeout is None:
                timeout = config.conversion_timeout
        except Exception:
            # Fallback to defaults
            if quality is None:
                quality = 100
            if effort is None:
                effort = 9
            if timeout is None:
                timeout = 300
    
    # Skip animated GIFs - JPEG XL doesn't support animation
    if is_animated_gif(image_path):
        return None
    
    # Check if cjxl is available
    cjxl = _check_cjxl_available()
    if not cjxl:
        return None
    
    try:
        # Use cjxl command-line tool for conversion
        # -q 100 = mathematically lossless (quality 100)
        # -e 7 = effort 7 (good compression, much faster than 9 with minimal size difference)
        # Note: cjxl doesn't have --lossless flag, use -q 100 instead
        result = subprocess.run(
            [
                cjxl,
                str(image_path),
                str(output_path),
                '-q', str(quality),
                '-e', str(effort),
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        
        if result.returncode == 0 and output_path.exists():
            return output_path.stat().st_size
        else:
            # Conversion failed - log error for debugging
            if result.stderr:
                # Only log if there's actual error output (ignore warnings)
                error_msg = result.stderr.strip()
                if error_msg and not error_msg.startswith('Warn'):
                    # Silently fail - errors are expected for some images
                    pass
            # Conversion failed
            if output_path.exists():
                output_path.unlink()
            return None
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        # Conversion failed
        if output_path.exists():
            output_path.unlink()
        return None


def convert_to_webp(image_path: Path, output_path: Path, method: Optional[int] = None, max_frames: Optional[int] = None) -> Optional[int]:
    """
    Convert an image to WebP format (lossless, highest compression).
    Supports both static images and animated GIFs (converts to animated WebP).
    
    Args:
        image_path: Path to the source image
        output_path: Path where the WebP file should be saved
        method: WebP compression method (0-6, 6 = highest). If None, uses config value.
        max_frames: Maximum frames for animated GIFs. If None, uses config value.
        
    Returns:
        File size in bytes if successful, None if conversion failed
    """
    # Get settings from config if not provided
    if method is None or max_frames is None:
        try:
            from config_loader import load_config
            config = load_config()
            if method is None:
                method = config.webp_method
            if max_frames is None:
                max_frames = config.max_animated_frames
        except Exception:
            # Fallback to defaults
            if method is None:
                method = 6
            if max_frames is None:
                max_frames = 1000
    
    try:
        with Image.open(image_path) as img:
            # Check if it's an animated GIF
            if is_animated_gif(image_path):
                # Convert animated GIF to animated WebP
                frames = []
                durations = []
                
                try:
                    # Extract all frames
                    frame_count = 0
                    
                    while True:
                        # Convert frame to RGBA if needed
                        frame = img.copy()
                        if frame.mode in ('P', 'LA', 'PA'):
                            frame = frame.convert('RGBA')
                        elif frame.mode == 'L':
                            # Keep grayscale as-is
                            pass
                        elif frame.mode not in ('RGB', 'RGBA'):
                            frame = frame.convert('RGB')
                        
                        frames.append(frame)
                        
                        # Get frame duration (default to 100ms if not available)
                        duration = img.info.get('duration', 100)
                        durations.append(duration)
                        
                        frame_count += 1
                        if frame_count >= max_frames:
                            break
                        
                        # Try to seek to next frame
                        try:
                            img.seek(img.tell() + 1)
                        except EOFError:
                            break
                    
                    if not frames:
                        return None
                    
                    # Save as animated WebP
                    frames[0].save(
                        output_path,
                        format='WEBP',
                        save_all=True,
                        append_images=frames[1:],
                        duration=durations,
                        lossless=True,
                        method=method,
                        loop=img.info.get('loop', 0),  # Preserve loop count if available
                    )
                    
                    return output_path.stat().st_size
                    
                except Exception as e:
                    # If animated conversion fails, return None
                    return None
            
            # Static image conversion
            # Convert to RGB/RGBA if needed
            if img.mode in ('P', 'LA', 'PA'):
                img = img.convert('RGBA')
            elif img.mode == 'L':
                # Keep grayscale as-is
                pass
            elif img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')
            
            # Save as WebP with lossless compression and high quality
            img.save(
                output_path,
                format='WEBP',
                lossless=True,
                method=method,
                # Metadata is not copied by default
            )
            
            return output_path.stat().st_size
    except Exception as e:
        return None


def convert_image(image_path: Path, temp_dir: Path, original_size: Optional[int] = None) -> Tuple[Optional[Path], Optional[Path], Optional[int], Optional[int]]:
    """
    Convert an image to both JPEG XL and WebP formats in parallel.
    
    Args:
        image_path: Path to the source image
        temp_dir: Directory where temporary converted files should be saved
        original_size: Original file size in bytes (for early exit optimization)
        
    Returns:
        Tuple of (jxl_path, webp_path, jxl_size, webp_size)
        Paths and sizes will be None if conversion failed
    """
    base_name = image_path.stem
    
    jxl_path = temp_dir / f"{base_name}.tmp.jxl"
    webp_path = temp_dir / f"{base_name}.tmp.webp"
    
    # Convert both formats in parallel using threads
    jxl_result = [None]  # Use list to allow modification from nested function
    webp_result = [None]
    
    def convert_jxl():
        jxl_result[0] = convert_to_jpegxl(image_path, jxl_path)
    
    def convert_webp():
        webp_result[0] = convert_to_webp(image_path, webp_path)
    
    # Start both conversions in parallel
    jxl_thread = threading.Thread(target=convert_jxl)
    webp_thread = threading.Thread(target=convert_webp)
    
    jxl_thread.start()
    webp_thread.start()
    
    # Wait for JXL to complete first (it's usually faster)
    jxl_thread.join()
    jxl_size = jxl_result[0]
    
    # Early exit optimization: if JXL is already significantly smaller than original,
    # we can skip waiting for WebP (but still let it finish in background)
    skip_webp_wait = False
    if original_size and jxl_size and jxl_size < original_size * 0.7:  # JXL is 30%+ smaller
        # JXL is already very good, but still wait for WebP to compare
        # (WebP might be even smaller)
        pass
    
    # Wait for WebP to complete
    webp_thread.join()
    webp_size = webp_result[0]
    
    # Clean up if conversion failed
    if jxl_size is None and jxl_path.exists():
        jxl_path.unlink()
        jxl_path = None
    
    if webp_size is None and webp_path.exists():
        webp_path.unlink()
        webp_path = None
    
    return jxl_path, webp_path, jxl_size, webp_size

