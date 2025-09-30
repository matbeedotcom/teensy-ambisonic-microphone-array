#!/bin/bash
# Build ODAS-Py Python bindings in Release mode
# Creates a distributable wheel package
# Run from odas_py root: bash build-scripts/build_release.sh

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJECT_ROOT"

echo "========================================"
echo "Building ODAS-Py - Release Mode"
echo "========================================"
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $PYTHON_VERSION"

# Check if ODAS library exists
ODAS_LIB_PATHS=(
    "../odas/build-release/lib/libodas.so"
    "../odas/build/lib/libodas.so"
    "../odas/build/libodas.a"
    "../odas/build-mingw/libodas.a"
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
    echo "ERROR: ODAS library not found!"
    echo "Please build ODAS first:"
    echo "  cd ../odas && bash build-scripts/build_release.sh"
    echo "  or: cd ../odas && bash build-scripts/build_mingw.sh"
    exit 1
fi

echo ""
echo "========================================"
echo "Installing build dependencies..."
echo "========================================"
echo ""

# Install/upgrade build tools
pip install --upgrade pip setuptools wheel build

# Install package dependencies
pip install -r requirements.txt

echo ""
echo "========================================"
echo "Cleaning previous builds..."
echo "========================================"
echo ""

# Clean previous builds
rm -rf build/
rm -rf dist/
rm -rf *.egg-info
rm -f odas_py/_odas_core*.so
rm -f odas_py/_odas_core*.pyd
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

echo ""
echo "========================================"
echo "Building C extension (Release)..."
echo "========================================"
echo ""

# Build extension with release optimizations
CMAKE_BUILD_TYPE=Release python3 setup.py build_ext --inplace

# Verify extension was built
if [ -f odas_py/_odas_core*.so ] || [ -f odas_py/_odas_core*.pyd ]; then
    echo ""
    echo "Extension built successfully:"
    ls -lh odas_py/_odas_core* | grep -E '\.(so|pyd)$'
else
    echo ""
    echo "ERROR: Extension build failed - no .so or .pyd file found"
    exit 1
fi

echo ""
echo "========================================"
echo "Preparing package files..."
echo "========================================"
echo ""

# Create README.md if it doesn't exist (use docs/README.md as fallback)
if [ ! -f "README.md" ]; then
    if [ -f "docs/README.md" ]; then
        echo "Copying README.md from docs/"
        cp docs/README.md .
    fi
fi

echo ""
echo "========================================"
echo "Creating distribution packages..."
echo "========================================"
echo ""

# Build source distribution and wheel
python3 -m build

echo ""
echo "========================================"
echo "Build Summary"
echo "========================================"
echo ""

# Show what was built
echo "Distribution packages created:"
echo "------------------------------"
ls -lh dist/

echo ""
echo "Wheel contents:"
echo "---------------"
unzip -l dist/*.whl | grep -E '(_odas_core|\.py$)' | head -20

echo ""
echo "Package info:"
echo "-------------"
pip show odas-py 2>/dev/null || echo "(Install with: pip install dist/*.whl)"

echo ""
echo "========================================"
echo "Release Build Complete!"
echo "========================================"
echo ""
echo "Distribution files:"
find dist/ -type f | sort

echo ""
echo "To install the wheel:"
echo "  pip install dist/odas_py-*.whl"
echo ""
echo "To upload to PyPI (after testing):"
echo "  pip install twine"
echo "  twine upload dist/*"
echo ""
echo "To test the package:"
echo "  python3 -c 'from odas_py import OdasLive; print(OdasLive)'"
echo "  python3 examples/example_quickstart.py"
echo ""
