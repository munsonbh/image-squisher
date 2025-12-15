# Image Squisher

A cross-platform image compression tool that losslessly converts images to JPEG XL and WebP formats, then keeps only the smallest file of the three. Perfect for optimizing image storage without any quality loss. Not perfect for keeping images exactly how they are.

**Supports:** macOS, Windows, and Linux

## ⚠️ Important Warnings

**⚠️ EXPERIMENTAL SOFTWARE**: This tool is currently experimental and should **NOT** be used on important files without backups. While the code includes safety measures (atomic file operations, verification, etc.), there is always a risk when modifying files. **Always backup your images before use.**

**⚠️ WINDOWS TESTING**: This tool has **NOT been tested on Windows**. While the code has been made cross-platform compatible, Windows users should test on non-critical files first and report any issues.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/image-squisher.git
cd image-squisher

# Run setup (creates venv and installs dependencies)
chmod +x setup.sh
./setup.sh

# Activate virtual environment
source venv/bin/activate

# (Optional) Install JPEG XL support for better compression
brew install jpeg-xl

# Run on your images
python main.py /path/to/your/images
```

**That's it!** The script will process all images recursively and keep the smallest file format.

## Features

- **Lossless compression**: Converts images to JPEG XL and WebP without any quality loss
- **Automatic format selection**: Keeps the smallest file (original, JPEG XL, or WebP)
- **Format detection**: Automatically detects and reports image formats in your folder
- **Safe file operations**: Uses atomic file replacement to prevent corruption
- **Metadata stripping**: Removes EXIF and other metadata to maximize compression
- **Recursive processing**: Optional recursive directory scanning

## Requirements

- **Python 3.8+** (3.9+ recommended)
- **macOS, Windows, or Linux**
- **Homebrew** (macOS, for optional JPEG XL support)

### Optional Dependencies

**macOS:**
- **JPEG XL support**: `brew install jpeg-xl` (enables JPEG XL compression)
- **HEIC support**: `brew install libheif` (for HEIC/HEIF files)
- **Notifications**: `brew install terminal-notifier` (for hang/error notifications)

**Windows:**
- **JPEG XL support**: Download from [libjxl releases](https://github.com/libjxl/libjxl/releases) or use `winget install libjxl` (if available)
- **Notifications**: Built-in Windows toast notifications (automatic)
- **Note**: HEIC/HEIF support not available on Windows (pillow-heif is macOS-only)

**Linux:**
- **JPEG XL support**: `apt install libjxl-tools` (Debian/Ubuntu) or equivalent
- **Notifications**: `notify-send` (usually pre-installed)

## Installation

### macOS Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/image-squisher.git
   cd image-squisher
   ```

2. **Run the setup script:**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

3. **Activate the virtual environment:**
   ```bash
   source venv/bin/activate
   ```

4. **Install optional dependencies (recommended):**
   ```bash
   brew install jpeg-xl libheif terminal-notifier
   ```

### Windows Setup

1. **Clone the repository:**
   ```cmd
   git clone https://github.com/yourusername/image-squisher.git
   cd image-squisher
   ```

2. **Run the setup script:**
   ```cmd
   setup.bat
   ```

3. **Activate the virtual environment:**
   ```cmd
   venv\Scripts\activate
   ```

