#!/usr/bin/env python3
"""Image compression tool - losslessly converts images to JPEG XL/WebP and keeps smallest."""

import argparse
import sys
import subprocess
import logging
import time
import platform
from pathlib import Path
from typing import List, Optional

from format_detector import scan_folder, detect_formats
from file_manager import process_image


def format_bytes(bytes: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} TB"


def check_terminal_notifier() -> Optional[str]:
    """Check if terminal-notifier is available and return its path (macOS only)."""
    system = platform.system()
    if system != 'Darwin':
        # terminal-notifier is macOS-only
        return None
    
    # Try shutil.which first (cross-platform)
    notifier_path = shutil.which('terminal-notifier')
    if notifier_path and Path(notifier_path).exists():
        return notifier_path
    
    # macOS-specific paths
    paths = [
        '/opt/homebrew/bin/terminal-notifier',
        '/usr/local/bin/terminal-notifier',
    ]
    for path in paths:
        if path and Path(path).exists():
            return path
    return None


def send_notification(title: str, message: str, sound: str = 'default') -> bool:
    """
    Send a notification (macOS: terminal-notifier, Windows: toast, Linux: notify-send).
    
    Args:
        title: Notification title
        message: Notification message
        sound: Notification sound (macOS only, default: 'default')
        
    Returns:
        True if notification was sent, False otherwise
    """
    system = platform.system()
    
    if system == 'Darwin':  # macOS
        notifier = check_terminal_notifier()
        if not notifier:
            return False
        try:
            subprocess.run(
                [
                    notifier,
                    '-title', title,
                    '-message', message,
                    '-sound', sound
                ],
                capture_output=True,
                timeout=5
            )
            return True
        except Exception:
            return False
    
    elif system == 'Windows':  # Windows
        try:
            # Use Windows toast notifications via PowerShell
            # Escape message for PowerShell
            escaped_title = title.replace('"', '`"')
            escaped_message = message.replace('"', '`"').replace('\n', '`n')
            ps_command = f'[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null; $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02); $text = $template.GetElementsByTagName("text"); $text[0].AppendChild($template.CreateTextNode("{escaped_title}")) > $null; $text[1].AppendChild($template.CreateTextNode("{escaped_message}")) > $null; $toast = [Windows.UI.Notifications.ToastNotification]::new($template); [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Image Squisher").Show($toast)'
            subprocess.run(
                ['powershell', '-Command', ps_command],
                capture_output=True,
                timeout=5,
                shell=True
            )
            return True
        except Exception:
            # Fallback: try win10toast if available, or just return False
            return False
    
    elif system == 'Linux':  # Linux
        try:
            # Try notify-send (common on Linux)
            subprocess.run(
                ['notify-send', title, message],
                capture_output=True,
                timeout=5
            )
            return True
        except Exception:
            return False
    
    return False


def setup_logging(log_file: Optional[Path] = None) -> logging.Logger:
    """
    Set up logging to both file and console.
    
    Args:
        log_file: Path to log file (default: image-squisher.log in current directory)
        
    Returns:
        Configured logger
    """
    if log_file is None:
        log_file = Path('image-squisher.log')
    
    # Create logger
    logger = logging.getLogger('image-squisher')
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Console handler (less verbose)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # Only show warnings/errors to console
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger


