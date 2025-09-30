#!/bin/bash
# Build ODAS-Py for Windows using MinGW cross-compilation
# Creates a distributable wheel for Windows
# Run from WSL: bash build-scripts/build_release_windows.sh

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJECT_ROOT"

echo "========================================"
echo "Building ODAS-Py for Windows - Release"
echo "========================================"
echo ""

# Check if MinGW is available
if ! command -v x86_64-w64-mingw32-gcc &> /dev/null; then
    echo "ERROR: MinGW toolchain not found!"
    echo "Install with: sudo apt-get install mingw-w64"
    exit 1
fi

# Check if Windows ODAS library exists
ODAS_LIB_PATHS=(
    "../odas/build-release-mingw/lib/libodas.dll.a"
    "../odas/build-mingw/libodas.dll.a"
    "../odas/build-windows/libodas.a"
)

ODAS_FOUND=false
for lib_path in "${ODAS_LIB_PATHS[@]}"; do
    if [ -f "$lib_path" ]; then
        echo "Found ODAS library: $lib_path"
        ODAS_FOUND=true
        break
    fi
done

if [ "$ODAS_FOUND" = false ]; then
    echo ""
    echo "ERROR: ODAS library for Windows not found!"
    echo "Please build ODAS for Windows first:"
    echo "  cd ../odas && bash build-scripts/build_release_mingw.sh"
    exit 1
fi

# Detect Windows Python installation
WINDOWS_PYTHON=""
WIN_PYTHON_PATHS=(
    "/mnt/c/Python312/python.exe"
    "/mnt/c/Python311/python.exe"
    "/mnt/c/Python310/python.exe"
    "/mnt/c/Users/$USER/anaconda3/python.exe"
    "/mnt/c/Users/$USER/AppData/Local/Programs/Python/Python312/python.exe"
    "/mnt/c/Users/$USER/AppData/Local/Programs/Python/Python311/python.exe"
)

for py_path in "${WIN_PYTHON_PATHS[@]}"; do
    if [ -f "$py_path" ]; then
        WINDOWS_PYTHON="$py_path"
        echo "Found Windows Python: $WINDOWS_PYTHON"
        break
    fi
done

if [ -z "$WINDOWS_PYTHON" ]; then
    echo "WARNING: Windows Python not auto-detected"
    echo "Please ensure Python is installed on Windows"
fi

echo ""
echo "========================================"
echo "Cleaning previous builds..."
echo "========================================"
echo ""

# Clean previous builds
rm -rf build-windows/
rm -rf dist-windows/
rm -f odas_py/_odas_core*.pyd

echo ""
echo "========================================"
echo "Building C extension for Windows..."
echo "========================================"
echo ""

# Set environment for MinGW cross-compilation
export CMAKE_BUILD_TYPE=Release

# Build extension
bash build-scripts/build_windows_from_wsl.sh

# Verify extension was built
if [ -f odas_py/_odas_core*.pyd ]; then
    echo ""
    echo "Extension built successfully:"
    ls -lh odas_py/_odas_core*.pyd
else
    echo ""
    echo "ERROR: Extension build failed - no .pyd file found"
    exit 1
fi

echo ""
echo "========================================"
echo "Creating Windows distribution..."
echo "========================================"
echo ""

# Create dist directory structure
mkdir -p dist-windows/odas_py

# Copy built extension to package directory
cp odas_py/_odas_core*.pyd dist-windows/odas_py/

# Copy Python package files
cp -r odas_py/*.py dist-windows/odas_py/

# Copy DLLs to package directory (they need to be with the .pyd)
if [ -f odas_py/libodas.dll ]; then
    cp odas_py/libodas.dll dist-windows/odas_py/
fi
if [ -f odas_py/libfftw3f-3.dll ]; then
    cp odas_py/libfftw3f-3.dll dist-windows/odas_py/
fi
if [ -f odas_py/libconfig.dll ]; then
    cp odas_py/libconfig.dll dist-windows/odas_py/
fi
if [ -f odas_py/libwinpthread-1.dll ]; then
    cp odas_py/libwinpthread-1.dll dist-windows/odas_py/
fi

# Copy examples if they exist
if [ -d "examples" ]; then
    cp -r examples dist-windows/
fi

# Copy documentation files if they exist
for file in README.md LICENSE requirements.txt; do
    if [ -f "$file" ]; then
        cp "$file" dist-windows/
    fi
done

# Copy docs directory if it exists
if [ -d "docs" ]; then
    cp -r docs dist-windows/
fi

# Also copy DLLs to root for convenience
if [ -f ../odas/dist-windows/lib/libodas.dll ]; then
    echo "Copying additional ODAS DLL to root..."
    cp ../odas/dist-windows/lib/libodas.dll dist-windows/
fi

if [ -f ../odas/fftw-mingw-build/install/bin/libfftw3f-3.dll ]; then
    echo "Copying additional FFTW DLL to root..."
    cp ../odas/fftw-mingw-build/install/bin/libfftw3f-3.dll dist-windows/
fi

echo ""
echo "========================================"
echo "Build Summary"
echo "========================================"
echo ""

echo "Windows distribution created:"
echo "-----------------------------"
find dist-windows/ -type f | sort

echo ""
echo "Extension info:"
ls -lh dist-windows/_odas_core*.pyd

echo ""
echo "========================================"
echo "Windows Release Build Complete!"
echo "========================================"
echo ""
echo "Distribution directory: $PROJECT_ROOT/dist-windows/"
echo ""
echo "To create a zip for distribution:"
echo "  cd $PROJECT_ROOT"
echo "  zip -r odas-py-windows-x64.zip dist-windows/"
echo ""
echo "To test on Windows:"
echo "  1. Copy dist-windows/ to Windows"
echo "  2. cd dist-windows"
echo "  3. python -c \"from _odas_core import *; print('Success!')\""
echo "  4. python examples/example_quickstart.py"
echo ""
