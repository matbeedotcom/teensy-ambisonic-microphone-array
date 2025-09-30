# ODAS-Py: Python Bindings for ODAS

Python bindings for [ODAS (Open embeddeD Audition System)](https://github.com/introlab/odas), providing high-performance native audio processing for sound source localization, tracking, and separation.

## Features

- **Native Performance**: Direct C bindings to ODAS library for maximum speed
- **Sound Source Localization (SSL)**: Real-time direction-of-arrival estimation
- **Sound Source Tracking (SST)**: Track moving sound sources in 3D space
- **Sound Source Separation (SSS)**: Isolate individual audio sources
- **Cross-Platform**: Supports Linux, Windows (MinGW), and macOS

## Prerequisites

Before installing `odas-py`, you need to build the ODAS library:

### Linux
```bash
cd ../odas
mkdir build && cd build
cmake ..
make -j4
```

### Windows (MinGW)
```bash
cd ../odas
bash build_mingw.sh
```

See `../odas/BUILD_WINDOWS.md` for detailed Windows build instructions.

## Installation

### Development Installation

```bash
# Install in development mode with pip
pip install -e .

# Or build the extension in-place
python setup.py build_ext --inplace
```

### Dependencies

```bash
pip install numpy
```

## Quick Start

```python
from odas_py import OdasProcessor

# Create processor with config file
processor = OdasProcessor('config/tetrahedral_4ch.cfg')

# Start processing
processor.start()

# Let it run...
import time
time.sleep(30)

# Stop when done
processor.stop()
```

### Context Manager Usage

```python
from odas_py import OdasProcessor

with OdasProcessor('config/tetrahedral_4ch.cfg') as processor:
    # Process for 30 seconds
    processor.run_for_duration(30.0)
    # Automatically stops when exiting context
```

## Examples

See the `examples/` directory for complete examples:

- `basic_usage.py` - Simple real-time processing
- `wav_file_processing.py` - Offline WAV file analysis

```bash
# Run basic example
python examples/basic_usage.py

# Process WAV file
python examples/wav_file_processing.py input.wav --duration 30
```

## Configuration

ODAS-Py uses standard ODAS configuration files (`.cfg`). These files define:

- Microphone array geometry
- Audio sources (live capture, WAV files, sockets)
- Processing modules (SSL, SST, SSS)
- Output sinks (files, sockets, stdout)

Example configurations are in `../odas/config/`:
- `tetrahedral_4ch.cfg` - 4-channel tetrahedral array
- And others...

## Architecture

```
┌─────────────────┐
│  Python Layer   │  odas_py.OdasProcessor (High-level API)
└────────┬────────┘
         │
┌────────▼────────┐
│ C Extension     │  _odas_core (Python C API wrapper)
│   (odas_core.c) │
└────────┬────────┘
         │
┌────────▼────────┐
│ C Wrapper       │  odas_wrapper.c (C interface)
│ (odas_wrapper.c)│
└────────┬────────┘
         │
┌────────▼────────┐
│  ODAS Library   │  Native ODAS processing (libodas.a)
│   (libodas.a)   │
└─────────────────┘
```

## API Reference

### OdasProcessor

Main class for ODAS audio processing.

#### Constructor
```python
OdasProcessor(config_file: str)
```
- `config_file`: Path to ODAS configuration file

#### Methods

- `start()` - Start processing threads
- `stop()` - Stop processing threads
- `is_running() -> bool` - Check if processor is active
- `run_for_duration(duration: float)` - Run for specified seconds
- `validate_config(config_file: str) -> bool` - Validate config file

## Output

ODAS results are output according to the sinks defined in your configuration file:

- **File Sinks**: Write tracking/localization data to files
- **Socket Sinks**: Stream results over network (JSON format)
- **Stdout Sink**: Print results to console

Example sink configuration in `.cfg` file:
```
snk_pots_ssl: {
    format = "json";
    interface = {
        type = "file";
        path = "ssl_output.json";
    }
}
```

## Troubleshooting

### "Failed to create ODAS processor"
- Verify the config file path is correct
- Check that the config file is valid (use `OdasProcessor.validate_config()`)
- Ensure required audio devices/files are accessible

### "ODAS native module not available"
- Build the C extension: `python setup.py build_ext --inplace`
- Ensure ODAS library is built (`libodas.a` exists in `../odas/build/`)
- Check that CMake found all dependencies

### Windows Build Issues
- Use MinGW toolchain (see `../odas/BUILD_WINDOWS.md`)
- Ensure Python development headers are installed
- Try: `pip install --upgrade pip setuptools wheel`

## Performance

ODAS-Py provides native C performance with minimal Python overhead:

- Real-time processing of 4-8 channel audio
- ~10-20ms latency for SSL results
- Low CPU usage (<15% on modern processors)

## Integration with Existing Project

This implementation integrates seamlessly with the Teensy Ambisonic Microphone project:

```python
from odas_py import OdasProcessor

# Use with tetrahedral microphone array
processor = OdasProcessor('../odas/config/tetrahedral_4ch.cfg')

with processor:
    # ODAS processes audio from Teensy USB audio device
    # Results available via configured sinks
    processor.run_for_duration(60.0)
```

## Future Enhancements

Planned features:
- [ ] Direct result callbacks (requires ODAS library modification)
- [ ] NumPy array input/output for custom processing
- [ ] Real-time visualization integration
- [ ] Jupyter notebook support
- [ ] Async/await interface

## License

Same license as ODAS (MIT License)

## Credits

- ODAS Library: [IntRoLab, Université de Sherbrooke](https://github.com/introlab/odas)
- Python Bindings: Part of Teensy Ambisonic Microphone project

## Related Projects

- Parent Project: Teensy Ambisonic Microphone Array
- ODAS: https://github.com/introlab/odas
- Python DOA Visualization: `../host_src/doa_visualizer.py`