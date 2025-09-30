# Installing MinGW-w64 on Windows

## Download MinGW-w64

1. Go to: https://github.com/niXman/mingw-builds-binaries/releases
2. Download: **x86_64-13.2.0-release-posix-seh-msvcrt-rt_v11-rev0.7z**
   (or latest x86_64-*-posix-seh-msvcrt version)

## Extract

1. Extract the `.7z` file (use 7-Zip if needed)
2. Move the `mingw64` folder to `C:\mingw64`
   - Should have: `C:\mingw64\bin\gcc.exe`

## Add to PATH

### Option 1: PowerShell (Permanent)
```powershell
[Environment]::SetEnvironmentVariable(
    "Path",
    "C:\mingw64\bin;" + [Environment]::GetEnvironmentVariable("Path", "User"),
    "User"
)
```

### Option 2: Manually
1. Search Windows for "Environment Variables"
2. Click "Environment Variables"
3. Under "User variables", select "Path"
4. Click "Edit"
5. Click "New"
6. Add: `C:\mingw64\bin`
7. Click "OK" on all dialogs

## Verify Installation

**Close and reopen PowerShell**, then:

```powershell
gcc --version
# Should show: gcc (x86_64-posix-seh-rev0, Built by MinGW-W64 project) 13.2.0

g++ --version
mingw32-make --version
```

## Build Python Extension

```powershell
cd C:\Users\mail\dev\personal\teensy_ambisonic_microphone\odas_py
rm -r -fo build
python setup.py build_ext --inplace
```

You should see:
```
Using MinGW: C:\mingw64\bin\gcc.exe
...
[100%] Built target _odas_core
```

## Test

```powershell
python -c "from odas_py import OdasLive; print('Success!')"
```