def main():
    parser = argparse.ArgumentParser(
        description='Losslessly compress images by converting to JPEG XL/WebP and keeping the smallest file.'
    )
    parser.add_argument(
        'folder',
        type=str,
        help='Path to folder containing images'
    )
    parser.add_argument(
        '--no-recursive',
        action='store_true',
        help='Only process top-level folder (disable recursive scanning)'
    )
    
    args = parser.parse_args()
    
    folder_path = Path(args.folder)
    
    if not folder_path.exists():
        print(f"Error: Folder '{folder_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
    
    if not folder_path.is_dir():
        print(f"Error: '{folder_path}' is not a directory.", file=sys.stderr)
        sys.exit(1)
    
    # Set up logging
    logger = setup_logging()
    logger.info(f"Starting image compression for folder: {folder_path}")
    logger.info(f"Recursive mode: {not args.no_recursive}")
    
    print(f"Scanning folder: {folder_path}")
    recursive = not args.no_recursive
    if recursive:
        print("Mode: Recursive (processing subdirectories)")
    else:
        print("Mode: Top-level only")
    print()
    
    # Scan for images
    logger.info("Scanning for image files...")
    image_files = scan_folder(folder_path, recursive=recursive)
    logger.info(f"Found {len(image_files)} image file(s)")
    
    if not image_files:
        print("No image files found.")
        sys.exit(0)
    
    # Detect and report formats
    formats = detect_formats(image_files)
    print(f"Found {len(image_files)} image file(s)")
    print(f"Formats detected: {', '.join(sorted(formats))}")
    
    # Check if JPEG XL support is available (via libjxl command-line tool)
    from processor import _check_cjxl_available
    cjxl_path = _check_cjxl_available()
    
    if not cjxl_path:
        system = platform.system()
        print("⚠ Warning: JPEG XL support not available (libjxl not installed)")
        if system == 'Darwin':
            print("  Install via: brew install jpeg-xl")
        elif system == 'Windows':
            print("  Install via: Download from https://github.com/libjxl/libjxl/releases")
            print("  Or use: winget install libjxl (if available)")
        else:
            print("  Install via your package manager (e.g., apt install libjxl-tools)")
        print("  Images will only be converted to WebP format.")
    else:
        print(f"✓ JPEG XL support available (using {cjxl_path})")
    print()
    
    # Process each image
    total_original = 0
    total_final = 0
    results = {'original': 0, 'jxl': 0, 'webp': 0}
    errors = 0
    start_time = time.time()
    last_progress_time = time.time()
    hang_timeout = 300  # 5 minutes without progress = potential hang
    
    for i, image_path in enumerate(image_files, 1):
        current_time = time.time()
        
        # Check for potential hang (no progress for hang_timeout seconds)
        if current_time - last_progress_time > hang_timeout:
            error_msg = f"Potential hang detected! Last processed: {image_files[i-2].name if i > 1 else 'none'}"
            logger.error(error_msg)
            logger.error(f"Current folder: {image_path.parent}")
            logger.error(f"Stuck on file: {image_path.name}")
            send_notification(
                'Image Squisher - Hang Detected',
                f"Script may be hung processing:\n{image_path.parent}\n\nFile: {image_path.name}",
                'Basso'
            )
            print(f"\n⚠ WARNING: Potential hang detected! Check log file for details.")
            print(f"   Current folder: {image_path.parent}")
            print(f"   Stuck on file: {image_path.name}")
            # Continue processing but log the issue
        
        print(f"[{i}/{len(image_files)}] Processing: {image_path.name}", end=' ... ', flush=True)
        logger.info(f"Processing [{i}/{len(image_files)}]: {image_path} (folder: {image_path.parent})")
        
        try:
            process_start = time.time()
            success, format_kept, original_size, final_size = process_image(image_path)
            process_duration = time.time() - process_start
            
            # Update last progress time
            last_progress_time = time.time()
            
            logger.info(f"Completed {image_path.name}: {format_kept} kept, {process_duration:.2f}s")
        
            if success:
                total_original += original_size
                total_final += final_size
                results[format_kept] += 1
                
                savings = original_size - final_size
                savings_pct = (savings / original_size * 100) if original_size > 0 else 0
                
                print(f"{format_kept.upper()} kept ({format_bytes(original_size)} → {format_bytes(final_size)}, "
                      f"-{format_bytes(savings)} / -{savings_pct:.1f}%)")
            else:
                errors += 1
                logger.warning(f"Failed to process {image_path.name}, kept original")
                print(f"ERROR (kept original)")
        except Exception as e:
            errors += 1
            error_msg = f"Exception processing {image_path.name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            logger.error(f"Error in folder: {image_path.parent}")
            print(f"ERROR (kept original)")
            
            # Send notification for exceptions
            send_notification(
                'Image Squisher - Error',
                f"Error processing:\n{image_path.name}\n\nFolder: {image_path.parent}",
                'Basso'
            )
    
    total_duration = time.time() - start_time
    
    print()
    print("=" * 60)
    print("Summary:")
    print(f"  Total images processed: {len(image_files)}")
    print(f"  Successful: {len(image_files) - errors}")
    print(f"  Errors: {errors}")
    print()
    print("  Format distribution:")
    print(f"    Original kept: {results['original']}")
    print(f"    JPEG XL kept: {results['jxl']}")
    print(f"    WebP kept: {results['webp']}")
    print()
    print("  Total size reduction:")
    print(f"    Original total: {format_bytes(total_original)}")
    print(f"    Final total: {format_bytes(total_final)}")
    savings = total_original - total_final
    savings_pct = (savings / total_original * 100) if total_original > 0 else 0
    print(f"    Saved: {format_bytes(savings)} ({savings_pct:.1f}%)")
    print(f"    Duration: {total_duration:.1f} seconds")
    
    # Log summary
    logger.info("=" * 60)
    logger.info(f"Summary: {len(image_files)} processed, {errors} errors, {total_duration:.1f}s")
    logger.info(f"Saved: {format_bytes(savings)} ({savings_pct:.1f}%)")
    
    # Send completion notification
    if errors > 0:
        send_notification(
            'Image Squisher - Completed with Errors',
            f"Processed {len(image_files)} images\n{errors} errors\nSaved: {format_bytes(savings)} ({savings_pct:.1f}%)",
            'Glass'
        )
    else:
        send_notification(
            'Image Squisher - Completed',
            f"Processed {len(image_files)} images\nSaved: {format_bytes(savings)} ({savings_pct:.1f}%)",
            'Ping'
        )
    
    print(f"\nLog file: image-squisher.log")


if __name__ == '__main__':
    main()

