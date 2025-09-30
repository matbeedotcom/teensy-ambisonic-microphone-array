#!/bin/bash
# Package ODAS-Py for distribution
# Creates distributable archives for the current platform
# Run from odas_py root: bash build-scripts/package_release.sh

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJECT_ROOT"

echo "========================================"
echo "Packaging ODAS-Py for Distribution"
echo "========================================"
echo ""

# Get version from version.py
VERSION=$(python3 -c "from odas_py.version import __version__; print(__version__)" 2>/dev/null || echo "1.0.0")
echo "Version: $VERSION"

# Detect platform
PLATFORM="$(uname -s)"
ARCH="$(uname -m)"

case "${PLATFORM}" in
    Linux*)     PLATFORM_NAME="linux";;
    Darwin*)    PLATFORM_NAME="macos";;
    CYGWIN*)    PLATFORM_NAME="windows";;
    MINGW*)     PLATFORM_NAME="windows";;
    MSYS*)      PLATFORM_NAME="windows";;
    *)          PLATFORM_NAME="unknown";;
esac

PACKAGE_NAME="odas-py-${VERSION}-${PLATFORM_NAME}-${ARCH}"
PACKAGE_DIR="dist-release"

echo "Platform: ${PLATFORM_NAME}-${ARCH}"
echo "Package name: ${PACKAGE_NAME}"
echo ""

# Create package directory
mkdir -p "$PACKAGE_DIR"
cd "$PACKAGE_DIR"

echo "========================================"
echo "Copying files..."
echo "========================================"
echo ""

# Create package structure
mkdir -p "${PACKAGE_NAME}"
cd "${PACKAGE_NAME}"

# Copy Python package
cp -r ../../odas_py .

# Copy examples
if [ -d "../../examples" ]; then
    cp -r ../../examples .
fi

# Copy documentation
for file in ../../docs/*.md; do
    if [ -f "$file" ]; then
        cp "$file" .
    fi
done

# Copy root-level docs
for file in ../../README.md ../../LICENSE ../../requirements.txt ../../CLAUDE.md; do
    if [ -f "$file" ]; then
        cp "$file" .
    fi
done

# Create distribution README
cat > INSTALL.txt << 'EOF'
ODAS-Py Distribution Package
=============================

This package contains pre-built ODAS-Py bindings for your platform.

Installation
------------

1. Install Python dependencies:
   pip install -r requirements.txt

2. Copy the odas_py directory to your Python path, or:
   python -c "import sys; import os; sys.path.insert(0, os.getcwd()); from odas_py import OdasLive; print(OdasLive)"

3. Test the installation:
   python examples/example_quickstart.py

Usage
-----

from odas_py import OdasLive

# Create processor
processor = OdasLive(
    nChannels=4,
    sampleRate=44100,
    frameSize=512,
    mics={
        "mic_0": [0.043, 0.0, 0.025],
        "mic_1": [-0.043, 0.0, 0.025],
        "mic_2": [0.0, 0.043, -0.025],
        "mic_3": [0.0, -0.043, -0.025]
    }
)

# Set audio source
processor.set_source_pyaudio(device_index=0)

# Set result callback
def ssl_callback(pots):
    for pot in pots:
        print(f"Direction: ({pot['x']:.2f}, {pot['y']:.2f}, {pot['z']:.2f}), Energy: {pot['E']:.4f}")

processor.set_ssl_callback(ssl_callback)

# Start processing
processor.start()

# Process for 30 seconds
import time
time.sleep(30)

# Stop
processor.stop()

Documentation
-------------

See README.md and the docs in this package for detailed documentation.

Troubleshooting
---------------

If you get import errors:
- Ensure all DLLs (.dll, .so) are in the same directory as the Python extension
- Check that your Python version is compatible (3.7+)
- Verify dependencies are installed: pip install -r requirements.txt

For more help, see BUILD.md

EOF

cd ..

echo "Creating archive..."

# Create archive (tar.gz for Unix, zip for Windows)
if [ "$PLATFORM_NAME" = "windows" ]; then
    zip -r "${PACKAGE_NAME}.zip" "${PACKAGE_NAME}"
    ARCHIVE_FILE="${PACKAGE_NAME}.zip"
else
    tar -czf "${PACKAGE_NAME}.tar.gz" "${PACKAGE_NAME}"
    ARCHIVE_FILE="${PACKAGE_NAME}.tar.gz"
fi

# Calculate size and checksum
ARCHIVE_SIZE=$(du -h "$ARCHIVE_FILE" | cut -f1)
if command -v sha256sum &> /dev/null; then
    CHECKSUM=$(sha256sum "$ARCHIVE_FILE" | cut -d' ' -f1)
elif command -v shasum &> /dev/null; then
    CHECKSUM=$(shasum -a 256 "$ARCHIVE_FILE" | cut -d' ' -f1)
else
    CHECKSUM="(checksum tool not found)"
fi

echo ""
echo "========================================"
echo "Package Summary"
echo "========================================"
echo ""
echo "Archive: $ARCHIVE_FILE"
echo "Size: $ARCHIVE_SIZE"
echo "SHA256: $CHECKSUM"
echo ""
echo "Contents:"
find "${PACKAGE_NAME}" -type f | head -20
echo "... (and more)"

echo ""
echo "========================================"
echo "Packaging Complete!"
echo "========================================"
echo ""
echo "Distribution package: $PROJECT_ROOT/$PACKAGE_DIR/$ARCHIVE_FILE"
echo ""
echo "To test:"
if [ "$PLATFORM_NAME" = "windows" ]; then
    echo "  unzip $ARCHIVE_FILE"
else
    echo "  tar -xzf $ARCHIVE_FILE"
fi
echo "  cd ${PACKAGE_NAME}"
echo "  python3 -c 'from odas_py import OdasLive; print(OdasLive)'"
echo ""
