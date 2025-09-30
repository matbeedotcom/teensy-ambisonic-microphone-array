# ODAS-Py Build Status

## What We've Created

A complete Python bindings package for ODAS with the following structure:

### Files Created
```
odas_py/
├── setup.py                    # Python package setup with CMake
├── CMakeLists.txt              # CMake build configuration
├── README.md                   # Full documentation
├── BUILD.md                    # Detailed build instructions
├── QUICKSTART.md               # Quick start guide
├── requirements.txt            # Python dependencies
├── build.sh                    # Build script (needs line ending fix)
├── test_structure.py           # Structure validation script
├── .gitignore                  # Git ignore patterns
├── odas_py/
│   ├── __init__.py            # Package init
│   ├── version.py             # Version info
│   └── odas_processor.py      # High-level Python API
├── src/
│   ├── odas_core.c            # Python C extension module
│   └── odas_wrapper.c         # C wrapper for ODAS
├── include/
│   └── odas_wrapper.h         # C wrapper header
└── examples/
    ├── basic_usage.py         # Basic usage example
    └── wav_file_processing.py # WAV file processing example
```

## Current Status

### ✅ Completed
- Full Python package structure
- CMake-based build system
- Python C extension module setup
- High-level Python API (OdasProcessor class)
- Documentation (README, BUILD, QUICKSTART)
- Example scripts
- Automatic library detection (finds ODAS build)
- Platform detection (Linux/Windows/MinGW)

### ⚠️ Issue
- **Symbol Resolution Problem**: The wrapper currently depends on `odaslive` demo code which has platform-specific dependencies (WASAPI on Windows, ALSA on Linux)
- The odaslive code includes interface constructors that aren't in the core ODAS library

## Solution Path

There are two approaches to fix this:

### Option 1: Simplified Wrapper (Recommended)
Create a minimal wrapper that doesn't use odaslive demo code, instead directly wrapping ODAS core modules:
- Expose individual modules (SSL, SST, SSS, STFT, etc.)
- Let Python code handle the pipeline construction
- More flexible but requires more Python-side logic

### Option 2: Static odaslive Linking
- Build odaslive as a static library
- Link it into the Python extension
- Requires handling all platform-specific audio I/O dependencies

## Next Steps

1. **Simplify the wrapper** to not depend on odaslive
2. **Create module-level wrappers** for:
   - mod_ssl (Sound Source Localization)
   - mod_sst (Sound Source Tracking)
   - mod_sss (Sound Source Separation)
   - mod_stft/istft (Frequency domain transforms)
3. **Test with simple audio input** (NumPy arrays from Python)

## Usage When Complete

```python
from odas_py import OdasProcessor

# Create processor with ODAS config
processor = OdasProcessor('config.cfg')

# Start processing
processor.start()

# Results available via configured sinks
# (files, sockets, or callbacks when implemented)

# Stop
processor.stop()
```

## Build Commands (WSL/Linux)

```bash
cd odas_py

# Build ODAS first (if not already built)
cd ../odas && mkdir -p build && cd build
cmake .. && make -j4
cd ../../odas_py

# Build Python extension
rm -rf build
python3 setup.py build_ext --inplace

# Test
python3 test_structure.py
python3 -c "from odas_py import OdasProcessor; print(OdasProcessor)"
```

## Dependencies

### Linux/WSL
- Python 3.7+
- NumPy
- CMake
- GCC/G++
- libconfig-dev
- ODAS library (built)

### Windows
- Same as above, but need MinGW toolchain for compatibility with MinGW-built ODAS

## Architecture

```
Python Code (odas_py.OdasProcessor)
          ↓
Python C Extension (_odas_core)
          ↓
C Wrapper (odas_wrapper.c)
          ↓
ODAS Library (libodas.so/dll)
```

## Notes

- The build system correctly detects ODAS library location
- Cross-compilation scenarios (MinGW from Linux) are problematic - need native builds
- WSL builds work great for Linux Python extension
- For Windows Python, need MinGW Python or native Windows ODAS build