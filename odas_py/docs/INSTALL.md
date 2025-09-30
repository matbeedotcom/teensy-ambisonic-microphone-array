# ODAS-Py Installation

## Quick Install (No Compilation)

The package includes pre-built binaries for common platforms.

### Install from source directory

```bash
pip install -e .
```

This installs in "editable" mode - the code runs directly from this directory.

### Or create a wheel and install

```bash
# Create wheel
pip install build
python -m build --wheel

# Install the wheel
pip install dist/odas_py-1.0.0-py3-none-any.whl
```

## Usage

```python
from odas_py import OdasLive

# Create processor
processor = OdasLive('config.cfg')

# Set audio source
processor.set_source_wav('input_4ch.wav')

# Add output sink
processor.add_sink_stdout('results')

# Process
processor.run_blocking()
```

## Pre-built Binaries

The package includes:
- `odas_py/_odas_core.so` - Linux/WSL2 (x86_64)
- More platforms coming soon

If the C extension doesn't load, the pure Python implementation will work as a fallback.

## Building from Source (Optional)

If you want to rebuild the C extension:

### Linux/WSL2
```bash
python setup.py build_ext --inplace
```

### Windows
Requires MinGW-w64. See `install_mingw_windows.md` for details.

## Dependencies

- Python 3.7+
- NumPy

Audio I/O requires:
- For WAV files: Built-in (wave module)
- For audio devices: `pyaudio` or `sounddevice` (optional)
- For network: Built-in (socket module)

## Testing

```bash
# Test import
python -c "from odas_py import OdasLive; print('Success!')"

# Run example
python examples/python_odaslive.py
```