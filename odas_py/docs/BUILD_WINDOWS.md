# Building odas_py for Windows

This guide explains how to build the native Windows extension for odas_py.

## Prerequisites

1. **Python 3.7+** for Windows
   - Download from https://www.python.org/downloads/
   - Make sure to install the development files (included by default)
   - Install NumPy: `python -m pip install numpy`

2. **ODAS library built for Windows**
   - See `../odas/BUILD_WINDOWS.md` for instructions
   - You need: `../odas/build-mingw/libodas.dll.a`

3. **Build environment** (choose one):
   - **Option A**: WSL2 with MinGW cross-compiler (easier, recommended)
   - **Option B**: Native Windows with MinGW-w64

---

## Option A: Build from WSL2 (Recommended)

This is the easiest method if you already have WSL2 installed.

### Install Prerequisites in WSL2

```bash
sudo apt update
sudo apt install mingw-w64 cmake build-essential
```

### Run the Build Script

```bash
cd /mnt/c/Users/your_name/path/to/odas_py
bash build_windows_from_wsl.sh
```

The script will:
- ✓ Check all prerequisites
- ✓ Configure CMake for Windows cross-compilation
- ✓ Build `_odas_core.pyd`
- ✓ Copy DLLs to the package
- ✓ Test import with Windows Python

### Output Files

```
odas_py/
  ├── _odas_core.pyd          # Compiled Python extension (235 KB)
  ├── libodas.dll             # ODAS library (2.7 MB)
  └── libwinpthread-1.dll     # MinGW threading library (317 KB)
```

---

## Option B: Build Natively on Windows

### Install MinGW-w64

See `install_mingw_windows.md` for detailed instructions.

Quick version:
1. Download from https://github.com/niXman/mingw-builds-binaries/releases
2. Extract to `C:\mingw64`
3. Add `C:\mingw64\bin` to PATH

### Install CMake

Download from https://cmake.org/download/

### Build

Open PowerShell and run:

```powershell
cd C:\Users\your_name\path\to\odas_py
.\build_windows.ps1
```

Or with custom Python path:

```powershell
.\build_windows.ps1 -PythonPath "C:\Python311\python.exe"
```

---

## Testing

Test that the extension works:

```powershell
python -c "from odas_py import OdasLive; print('Success!')"
```

Test with the C extension:

```powershell
python -c "from odas_py import _odas_core; print(_odas_core.OdasPipeline)"
```

---

## Troubleshooting

### "NumPy not found"
```powershell
python -m pip install numpy
```

### "ODAS library not found"
Build ODAS first following `../odas/BUILD_WINDOWS.md`

### "MinGW not found"
Add MinGW to PATH:
```powershell
$env:PATH = "C:\mingw64\bin;$env:PATH"
```

### "DLL not found" when importing
Make sure these files are in `odas_py/`:
- `_odas_core.pyd`
- `libodas.dll`
- `libwinpthread-1.dll`

### Import works but using "simulation mode"
This means the C extension didn't load. Check:
1. All DLLs are present
2. Python version matches (3.13 in this case)
3. Architecture matches (x64)

---

## For Developers

### Manual Build

If you need more control:

```bash
# From WSL2
cd odas_py
mkdir build-windows && cd build-windows

cmake .. \
  -DCMAKE_SYSTEM_NAME=Windows \
  -DCMAKE_C_COMPILER=x86_64-w64-mingw32-gcc \
  -DCMAKE_CXX_COMPILER=x86_64-w64-mingw32-g++ \
  -DCMAKE_BUILD_TYPE=Release \
  -DPython3_EXECUTABLE=/mnt/c/Python313/python.exe \
  -DPython3_INCLUDE_DIRS=/mnt/c/Python313/include \
  -DPython3_LIBRARIES=/mnt/c/Python313/libs/python313.lib

cmake --build . --config Release -- -j4

# Copy files
cp _odas_core.pyd ../odas_py/
cp ../../odas/build-mingw/bin/libodas.dll ../odas_py/
cp ../../odas/build-mingw/bin/libwinpthread-1.dll ../odas_py/
```

### Technical Notes

- The extension is built for Python 3.13 on Windows x64
- MinGW uses the `posix` thread model
- NumPy's complex number macro `I` conflicts with ODAS headers and is undefined before including ODAS
- CMake automatically converts Windows paths to WSL paths for cross-compilation

---

## Next Steps

Once built, you can use odas_py with your Teensy microphone array:

```python
from odas_py import OdasLive

# Your tetrahedral array geometry
mic_positions = {
    'mic_0': [0.025, 0.025, 0.025],
    'mic_1': [0.025, -0.025, -0.025],
    'mic_2': [-0.025, 0.025, -0.025],
    'mic_3': [-0.025, -0.025, 0.025],
}

processor = OdasLive(mic_positions=mic_positions, n_channels=4)
# Process audio from your Teensy...
```

See `example_quickstart.py` for complete examples.