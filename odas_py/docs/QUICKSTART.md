# ODAS-Py Quick Start

Get up and running with ODAS-Py in 3 steps.

## Prerequisites

```bash
# Install Python dependencies
pip install numpy

# Verify Python setup
python3 --version  # Should be 3.7+
```

## Step 1: Build ODAS Library (One-Time Setup)

### Linux
```bash
cd ../odas
mkdir -p build && cd build
cmake ..
make -j4
cd ../../odas_py
```

### Windows (WSL with MinGW)
```bash
cd ../odas
bash build_mingw.sh
cd ../odas_py
```

## Step 2: Build Python Bindings

```bash
# Simple one-liner
bash build.sh

# Or manually
python3 setup.py build_ext --inplace
```

## Step 3: Test It!

```bash
# Verify installation
python3 -c "from odas_py import OdasProcessor; print('✓ Success!')"

# Run example (requires config file and audio device)
python3 examples/basic_usage.py
```

## Usage Example

```python
from odas_py import OdasProcessor

# Initialize with config
processor = OdasProcessor('path/to/config.cfg')

# Start processing
processor.start()

# Let it run
import time
time.sleep(30)

# Stop
processor.stop()
```

## Common Issues

### "ODAS library not found"
→ Build ODAS first (Step 1)

### "Config file not found"
→ Use a valid path to `.cfg` file:
```python
processor = OdasProcessor('../odas/config/tetrahedral_4ch.cfg')
```

### "Failed to initialize audio capture"
→ Check your config file specifies correct audio device/interface

## What's Next?

- Read [README.md](README.md) for full API documentation
- See [BUILD.md](BUILD.md) for detailed build instructions
- Check [examples/](examples/) for more usage patterns
- Review ODAS configuration format: https://github.com/introlab/odas

## Performance Tips

- Use Release build of ODAS library for best performance
- Configure ODAS sinks (file/socket) for result output
- Monitor CPU usage - should be <15% on modern hardware

## Getting Help

1. Run structure test: `python3 test_structure.py`
2. Check build logs for errors
3. Review [BUILD.md](BUILD.md) troubleshooting section
4. Report issues with full error messages