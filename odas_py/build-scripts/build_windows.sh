#!/bin/bash
# Build odas_py for Windows using MinGW cross-compiler from WSL2
# Run from odas_py root directory: bash build-scripts/build_windows.sh

set -e

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJECT_ROOT"

# Paths
ODAS_ROOT="../odas"
ODAS_BUILD_MINGW="${ODAS_ROOT}/build-mingw"
WIN_PYTHON="/mnt/c/Python313"
BUILD_DIR="build-windows"

# Get NumPy include path from Windows Python
NUMPY_INCLUDE=$(${WIN_PYTHON}/python.exe -c "import numpy; print(numpy.get_include())" | tr -d '\r')
# Convert Windows path to WSL path
NUMPY_INCLUDE_WSL=$(wslpath "${NUMPY_INCLUDE}")

echo "Building odas_py for Windows..."
echo "ODAS MinGW Build: ${ODAS_BUILD_MINGW}"
echo "Python: ${WIN_PYTHON}"
echo "NumPy Include: ${NUMPY_INCLUDE_WSL}"

# Clean build directory
rm -rf ${BUILD_DIR}
mkdir -p ${BUILD_DIR}
cd ${BUILD_DIR}

# Run CMake with explicit paths
cmake .. \
  -DCMAKE_SYSTEM_NAME=Windows \
  -DCMAKE_C_COMPILER=x86_64-w64-mingw32-gcc \
  -DCMAKE_CXX_COMPILER=x86_64-w64-mingw32-g++ \
  -DCMAKE_BUILD_TYPE=Release \
  -DPython3_EXECUTABLE=${WIN_PYTHON}/python.exe \
  -DPython3_INCLUDE_DIRS=${WIN_PYTHON}/include \
  -DPython3_LIBRARIES=${WIN_PYTHON}/libs/python313.lib \
  -DNUMPY_INCLUDE_DIR=${NUMPY_INCLUDE_WSL}

# Build
cmake --build . --config Release -- -j4

echo ""
echo "Build complete!"
echo "Output: odas_py/_odas_core.pyd"
echo ""
echo "Required DLLs (copy to odas_py/):"
echo "  - ${ODAS_BUILD_MINGW}/bin/libodas.dll"
echo "  - ${ODAS_BUILD_MINGW}/bin/libwinpthread-1.dll"