4. **Install optional JPEG XL support:**
   - Download from [libjxl releases](https://github.com/libjxl/libjxl/releases)
   - Extract and add to PATH, or place `cjxl.exe` in a location in your PATH

### Linux Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/image-squisher.git
   cd image-squisher
   ```

2. **Create virtual environment and install:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Install optional dependencies:**
   ```bash
   # Debian/Ubuntu
   sudo apt install libjxl-tools
   
   # Or build from source: https://github.com/libjxl/libjxl
   ```

### Manual Setup (All Platforms)

```bash
# Create virtual environment
python3 -m venv venv  # Windows: python -m venv venv

# Activate
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Note: On Windows, pillow-heif will be skipped (macOS only)
```

## Usage

### Basic Usage

Process images recursively (default - processes all subdirectories):
```bash
python main.py /path/to/images
```

Process only top-level folder:
```bash
python main.py /path/to/images --no-recursive
```

Process with custom number of parallel workers (default: number of CPU cores):
```bash
python main.py /path/to/images --workers 4
```

### Features

- **Automatic format detection**: Scans and reports all image formats found
- **Smart compression**: Only keeps converted files if they're at least 5% smaller
- **Parallel processing**: Processes multiple images concurrently (default: number of CPU cores)
- **Parallel conversions**: Converts to JPEG XL and WebP simultaneously for each image
- **Optimized compression**: Uses balanced compression settings for faster processing
- **Skip optimized files**: Automatically skips files already in JXL or WebP format
- **Progress tracking**: Real-time progress with file-by-file updates
- **Hang detection**: Automatically detects if processing stalls (5+ minutes)
- **Error notifications**: macOS notifications for errors and hangs (requires terminal-notifier)
- **Detailed logging**: All activity logged to `image-squisher.log`

## How It Works

1. **Scans** the specified folder for image files (recursively by default)
2. **For each image (processed in parallel):**
   - Skips files already in JXL or WebP format
   - Converts to JPEG XL and WebP **simultaneously** (lossless, optimized compression) - if available
   - Compares file sizes of original, JPEG XL, and WebP
   - **Only keeps converted file if it's at least 5% smaller** (preserves originals for minimal gains)
   - Deletes temporary files
3. **Reports** detailed statistics on compression results
4. **Logs** all activity to `image-squisher.log` for troubleshooting

### Performance Optimizations

- **Parallel image processing**: Multiple images processed concurrently (default: CPU core count)
- **Parallel format conversion**: JPEG XL and WebP conversions run simultaneously for each image
- **Optimized compression settings**: Uses effort level 7 for JPEG XL and method 4 for WebP (faster than maximum with minimal size difference)
- **Smart skipping**: Automatically skips files already in optimized formats

### Special Handling

- **Animated GIFs**: Converted to animated WebP (often 25-50% smaller)
- **Static images**: Converted to JPEG XL and WebP, smallest kept
- **Files that don't compress well**: Original format preserved

## Supported formats

The tool can process images in these formats:
- PNG, JPEG, TIFF, BMP, GIF
- WebP, AVIF, JPEG XL
- HEIC/HEIF (macOS)
- And other formats supported by Pillow

## Safety Features

- ✅ **Atomic file operations**: Files written to temp locations first, then atomically replaced
- ✅ **Verification**: Original files only replaced after successful conversion and verification
- ✅ **Error handling**: If conversion fails, original file is always kept
- ✅ **5% threshold**: Only replaces original if converted file is at least 5% smaller
- ✅ **Metadata stripping**: Removes EXIF and other metadata for maximum compression
- ✅ **Hang detection**: Monitors progress and alerts if processing stalls
- ✅ **Detailed logging**: All operations logged for troubleshooting

**⚠️ Remember**: Despite these safety features, this is experimental software. Always backup important files before use.

## Troubleshooting

### Check the Log File

If something goes wrong, check `image-squisher.log` for detailed information:
```bash
tail -f image-squisher.log
```

### Common Issues

**"JPEG XL support not available"**
- Install: `brew install jpeg-xl`
- The app works fine with WebP only if JPEG XL isn't available

**"HEIC files not processing"**
- macOS: Install `brew install libheif`
- Windows/Linux: HEIC support not available (pillow-heif is macOS-only)

**Script appears to hang**
- Check `image-squisher.log` for the last processed file and folder
- The script will send a notification if terminal-notifier is installed
- Large animated GIFs or very large images may take several minutes

**Notifications not working**
- Install: `brew install terminal-notifier`
- Notifications are optional - the script works without them

## Example output

```
Scanning folder: /Users/example/photos
Mode: Recursive (processing subdirectories)

Found 25 image file(s)
Formats detected: .heic, .jpg, .png

[1/25] Processing: IMG_001.HEIC ... JXL kept (3.45 MB → 2.12 MB, -1.33 MB / -38.6%)
[2/25] Processing: photo.png ... WEBP kept (1.23 MB → 856.34 KB, -373.66 KB / -29.7%)
...

Summary:
  Total images processed: 25
  Successful: 25
  Errors: 0

  Format distribution:
    Original kept: 3
    JPEG XL kept: 15
    WebP kept: 7

  Total size reduction:
    Original total: 45.67 MB
    Final total: 28.34 MB
    Saved: 17.33 MB (38.0%)
    Duration: 45.2 seconds

Log file: image-squisher.log
```

## Development

### Project Structure

```
image-squisher/
├── main.py              # CLI entry point
├── format_detector.py   # Image format detection and scanning
├── processor.py         # Image conversion (JPEG XL, WebP)
├── file_manager.py      # Safe file operations and size comparison
├── requirements.txt     # Python dependencies
├── setup.sh            # Automated setup script
├── Makefile            # Convenience commands
└── README.md           # This file
```

### Using Makefile

```bash
make setup      # Run automated setup
make install    # Install dependencies (venv must be activated)
make clean      # Remove venv and log files
make run FOLDER=/path/to/images  # Run the script
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- Uses [Pillow](https://python-pillow.org/) for image processing
- Uses [libjxl](https://github.com/libjxl/libjxl) for JPEG XL compression
- Uses [terminal-notifier](https://github.com/julienXX/terminal-notifier) for macOS notifications

