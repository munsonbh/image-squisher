#!/bin/bash
# Setup script for image-squisher
# This script sets up the Python virtual environment and installs dependencies

set -e

echo "=========================================="
echo "Image Squisher - Setup"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 not found. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✓ Found Python $PYTHON_VERSION"
echo ""

# Create venv if it doesn't exist
echo "Setting up virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Created virtual environment"
else
    echo "✓ Virtual environment already exists"
fi

# Activate venv
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip --quiet

# Install core dependencies
echo ""
echo "Installing Python dependencies..."
pip install "Pillow>=10.0.0" --quiet
echo "✓ Installed Pillow"

# Install pillow-heif only on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    pip install "pillow-heif>=0.13.0" --quiet
    echo "✓ Installed pillow-heif (HEIC support)"
else
    echo "⚠ pillow-heif skipped (macOS only)"
fi

# Check for optional dependencies
echo ""
echo "Checking optional dependencies..."

# Check for JPEG XL
if command -v cjxl &> /dev/null || [ -f "/opt/homebrew/bin/cjxl" ] || [ -f "/usr/local/bin/cjxl" ]; then
    echo "✓ JPEG XL support available"
else
    echo "⚠ JPEG XL not found (optional)"
    echo "  Install with: brew install jpeg-xl"
fi

# Check for terminal-notifier
if command -v terminal-notifier &> /dev/null || [ -f "/opt/homebrew/bin/terminal-notifier" ] || [ -f "/usr/local/bin/terminal-notifier" ]; then
    echo "✓ terminal-notifier available (for notifications)"
else
    echo "⚠ terminal-notifier not found (optional)"
    echo "  Install with: brew install terminal-notifier"
fi

echo ""
echo "=========================================="
echo "✓ Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Activate the virtual environment:"
echo "     source venv/bin/activate"
echo ""
echo "  2. (Optional) Install additional dependencies:"
echo "     brew install jpeg-xl libheif terminal-notifier"
echo ""
echo "  3. Run the script:"
echo "     python main.py /path/to/your/images"
echo ""

