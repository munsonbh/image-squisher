"""Image conversion to JPEG XL and WebP formats."""

import io
import logging
import subprocess
import shutil
import platform
from pathlib import Path
from typing import Optional, Tuple, List
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
                    logger = logging.getLogger('image-squisher')
                    logger.debug(f"Animated WebP conversion failed for {image_path.name}: {e}")
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
        logger = logging.getLogger('image-squisher')
        logger.debug(f"WebP conversion failed for {image_path.name}: {e}")
        return None


def convert_image(
    image_path: Path,
    temp_dir: Path,
    original_size: Optional[int] = None,
    jpegxl_quality: Optional[int] = None,
    jpegxl_effort: Optional[int] = None,
    webp_method: Optional[int] = None,
    max_animated_frames: Optional[int] = None,
    conversion_timeout: Optional[int] = None,
    skip_second_threshold: Optional[float] = None
) -> Tuple[Optional[Path], Optional[Path], Optional[int], Optional[int]]:
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
    logger = logging.getLogger('image-squisher')

    base_name = image_path.stem

    jxl_path = temp_dir / f"{base_name}.tmp.jxl"
    webp_path = temp_dir / f"{base_name}.tmp.webp"
    
    # Resolve conversion settings once for this image to avoid repeated config loads
    if (
        jpegxl_quality is None
        or jpegxl_effort is None
        or webp_method is None
        or max_animated_frames is None
        or conversion_timeout is None
        or skip_second_threshold is None
    ):
        try:
            from config_loader import load_config
            config = load_config()
            if jpegxl_quality is None:
                jpegxl_quality = config.jpegxl_quality
            if jpegxl_effort is None:
                jpegxl_effort = config.jpegxl_effort
            if webp_method is None:
                webp_method = config.webp_method
            if max_animated_frames is None:
                max_animated_frames = config.max_animated_frames
            if conversion_timeout is None:
                conversion_timeout = config.conversion_timeout
            if skip_second_threshold is None:
                skip_second_threshold = config.skip_second_threshold
        except Exception:
            if jpegxl_quality is None:
                jpegxl_quality = 100
            if jpegxl_effort is None:
                jpegxl_effort = 9
            if webp_method is None:
                webp_method = 6
            if max_animated_frames is None:
                max_animated_frames = 1000
            if conversion_timeout is None:
                conversion_timeout = 300
            if skip_second_threshold is None:
                skip_second_threshold = 0.70
    
    jxl_size: Optional[int] = None
    webp_size: Optional[int] = None
    jxl_error: Optional[str] = None
    webp_error: Optional[str] = None

    # File-type heuristic: PNG/GIF-like images often favor WebP; JPEG/TIFF-like often favor JXL.
    prefer_webp_exts = {'.png', '.gif', '.bmp'}
    suffix = image_path.suffix.lower()
    run_order: List[str] = ['webp', 'jxl'] if suffix in prefer_webp_exts else ['jxl', 'webp']

    # If the first conversion is already much smaller than original, skip the second pass.
    # This intentionally trades a tiny amount of possible savings for substantially less CPU/log I/O.
    if skip_second_threshold is None:
        skip_second_threshold = 0.70

    for idx, codec in enumerate(run_order):
        is_second = idx == 1
        if is_second:
            first_size = webp_size if run_order[0] == 'webp' else jxl_size
            if original_size and first_size and first_size <= int(original_size * skip_second_threshold):
                logger.debug(
                    f"Skipping second codec for {image_path.name}: "
                    f"first result already <= {int(skip_second_threshold * 100)}% of original"
                )
                break

        if codec == 'jxl':
            try:
                jxl_size = convert_to_jpegxl(
                    image_path,
                    jxl_path,
                    quality=jpegxl_quality,
                    effort=jpegxl_effort,
                    timeout=conversion_timeout
                )
                if jxl_size is None:
                    logger.debug(f"JXL conversion failed for {image_path.name}")
                else:
                    logger.debug(f"JXL conversion succeeded for {image_path.name}: {jxl_size} bytes")
            except Exception as e:
                jxl_error = str(e)
                logger.warning(f"JXL conversion exception for {image_path.name}: {e}", exc_info=True)
        else:
            try:
                webp_size = convert_to_webp(
                    image_path,
                    webp_path,
                    method=webp_method,
                    max_frames=max_animated_frames
                )
                if webp_size is None:
                    logger.debug(f"WebP conversion failed for {image_path.name}")
                else:
                    logger.debug(f"WebP conversion succeeded for {image_path.name}: {webp_size} bytes")
            except Exception as e:
                webp_error = str(e)
                logger.warning(f"WebP conversion exception for {image_path.name}: {e}", exc_info=True)
    
    # Log results for debugging
    if jxl_size is None and webp_size is None:
        logger.warning(f"Both JXL and WebP conversions failed for {image_path.name}")
        if jxl_error:
            logger.warning(f"JXL error: {jxl_error}")
        if webp_error:
            logger.warning(f"WebP error: {webp_error}")
    elif jxl_size is None:
        logger.debug(f"JXL conversion failed, WebP succeeded ({webp_size} bytes) for {image_path.name}")
    elif webp_size is None:
        logger.debug(f"WebP conversion failed, JXL succeeded ({jxl_size} bytes) for {image_path.name}")
    else:
        logger.debug(f"Both conversions succeeded for {image_path.name}: JXL={jxl_size} bytes, WebP={webp_size} bytes")
    
    # Clean up if conversion failed
    if jxl_size is None and jxl_path.exists():
        jxl_path.unlink()
        jxl_path = None
    
    if webp_size is None and webp_path.exists():
        webp_path.unlink()
        webp_path = None
    
    return jxl_path, webp_path, jxl_size, webp_size

