@echo off
REM Build script for Windows ODAS application

echo Building Tetrahedral Microphone Array ODAS Application...

REM Set up build directory
if not exist "build" mkdir build
cd build

REM Configure with CMake
echo Configuring project with CMake...
cmake -G "MinGW Makefiles" ..
if %errorlevel% neq 0 (
    echo CMake configuration failed
    exit /b 1
)

REM Build the project
echo Building project...
cmake --build .
if %errorlevel% neq 0 (
    echo Build failed
    exit /b 1
)

echo Build completed successfully!
echo Executable: build/tetrahedral_mic_array.exe

cd ..