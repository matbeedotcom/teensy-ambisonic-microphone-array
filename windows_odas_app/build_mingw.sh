#!/bin/bash
# Build script for MinGW cross-compilation from WSL2 to Windows

echo "Building Tetrahedral Microphone Array ODAS Application for Windows..."

# Clean any previous build
rm -rf build

# Set up fresh build directory
mkdir -p build
cd build

# Configure with CMake for MinGW cross-compilation
echo "Configuring project with CMake for MinGW cross-compilation..."
cmake -DCMAKE_SYSTEM_NAME=Windows \
      -DCMAKE_C_COMPILER=x86_64-w64-mingw32-gcc \
      -DCMAKE_CXX_COMPILER=x86_64-w64-mingw32-g++ \
      -DCMAKE_RC_COMPILER=x86_64-w64-mingw32-windres \
      -DCMAKE_FIND_ROOT_PATH=/usr/x86_64-w64-mingw32 \
      -DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER \
      -DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=ONLY \
      -DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY \
      ..

if [ $? -ne 0 ]; then
    echo "CMake configuration failed"
    exit 1
fi

# Build the project
echo "Building project..."
make -j$(nproc)
if [ $? -ne 0 ]; then
    echo "Build failed"
    exit 1
fi

echo "Build completed successfully!"
echo "Windows executable: build/tetrahedral_mic_array.exe"

# Copy required DLLs to the bin directory
cp ../lib/libodas.dll bin/
cp ../../odas/fftw-mingw-build/install/bin/libfftw3f-3.dll bin/

echo "DLL copied to build directory"

cd ..