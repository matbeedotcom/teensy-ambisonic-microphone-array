# ODAS-Py: Python Bindings for ODAS

Python bindings for [ODAS (Open embeddeD Audition System)](https://github.com/introlab/odas), providing high-performance native audio processing for sound source localization, tracking, and separation.

## Features

- **Native Performance**: Direct C bindings to ODAS library for maximum speed
- **Sound Source Localization (SSL)**: Real-time direction-of-arrival estimation
- **Sound Source Tracking (SST)**: Track moving sound sources in 3D space
- **Sound Source Separation (SSS)**: Isolate individual audio sources
- **Two API Styles**: Modern Python API (OdasLive) and traditional config-based API (OdasProcessor)
- **Direct Callbacks**: Get results in Python callbacks without sockets/files
- **Cross-Platform**: Supports Linux, Windows (MinGW), and macOS

## Prerequisites

Before installing `odas-py`, you need to build the ODAS library:

### Linux
```bash
cd ../odas
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
make -j4
```

### Windows (MinGW via WSL)
```bash
cd ../odas
bash build-scripts/build_mingw.sh
```

See `../odas/BUILD_WINDOWS.md` or `docs/BUILD_WINDOWS.md` for detailed Windows build instructions.

## Installation

### Quick Build

```bash
# Linux/macOS
bash build-scripts/build.sh

# Windows (from WSL with MinGW)
bash build-scripts/build_windows_from_wsl.sh
```

### Development Installation

```bash
# Install in development mode with pip
pip install -e .

# Or build the extension in-place
python3 setup.py build_ext --inplace
```

### Dependencies

```bash
pip install numpy
# Optional: For live audio capture
pip install pyaudio
```

## Quick Start

### Option 1: OdasLive API (Recommended)

Modern Python API with direct configuration and callbacks:

```python
from odas_py import OdasLive
import numpy as np

# Create processor with microphone array geometry
processor = OdasLive(
    n_channels=4,
    sample_rate=44100,
    frame_size=512,
    mic_positions={
        'mic_0': [0.043, 0.0, 0.025],
        'mic_1': [-0.043, 0.0, 0.025],
        'mic_2': [0.0, 0.043, -0.025],
        'mic_3': [0.0, -0.043, -0.025]
    }
)

# Set up callback for localization results
def ssl_callback(pots):
    for pot in pots:
        x, y, z = pot['x'], pot['y'], pot['z']
        energy = pot.get('value', 0)
        print(f"Source at ({x:.2f}, {y:.2f}, {z:.2f}), E={energy:.3f}")

processor.set_pots_callback(ssl_callback)

# Process audio frames directly
audio_frame = np.random.randn(512, 4).astype(np.float32) * 0.01
result = processor.odas_pipeline.process(audio_frame)
```

### Option 2: OdasProcessor API (Config-based)

Traditional ODAS approach using configuration files:

```python
from odas_py import OdasProcessor

# Create processor with config file
processor = OdasProcessor('examples/config/tetrahedral_4ch.cfg')

# Start processing
processor.start()

# Results sent to sinks defined in config (sockets/files)
import time
time.sleep(30)

# Stop when done
processor.stop()
```

## Examples

### OdasLive Examples (Modern API)

```bash
# Basic synthetic signal processing
python examples/basic_usage.py

# Multiple scenarios with detailed explanations
python examples/example_quickstart.py

# Live audio capture from microphone
python examples/example_live_audio.py

# Sound source separation
python examples/example_separation.py

# Audio capture demonstration
python examples/example_capture_audio.py
```

### OdasProcessor Examples (Config-based)

```bash
# Config file based processing
python examples/config_based_usage.py

# WAV file processing (requires config modification)
python examples/wav_file_processing.py input.wav --duration 30
```

## API Comparison

### OdasLive (Recommended for new projects)

**Advantages:**
- Configure directly in Python code
- Direct callback access to results
- No socket/file I/O overhead
- Easy to prototype and debug
- Better for integration

**Example:**
```python
processor = OdasLive(
    n_channels=4,
    mic_positions={...},
    enable_tracking=True,
    enable_separation=True
)
processor.set_pots_callback(my_callback)
processor.set_tracks_callback(my_track_callback)
```

### OdasProcessor (Compatible with ODAS configs)

**Advantages:**
- Uses standard ODAS `.cfg` files
- Compatible with existing ODAS configurations
- Full feature parity with odaslive demo
- Good for production deployments

**Example:**
```python
processor = OdasProcessor('config.cfg')
processor.start()
# Results via sockets/files as configured
```

## Architecture

```
┌─────────────────────────────────────────┐
│  Python High-Level APIs                 │
│  - OdasLive (modern, callback-based)    │
│  - OdasProcessor (config-based)         │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│  C Extension (_odas_core)               │
│  - OdasPipeline (direct processing)     │
│  - OdasProcessor (odaslive wrapper)     │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│  ODAS Library (libodas)                 │
│  - SSL, SST, SSS modules                │
│  - STFT/ISTFT processing                │
│  - Beamforming algorithms               │
└─────────────────────────────────────────┘
```

## Configuration

### OdasLive Configuration (In Python)

```python
from odas_py import OdasLive

processor = OdasLive(
    n_channels=4,              # Number of microphones
    sample_rate=44100,         # Sample rate in Hz
    frame_size=512,            # STFT frame size
    mic_positions={            # Microphone positions (meters)
        'mic_0': [x, y, z],
        'mic_1': [x, y, z],
        # ...
    },
    enable_tracking=True,      # Enable SST module
    enable_separation=True     # Enable SSS module
)
```

### OdasProcessor Configuration (Config files)

ODAS-Py uses standard ODAS configuration files (`.cfg`). These files define:

- Microphone array geometry
- Audio sources (live capture, WAV files, sockets)
- Processing modules (SSL, SST, SSS)
- Output sinks (files, sockets, stdout)

Example configurations:
- `examples/config/tetrahedral_4ch.cfg` - 4-channel tetrahedral array
- `../odas/config/odaslive/*.cfg` - Various ODAS configurations

## API Reference

### OdasLive

Modern Python API with direct control and callbacks.

#### Constructor
```python
OdasLive(
    config_file: str = None,
    mic_positions: Dict[str, list] = None,
    n_channels: int = 4,
    frame_size: int = 512,
    sample_rate: int = 44100,
    enable_tracking: bool = False,
    enable_separation: bool = False
)
```

#### Methods

**Audio Sources:**
- `set_source_pyaudio(device_index=None, device_name=None)` - Live audio capture
- `set_source_wav(filename)` - WAV file input
- `set_source_socket(host, port)` - Network audio stream

**Callbacks:**
- `set_pots_callback(func)` - SSL results (potential sources)
- `set_tracks_callback(func)` - SST results (tracked sources)
- `set_separated_callback(func)` - SSS results (separated audio)

**Processing:**
- `start()` - Start processing thread
- `stop()` - Stop processing
- `run_for_duration(seconds)` - Process for specified time

**Utility:**
- `list_audio_devices()` - List available audio devices
- `print_audio_devices()` - Print formatted device list

#### Direct Processing

```python
# Access native pipeline directly
result = processor.odas_pipeline.process(audio_frame)

# result contains:
# {
#     'pots': [{'x': float, 'y': float, 'z': float, 'value': float}, ...],
#     'timestamp': int
# }
```

### OdasProcessor

Config-file based API compatible with standard ODAS.

#### Constructor
```python
OdasProcessor(config_file: str)
```

#### Methods
- `start()` - Start processing threads
- `stop()` - Stop processing threads
- `is_running() -> bool` - Check if processor is active

## Output Formats

### SSL Results (Potential Sources)

```python
[
    {'x': 0.707, 'y': 0.0, 'z': 0.707, 'value': 0.85},
    {'x': -0.5, 'y': 0.5, 'z': 0.707, 'value': 0.42},
    # ...
]
```

### SST Results (Tracked Sources)

```python
[
    {'id': 1, 'x': 0.7, 'y': 0.0, 'z': 0.7, 'activity': 0.9},
    {'id': 2, 'x': -0.5, 'y': 0.5, 'z': 0.7, 'activity': 0.6},
    # ...
]
```

### SSS Results (Separated Audio)

```python
{
    'separated': np.ndarray,  # Shape: (hop_size, n_sources)
    'residual': np.ndarray    # Shape: (hop_size, n_channels)
}
```

## Troubleshooting

### "ODAS native module not available"

**Linux:**
```bash
# Build C extension
python3 setup.py build_ext --inplace

# Check ODAS library exists
ls -la ../odas/build/lib/libodas.so
```

**Windows:**
```bash
# Ensure MinGW build completed
ls -la ../odas/build-mingw/libodas.dll.a

# Rebuild extension
bash build-scripts/build_windows_from_wsl.sh
```

### "Failed to create ODAS processor"

- Verify the config file path is correct
- Check config file syntax (use a validator)
- Ensure audio devices are accessible
- Check socket ports aren't already in use

### Import Errors on Windows

If DLLs can't be loaded:
```python
import os
import sys
# Add DLL directory before importing
os.add_dll_directory(r'C:\path\to\odas_py\odas_py')
from odas_py import OdasLive
```

(Note: This is done automatically in `__init__.py`)

### No Audio Devices Found

```bash
# List devices
python -c "from odas_py import print_audio_devices; print_audio_devices()"

# Install PyAudio if needed
pip install pyaudio
```

### Poor Localization Accuracy

- Verify microphone positions match physical array
- Check all channels are receiving audio
- Adjust `speed_of_sound` for temperature (c ≈ 331 + 0.6 × T°C)
- Increase frame size for better frequency resolution
- Reduce background noise

## Performance

ODAS-Py provides native C performance with minimal Python overhead:

- **Real-time**: 4-8 channel audio at 44.1 kHz
- **Latency**: ~10-20ms for SSL results (frame_size=512)
- **CPU Usage**: <15% on modern processors (single core)
- **Memory**: ~50 MB for typical 4-channel configuration

## Integration with Teensy Ambisonic Microphone

This implementation integrates seamlessly with the Teensy Ambisonic Microphone project:

```python
from odas_py import OdasLive

# Tetrahedral array (70.7mm edges, 43.3mm radius)
processor = OdasLive(
    n_channels=4,
    sample_rate=44100,
    mic_positions={
        'mic_0': [0.025, 0.025, 0.025],
        'mic_1': [0.025, -0.025, -0.025],
        'mic_2': [-0.025, 0.025, -0.025],
        'mic_3': [-0.025, -0.025, 0.025]
    }
)

# Capture from Teensy USB audio
processor.set_source_pyaudio(device_name="Teensy Audio")

# Process and visualize
def ssl_callback(pots):
    # Your visualization code here
    pass

processor.set_pots_callback(ssl_callback)
processor.start()
```

## Features Completed

- ✅ Direct result callbacks (OdasLive API)
- ✅ NumPy array input/output
- ✅ Live audio capture (PyAudio)
- ✅ WAV file processing
- ✅ Sound source separation
- ✅ Cross-platform (Linux, Windows, macOS)

## Planned Enhancements

- [ ] Real-time visualization integration
- [ ] Jupyter notebook widgets
- [ ] Async/await interface
- [ ] Multiple array support
- [ ] Batch processing utilities

## License

MIT License - Same as ODAS

## Credits

- **ODAS Library**: [IntRoLab, Université de Sherbrooke](https://github.com/introlab/odas)
- **Python Bindings**: Part of Teensy Ambisonic Microphone project
- **Contributors**: See Git history

## Related Projects

- [Teensy Ambisonic Microphone Array](../) - Parent project
- [ODAS](https://github.com/introlab/odas) - Open embeddeD Audition System
- [IntRoLab Projects](https://github.com/introlab) - Robotics and audio research

## Support

For issues and questions:
- Check [docs/](docs/) directory for detailed documentation
- Review [examples/](examples/) for usage patterns
- Report bugs via GitHub issues
- See [BUILD.md](docs/BUILD.md) for build troubleshooting

## Citation

If you use ODAS-Py in research, please cite:

```
@misc{odas,
  author = {IntRoLab, Universit\'{e} de Sherbrooke},
  title = {ODAS: Open embeddeD Audition System},
  url = {https://github.com/introlab/odas},
  year = {2017}
}
```
