#!/bin/bash
# Build odas_py for Windows using MinGW cross-compiler from WSL2
# This creates a native Windows .pyd extension that works with Windows Python
# Run from odas_py root directory: bash build-scripts/build_windows_from_wsl.sh

set -e

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJECT_ROOT"

echo "========================================"
echo "Building odas_py for Windows"
echo "========================================"
echo ""

# Check prerequisites
if ! command -v x86_64-w64-mingw32-gcc &> /dev/null; then
    echo "ERROR: MinGW cross-compiler not found!"
    echo "Install with: sudo apt install mingw-w64"
    exit 1
fi

if [ ! -f "/mnt/c/Python313/python.exe" ]; then
    echo "ERROR: Windows Python not found at /mnt/c/Python313/python.exe"
    echo "Please adjust the WINDOWS_PYTHON variable in this script"
    exit 1
fi

# Configuration
WINDOWS_PYTHON="/mnt/c/Users/mail/anaconda3/python.exe"
ODAS_ROOT="../odas"
BUILD_DIR="build-windows"

echo "Checking Python and NumPy..."
if ! $WINDOWS_PYTHON -c "import numpy" 2>/dev/null; then
    echo "ERROR: NumPy not installed in Windows Python"
    echo "Install with: $WINDOWS_PYTHON -m pip install numpy"
    exit 1
fi
echo "✓ Windows Python with NumPy found"
echo ""

# Check ODAS library
if [ ! -f "${ODAS_ROOT}/build-mingw/libodas.dll.a" ]; then
    echo "ERROR: ODAS MinGW library not found!"
    echo "Expected: ${ODAS_ROOT}/build-mingw/libodas.dll.a"
    echo "Please build ODAS for Windows first (see odas/BUILD_WINDOWS.md)"
    exit 1
fi
echo "✓ ODAS MinGW library found"
echo ""

# Check FFTW3
if [ ! -f "${ODAS_ROOT}/fftw-mingw-build/install/include/fftw3.h" ]; then
    echo "ERROR: FFTW3 headers not found!"
    echo "Expected: ${ODAS_ROOT}/fftw-mingw-build/install/include/fftw3.h"
    exit 1
fi
echo "✓ FFTW3 headers found"
echo ""

# Clean build directory
echo "Cleaning build directory..."
rm -rf ${BUILD_DIR}
mkdir -p ${BUILD_DIR}
cd ${BUILD_DIR}

# Get Python paths
PYTHON_VERSION=$($WINDOWS_PYTHON -c "import sys; print(f'{sys.version_info.major}{sys.version_info.minor}')")
PYTHON_PREFIX=$($WINDOWS_PYTHON -c "import sys; import os; print(sys.prefix.replace(os.sep, '/'))" | tr -d '\r')
# Convert Windows path to WSL path
PYTHON_PREFIX_WSL=$(echo "$PYTHON_PREFIX" | sed 's|C:|/mnt/c|I' | sed 's|\\|/|g')
PYTHON_INCLUDE="${PYTHON_PREFIX_WSL}/include"
PYTHON_LIB="${PYTHON_PREFIX_WSL}/libs/python${PYTHON_VERSION}.lib"

echo "Python version: ${PYTHON_VERSION}"
echo "Python prefix: ${PYTHON_PREFIX_WSL}"
echo "Python include: ${PYTHON_INCLUDE}"
echo "Python library: ${PYTHON_LIB}"
echo ""

# Configure with CMake
echo "Configuring CMake for Windows cross-compilation..."
cmake .. \
  -DCMAKE_SYSTEM_NAME=Windows \
  -DCMAKE_C_COMPILER=x86_64-w64-mingw32-gcc \
  -DCMAKE_CXX_COMPILER=x86_64-w64-mingw32-g++ \
  -DCMAKE_RC_COMPILER=x86_64-w64-mingw32-windres \
  -DCMAKE_BUILD_TYPE=Release \
  -DPython3_EXECUTABLE=${WINDOWS_PYTHON} \
  -DPython3_INCLUDE_DIRS=${PYTHON_INCLUDE} \
  -DPython3_LIBRARIES=${PYTHON_LIB}

if [ $? -ne 0 ]; then
    echo "ERROR: CMake configuration failed!"
    exit 1
fi
echo ""

# Build
echo "Building Windows extension..."
cmake --build . --config Release -- -j4

if [ $? -ne 0 ]; then
    echo "ERROR: Build failed!"
    exit 1
fi
echo ""

# Copy files to package
echo "Copying files to odas_py package..."
cp _odas_core.pyd ../odas_py/
cp ../../odas/build-mingw/bin/libodas.dll ../odas_py/ || echo "Warning: libodas.dll not found"
cp ../../odas/build-mingw/bin/libwinpthread-1.dll ../odas_py/ || echo "Warning: libwinpthread-1.dll not found"

# Also copy libconfig.dll if it exists (might be needed)
if [ -f "../../odas/build-mingw/bin/libconfig.dll" ]; then
    cp ../../odas/build-mingw/bin/libconfig.dll ../odas_py/
fi

cd ..
echo ""
echo "========================================"
echo "Build complete!"
echo "========================================"
echo ""
echo "Files created in odas_py/:"
ls -lh odas_py/*.{pyd,dll} 2>/dev/null
echo ""
echo "Testing Windows Python import..."
if $WINDOWS_PYTHON -c "import sys; sys.path.insert(0, '.'); from odas_py import OdasLive; print('✓ Success! OdasLive imported from Windows Python')" 2>&1; then
    echo ""
    echo "🎉 All done! odas_py is ready to use in Windows"
else
    echo ""
    echo "⚠ Warning: Import test failed. You may need to install dependencies:"
    echo "  $WINDOWS_PYTHON -m pip install numpy"
fi