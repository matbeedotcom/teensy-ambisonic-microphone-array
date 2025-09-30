# ODAS-Py Build Scripts

This directory contains scripts for building ODAS Python bindings on Windows with automatic MinGW setup.

## Automatic MinGW Download

When you run `pip install -e .` on Windows, the setup.py will automatically:

1. Check if MinGW is in PATH
2. If not found, download portable MinGW-w64 (~263MB .zip file)
3. Extract to `../mingw-portable/mingw64/`
4. Use MinGW for compilation (required for ODAS compatibility)

## Manual MinGW Setup

If you want to pre-download MinGW before running pip install:

```bash
# Download portable MinGW (uses .zip format, no external tools needed)
python build-scripts/download_mingw_portable.py --prefer-zip

# Or if you have 7-Zip or py7zr installed (smaller download)
python build-scripts/download_mingw_portable.py
```

This creates:
- `../mingw-portable/mingw64/` - Portable GCC 15.2.0 toolchain
- `build-scripts/toolchain-mingw-portable.cmake` - CMake toolchain file

## Using Your Own MinGW

If you already have MinGW-w64 installed (e.g., from MSYS2), add it to PATH:

```powershell
# Example for MSYS2 MinGW64
$env:PATH = "C:\msys64\mingw64\bin;$env:PATH"
pip install -e .
```

The setup.py will detect it and skip the automatic download.

## Files

- **download_mingw_portable.py** - Downloads and extracts portable MinGW-w64
- **setup_cross_compile.py** - Helper functions for setup.py integration
- **setup_windows_prebuild.py** - Pre-build validation (existing script)

## Requirements

- Python 3.7+
- CMake (install separately: `winget install Kitware.CMake`)
- Internet connection (for automatic MinGW download)

## Troubleshooting

### "MinGW not found and download failed"

The automatic download requires:
- Internet connection
- ~263MB free disk space
- Write permissions to parent directory

Manual workaround:
1. Download MinGW manually from https://winlibs.com/
2. Extract to `../mingw-portable/mingw64/`
3. Or add existing MinGW to PATH

### "Cannot extract .7z file"

If you run the download script manually without `--prefer-zip`:
```bash
pip install py7zr
python build-scripts/download_mingw_portable.py
```

Or use the .zip version:
```bash
python build-scripts/download_mingw_portable.py --prefer-zip
```

### Build fails with MSVC errors

If you see `pthread.h: No such file or directory`, MinGW setup failed and it fell back to MSVC (which is incompatible with ODAS).

Solution:
1. Manually download MinGW: `python build-scripts/download_mingw_portable.py --prefer-zip`
2. Add to PATH and retry:
   ```powershell
   $mingw_bin = (Get-Item ../mingw-portable/mingw64/bin).FullName
   $env:PATH = "$mingw_bin;$env:PATH"
   pip install -e .
   ```

## Why MinGW is Required

ODAS library is built with MinGW and uses pthread (POSIX threads). MSVC (Microsoft's compiler) is incompatible because:
- No pthread.h header
- Different C runtime (MSVCRT vs MinGW's runtime)
- ABI incompatibility

The portable MinGW ensures consistent, reproducible builds across Windows systems.
