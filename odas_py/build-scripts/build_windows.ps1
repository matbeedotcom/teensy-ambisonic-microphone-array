# Build odas_py for Windows using MinGW
# Requires: MinGW-w64, CMake, Python 3.7+

param(
    [string]$PythonPath = "C:\Python313\python.exe",
    [string]$MinGWPath = "C:\mingw64\bin"
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Building odas_py for Windows" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
if (!(Test-Path $PythonPath)) {
    Write-Host "ERROR: Python not found at $PythonPath" -ForegroundColor Red
    Write-Host "Specify path with: -PythonPath <path>" -ForegroundColor Yellow
    exit 1
}
Write-Host "✓ Python found at $PythonPath" -ForegroundColor Green

# Check NumPy
& $PythonPath -c "import numpy" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: NumPy not installed" -ForegroundColor Red
    Write-Host "Install with: $PythonPath -m pip install numpy" -ForegroundColor Yellow
    exit 1
}
Write-Host "✓ NumPy installed" -ForegroundColor Green

# Check MinGW
$gccPath = Join-Path $MinGWPath "gcc.exe"
if (!(Test-Path $gccPath)) {
    Write-Host "ERROR: MinGW not found at $MinGWPath" -ForegroundColor Red
    Write-Host "See install_mingw_windows.md for installation instructions" -ForegroundColor Yellow
    exit 1
}
Write-Host "✓ MinGW found at $MinGWPath" -ForegroundColor Green

# Check ODAS library
if (!(Test-Path "..\odas\build-mingw\libodas.dll.a")) {
    Write-Host "ERROR: ODAS library not built" -ForegroundColor Red
    Write-Host "Please build ODAS first (see ..\odas\BUILD_WINDOWS.md)" -ForegroundColor Yellow
    exit 1
}
Write-Host "✓ ODAS library found" -ForegroundColor Green
Write-Host ""

# Get Python paths
$PythonDir = Split-Path -Parent $PythonPath
$PythonInclude = Join-Path $PythonDir "include"
$PythonLibs = Join-Path $PythonDir "libs"

# Get NumPy include
$NumpyInclude = & $PythonPath -c "import numpy; print(numpy.get_include())"
Write-Host "NumPy include: $NumpyInclude" -ForegroundColor Gray
Write-Host ""

# Add MinGW to PATH
$env:PATH = "$MinGWPath;$env:PATH"

# Clean build directory
if (Test-Path "build-windows") {
    Remove-Item -Recurse -Force "build-windows"
}
New-Item -ItemType Directory -Path "build-windows" | Out-Null
Set-Location "build-windows"

# Configure CMake
Write-Host "Configuring CMake..." -ForegroundColor Cyan
cmake .. `
  -G "MinGW Makefiles" `
  -DCMAKE_BUILD_TYPE=Release `
  -DPython3_EXECUTABLE="$PythonPath" `
  -DPython3_INCLUDE_DIRS="$PythonInclude" `
  -DPython3_LIBRARIES="$PythonLibs\python313.lib" `
  -DNUMPY_INCLUDE_DIR="$NumpyInclude"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: CMake configuration failed" -ForegroundColor Red
    Set-Location ..
    exit 1
}
Write-Host ""

# Build
Write-Host "Building..." -ForegroundColor Cyan
cmake --build . --config Release -- -j4

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Build failed" -ForegroundColor Red
    Set-Location ..
    exit 1
}
Write-Host ""

# Copy files
Write-Host "Copying files to package..." -ForegroundColor Cyan
Copy-Item "_odas_core.pyd" "..\odas_py\"
Copy-Item "..\..\odas\build-mingw\bin\libodas.dll" "..\odas_py\"
Copy-Item "..\..\odas\build-mingw\bin\libwinpthread-1.dll" "..\odas_py\"

Set-Location ..
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Build complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Files in odas_py\:" -ForegroundColor Cyan
Get-ChildItem "odas_py\*.pyd", "odas_py\*.dll" | Format-Table Name, Length
Write-Host ""

# Test import
Write-Host "Testing import..." -ForegroundColor Cyan
$testResult = & $PythonPath -c "import sys; sys.path.insert(0, '.'); from odas_py import OdasLive; print('Success')" 2>&1
if ($testResult -match "Success") {
    Write-Host "✓ Import successful!" -ForegroundColor Green
    Write-Host ""
    Write-Host "🎉 odas_py is ready to use!" -ForegroundColor Green
} else {
    Write-Host "⚠ Import test failed:" -ForegroundColor Yellow
    Write-Host $testResult
}