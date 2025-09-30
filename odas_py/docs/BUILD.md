# Building ODAS-Py

Complete build instructions for ODAS-Py Python bindings.

## Prerequisites

### System Dependencies

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install -y \
    cmake \
    build-essential \
    python3-dev \
    python3-pip \
    libfftw3-dev \
    libasound2-dev \
    libpulse-dev
```

#### Windows (WSL2/MinGW)
```bash
# Install MinGW toolchain
sudo apt-get install -y \
    mingw-w64 \
    cmake \
    python3-dev \
    python3-pip
```

#### macOS
```bash
brew install cmake fftw python
```

### Python Dependencies
```bash
pip install numpy setuptools wheel
```

## Step 1: Build ODAS Library

The Python bindings require the ODAS library to be built first.

### Linux
```bash
cd ../odas
mkdir -p build
cd build
cmake ..
make -j4
```

Verify: Check that `libodas.a` exists in `../odas/build/`

### Windows (MinGW via WSL)
```bash
cd ../odas
bash build_mingw.sh
```

Verify: Check that `libodas.a` exists in `../odas/build-mingw/`

See `../odas/BUILD_WINDOWS.md` for detailed Windows instructions.

## Step 2: Build Python Extension

Once ODAS is built, build the Python bindings:

### Quick Build
```bash
cd odas_py
bash build.sh
```

### Manual Build
```bash
cd odas_py

# Clean previous build
rm -rf build/
rm -f odas_py/_odas_core*.so odas_py/_odas_core*.pyd

# Build extension
python3 setup.py build_ext --inplace
```

### Development Installation
```bash
# Install in editable mode
pip install -e .
```

## Step 3: Verify Installation

```bash
# Test import
python3 -c "from odas_py import OdasProcessor; print('Success!')"

# Check version
python3 -c "from odas_py import __version__; print(__version__)"

# Run basic example
python3 examples/basic_usage.py
```

## Troubleshooting

### "ODAS library not found"

**Problem**: CMake can't find `libodas.a`

**Solution**:
```bash
# Verify ODAS is built
ls -la ../odas/build/libodas.a        # Linux
ls -la ../odas/build-mingw/libodas.a  # Windows/MinGW

# If missing, build ODAS first (see Step 1)
```

### "Python.h: No such file or directory"

**Problem**: Python development headers not installed

**Solution**:
```bash
# Ubuntu/Debian
sudo apt-get install python3-dev

# macOS (if using homebrew Python)
brew reinstall python

# Check it's available
python3-config --includes
```

### "numpy/arrayobject.h: No such file or directory"

**Problem**: NumPy not installed or headers not found

**Solution**:
```bash
pip install --upgrade numpy

# Verify NumPy is installed
python3 -c "import numpy; print(numpy.get_include())"
```

### "undefined reference to pthread_create"

**Problem**: Missing pthread library (Linux)

**Solution**: Already handled in CMakeLists.txt, but if issue persists:
```bash
# Verify pthread is available
ldconfig -p | grep pthread
```

### Windows-specific: "cannot find -lodas"

**Problem**: MinGW build not found

**Solution**:
```bash
# Build ODAS with MinGW
cd ../odas
bash build_mingw.sh

# Verify library exists
ls -la build-mingw/libodas.a
```

### Import Error: "ImportError: No module named '_odas_core'"

**Problem**: Extension not built or not in correct location

**Solution**:
```bash
# Check if extension was built
ls -la odas_py/_odas_core*.so   # Linux/macOS
ls -la odas_py/_odas_core*.pyd  # Windows

# If missing, rebuild
python3 setup.py build_ext --inplace

# Verify it's importable
python3 -c "from odas_py._odas_core import OdasProcessor"
```

## Build Variants

### Debug Build
```bash
python3 setup.py build_ext --inplace --debug
```

### Release Build (optimized)
```bash
python3 setup.py build_ext --inplace --force
```

### Install System-wide
```bash
sudo pip install .
```

### Create Distribution Package
```bash
python3 setup.py sdist bdist_wheel
# Output in dist/
```

## Platform-Specific Notes

### Linux
- Standard build process works out of the box
- Requires ALSA/PulseAudio dev packages for audio I/O
- Use system Python or virtualenv

### Windows (WSL2)
- Build ODAS using MinGW cross-compiler
- Python bindings run in WSL Linux environment
- Can access Windows audio devices via WASAPI (if configured)

### Windows (Native)
- Not yet tested with native Windows Python
- Recommend WSL2 approach
- Future: Native Windows build with MSVC

### macOS
- Use Homebrew Python recommended
- May need to set CMAKE_OSX_ARCHITECTURES for M1/M2
- CoreAudio backend supported in ODAS

## Continuous Integration

For automated builds:

```bash
#!/bin/bash
set -e

# Build ODAS
cd odas
mkdir -p build && cd build
cmake .. && make -j4
cd ../..

# Build Python bindings
cd odas_py
pip install -r requirements.txt
python3 setup.py build_ext --inplace

# Test
python3 -m pytest tests/  # If tests exist
```

## Performance Optimization

For maximum performance:

1. Build ODAS with optimizations:
   ```bash
   cmake -DCMAKE_BUILD_TYPE=Release ..
   ```

2. Use Intel MKL for FFTW (if available):
   ```bash
   cmake -DUSE_INTEL_MKL=ON ..
   ```

3. Enable OpenMP:
   ```bash
   cmake -DUSE_OPENMP=ON ..
   ```

## Next Steps

Once built successfully:

1. Try the examples: `python3 examples/basic_usage.py`
2. Read the API documentation: `README.md`
3. Integrate with your application

## Support

Issues? Check:
1. ODAS build logs: `../odas/build/CMakeFiles/CMakeError.log`
2. Python extension build: Look for errors in terminal output
3. GitHub Issues: Report bugs with full build log