#!/bin/bash
# Build script for ODAS-Py
# Run from odas_py root directory: bash build-scripts/build.sh

set -e

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJECT_ROOT"

echo "=================================="
echo "Building ODAS-Py"
echo "=================================="

# Check if ODAS library exists
ODAS_LIB="../odas/build/libodas.a"
ODAS_LIB_MINGW="../odas/build-mingw/libodas.a"

if [ ! -f "$ODAS_LIB" ] && [ ! -f "$ODAS_LIB_MINGW" ]; then
    echo "Error: ODAS library not found!"
    echo "Please build ODAS first:"
    echo "  cd ../odas && mkdir build && cd build && cmake .. && make"
    echo "  or for Windows: cd ../odas && bash build_mingw.sh"
    exit 1
fi

# Clean previous build
echo "Cleaning previous build..."
rm -rf build/
rm -f odas_py/_odas_core*.so
rm -f odas_py/_odas_core*.pyd

# Build extension
echo "Building C extension..."
python3 setup.py build_ext --inplace

echo ""
echo "=================================="
echo "Build complete!"
echo "=================================="
echo ""
echo "To install in development mode:"
echo "  pip install -e ."
echo ""
echo "To test:"
echo "  python3 -c 'from odas_py import OdasProcessor; print(OdasProcessor)'"
echo "  python3 examples/basic_usage.py"