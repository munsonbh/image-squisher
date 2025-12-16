#!/usr/bin/env python3
"""Image compression tool - losslessly converts images to JPEG XL/WebP and keeps smallest."""

import argparse
import sys
import subprocess
import shutil
import logging
import time
import platform
import threading
from pathlib import Path
from typing import List, Optional, Tuple
from queue import Queue, Empty

from format_detector import scan_folder, detect_formats
from file_manager import process_image
from config_loader import load_config, Config


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


def send_notification(title: str, message: str, sound: str = 'default', enabled: bool = True) -> bool:
    """
    Send a notification (macOS: terminal-notifier, Windows: toast, Linux: notify-send).
    
    Args:
        title: Notification title
        message: Notification message
        sound: Notification sound (macOS only, default: 'default')
        enabled: Whether notifications are enabled
        
    Returns:
        True if notification was sent, False otherwise
    """
    if not enabled:
        return False
    
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


def setup_logging(log_file: Optional[str] = None) -> logging.Logger:
    """
    Set up logging to both file and console.
    
    Args:
        log_file: Path to log file (default: image-squisher.log in current directory)
        
    Returns:
        Configured logger
    """
    if log_file is None:
        log_file = 'image-squisher.log'
    
    log_file = Path(log_file)
    
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
    parser.add_argument(
        '--config',
        type=str,
        help='Path to config file (default: config.json in current directory)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=None,
        help='Number of parallel workers (overrides config.threads, default: number of CPU cores)'
    )
    
    args = parser.parse_args()
    
    folder_path = Path(args.folder)
    
    if not folder_path.exists():
        print(f"Error: Folder '{folder_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
    
    if not folder_path.is_dir():
        print(f"Error: '{folder_path}' is not a directory.", file=sys.stderr)
        sys.exit(1)
    
    # Load configuration
    try:
        config_path = Path(args.config) if args.config else None
        config = load_config(config_path)
    except Exception as e:
        print(f"Warning: Could not load config file: {e}", file=sys.stderr)
        print("Using default configuration.", file=sys.stderr)
        config = Config()
    
    # Set up logging
    logger = setup_logging(config.log_file)
    
    print(f"Scanning folder: {folder_path}")
    # Command-line argument overrides config
    recursive = not args.no_recursive if args.no_recursive else config.recursive
    if recursive:
        print("Mode: Recursive (processing subdirectories)")
    else:
        print("Mode: Top-level only")
    print()
    
    # Scan for images
    image_files = scan_folder(folder_path, recursive=recursive, skip_extensions=config.skip_extensions)
    
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
    
    # Determine number of workers (--workers overrides config.threads)
    import multiprocessing
    if args.workers is not None:
        num_workers = args.workers
    else:
        # Use config.threads if set, otherwise default to CPU count
        if config.threads > 1:
            num_workers = config.threads
        else:
            num_workers = min(multiprocessing.cpu_count(), len(image_files))
    
    if num_workers < 1:
        num_workers = 1
    if num_workers > len(image_files):
        num_workers = len(image_files)
    
    print(f"Using {num_workers} parallel worker(s)")
    print()
    
    # Process images in parallel
    total_original = 0
    total_final = 0
    results = {'original': 0, 'jxl': 0, 'webp': 0}
    errors = 0
    start_time = time.time()
    last_progress_time = time.time()
    hang_timeout = config.hang_timeout
    
    # Thread-safe counters and locks
    results_lock = threading.Lock()
    completed_count = [0]  # Use list for mutable reference
    
    def process_worker(image_queue: Queue, result_queue: Queue):
        """Worker thread that processes images from the queue."""
        while True:
            item = image_queue.get()
            if item is None:  # Poison pill
                break
            
            index, image_path = item
            try:
                success, format_kept, original_size, final_size = process_image(image_path)
                result_queue.put((index, image_path, success, format_kept, original_size, final_size, None))
            except Exception as e:
                # Log exception with full traceback here where exception context exists
                error_msg = f"Exception processing {image_path.name}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                logger.error(f"Error in folder: {image_path.parent}")
                result_queue.put((index, image_path, False, 'original', 0, 0, error_msg))
            finally:
                image_queue.task_done()
    
    if num_workers > 1:
        # Use threading for parallel processing
        image_queue = Queue()
        result_queue = Queue()
        
        # Start worker threads
        workers = []
        for _ in range(num_workers):
            worker = threading.Thread(target=process_worker, args=(image_queue, result_queue))
            worker.daemon = True
            worker.start()
            workers.append(worker)
        
        # Add all images to queue
        for i, image_path in enumerate(image_files):
            image_queue.put((i, image_path))
        
        # Collect results as they complete with hang detection
        results_dict = {}
        hang_check_interval = 60  # Check for hangs every 60 seconds
        last_hang_check = time.time()
        
        while len(results_dict) < len(image_files):
            try:
                # Use timeout to periodically check for hangs
                timeout = min(hang_timeout, hang_check_interval)
                index, image_path, success, format_kept, original_size, final_size, error_msg = result_queue.get(timeout=timeout)
                results_dict[index] = (image_path, success, format_kept, original_size, final_size, error_msg)
                completed_count[0] += 1
                last_progress_time = time.time()
                last_hang_check = time.time()
            except Empty:
                # Timeout occurred - check for potential hang
                current_time = time.time()
                time_since_progress = current_time - last_progress_time
                
                if time_since_progress > hang_timeout:
                    # Potential hang detected
                    # Find which images are still being processed
                    processed_indices = set(results_dict.keys())
                    remaining_indices = [i for i in range(len(image_files)) if i not in processed_indices]
                    
                    if remaining_indices:
                        # Report the first remaining image as potentially stuck
                        stuck_index = remaining_indices[0]
                        stuck_image = image_files[stuck_index]
                        error_msg = f"Potential hang detected! No progress for {time_since_progress:.0f} seconds"
                        logger.error(error_msg)
                        logger.error(f"Current folder: {stuck_image.parent}")
                        logger.error(f"Stuck on file: {stuck_image.name}")
                        logger.error(f"Remaining images: {len(remaining_indices)}")
                        send_notification(
                            'Image Squisher - Hang Detected',
                            f"Script may be hung processing:\n{stuck_image.parent}\n\nFile: {stuck_image.name}\n\nNo progress for {time_since_progress:.0f}s",
                            'Basso',
                            config.enable_notifications
                        )
                        print(f"\n⚠ WARNING: Potential hang detected! Check log file for details.")
                        print(f"   Current folder: {stuck_image.parent}")
                        print(f"   Stuck on file: {stuck_image.name}")
                        print(f"   No progress for {time_since_progress:.0f} seconds")
                        # Reset last_progress_time to avoid spamming notifications
                        last_progress_time = current_time
                
                # Continue waiting for results
                continue
        
        # Stop workers
        for _ in range(num_workers):
            image_queue.put(None)
        for worker in workers:
            worker.join()
        
        # Process results in order
        for i in range(len(image_files)):
            image_path, success, format_kept, original_size, final_size, error_msg = results_dict[i]
            
            print(f"[{i+1}/{len(image_files)}] Processing: {image_path.name}", end=' ... ', flush=True)
            
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
                if error_msg:
                    # Exception was already logged with traceback in worker thread
                    # Just log the error message here (no exc_info since we're outside exception context)
                    logger.error(error_msg)
                    send_notification(
                        'Image Squisher - Error',
                        f"Error processing:\n{image_path.name}\n\nFolder: {image_path.parent}",
                        'Basso',
                        config.enable_notifications
                    )
                else:
                    logger.warning(f"Failed to process {image_path.name}, kept original")
                    send_notification(
                        'Image Squisher - Error',
                        f"Error processing:\n{image_path.name}\n\nFolder: {image_path.parent}",
                        'Basso',
                        config.enable_notifications
                    )
                print(f"ERROR (kept original)")
    else:
        # Single-threaded processing (original behavior)
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
                    'Basso',
                    config.enable_notifications
                )
                print(f"\n⚠ WARNING: Potential hang detected! Check log file for details.")
                print(f"   Current folder: {image_path.parent}")
                print(f"   Stuck on file: {image_path.name}")
                # Continue processing but log the issue
            
            print(f"[{i}/{len(image_files)}] Processing: {image_path.name}", end=' ... ', flush=True)
            
            try:
                process_start = time.time()
                success, format_kept, original_size, final_size = process_image(image_path)
                process_duration = time.time() - process_start
                
                # Update last progress time
                last_progress_time = time.time()
            
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
                    # Send notification for conversion failures
                    send_notification(
                        'Image Squisher - Error',
                        f"Error processing:\n{image_path.name}\n\nFolder: {image_path.parent}",
                        'Basso',
                        config.enable_notifications
                    )
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
                    'Basso',
                    config.enable_notifications
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
    if config.enable_notifications:
        if errors > 0:
            send_notification(
                'Image Squisher - Completed with Errors',
                f"Processed {len(image_files)} images\n{errors} errors\nSaved: {format_bytes(savings)} ({savings_pct:.1f}%)",
                'Glass',
                config.enable_notifications
            )
        else:
            send_notification(
                'Image Squisher - Completed',
                f"Processed {len(image_files)} images\nSaved: {format_bytes(savings)} ({savings_pct:.1f}%)",
                'Ping',
                config.enable_notifications
            )
    
    print(f"\nLog file: {config.log_file}")


if __name__ == '__main__':
    main()

