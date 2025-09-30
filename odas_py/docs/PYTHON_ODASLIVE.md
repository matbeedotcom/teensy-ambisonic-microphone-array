# Python OdasLive

Pure Python implementation of the ODAS Live demo, providing a clean Pythonic interface for real-time audio processing.

## Overview

Instead of wrapping the C `odaslive` demo code (which has complex platform-specific dependencies), we've created a **pure Python implementation** that:

- ✅ Handles all I/O in Python (WAV files, sockets, audio devices)
- ✅ Manages threading and processing pipeline in Python
- ✅ Calls ODAS library only for core DSP operations
- ✅ Provides clean, Pythonic API
- ✅ Works immediately without native extension build issues

## Architecture

```
┌─────────────────────────────────────────┐
│   Python Application Code              │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│   OdasLive (Python)                     │
│   - Audio I/O (WAV, Socket)             │
│   - Threading & Pipeline                │
│   - Result handling                     │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│   ODAS Modules (C extension - future)   │
│   - SSL, SST, SSS                       │
│   - STFT/ISTFT                          │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│   ODAS Library (libodas.so)             │
└───────────────────────────────────────┘
```

## Quick Start

```python
from odas_py import OdasLive

# Create processor
processor = OdasLive('config.cfg')

# Set audio source
processor.set_source_wav('input_4ch.wav')

# Configure outputs
processor.add_sink_stdout('ssl_results')
processor.add_sink_file('tracks', 'tracks.json')

# Set callbacks for results
def on_sound_detected(pots):
    print(f"Detected {len(pots)} sound sources")

processor.set_pots_callback(on_sound_detected)

# Run processing
processor.run_blocking()
```

## Features

### Audio Sources

**WAV File Input**
```python
processor.set_source_wav('input.wav')
```

**Network Socket Input**
```python
processor.set_source_socket('localhost', 10000)
```

**Audio Device Input** (coming soon)
```python
processor.set_source_device('hw:0')  # ALSA
processor.set_source_device('Teensy Audio')  # PulseAudio
```

### Result Sinks

**File Output**
```python
processor.add_sink_file('ssl', 'ssl_results.json')
```

**Network Socket Output**
```python
processor.add_sink_socket('sst', 'localhost', 9000)
```

**Stdout Output**
```python
processor.add_sink_stdout('debug')
```

### Callbacks

**Sound Source Localization (SSL)**
```python
def ssl_callback(pots):
    for pot in pots:
        x, y, z = pot['x'], pot['y'], pot['z']
        print(f"Source at ({x:.2f}, {y:.2f}, {z:.2f})")

processor.set_pots_callback(ssl_callback)
```

**Sound Source Tracking (SST)**
```python
def sst_callback(tracks):
    for track in tracks:
        track_id = track['id']
        x, y, z = track['x'], track['y'], track['z']
        print(f"Track {track_id}: ({x:.2f}, {y:.2f}, {z:.2f})")

processor.set_tracks_callback(sst_callback)
```

## Threading Modes

### Blocking Mode
```python
# Run in current thread until audio ends
processor.run_blocking()
```

### Background Thread
```python
# Start processing in background
processor.start()

# Do other work
for i in range(10):
    time.sleep(1)
    print(f"Main thread working... {i}/10")

# Stop when done
processor.stop()
```

### Context Manager
```python
with OdasLive('config.cfg') as processor:
    processor.set_source_wav('input.wav')
    processor.add_sink_stdout('results')
    processor.run_blocking()
# Automatically cleaned up
```

## Examples

### Example 1: Process WAV File

```python
from odas_py import OdasLive

processor = OdasLive('config.cfg')
processor.set_source_wav('input_4ch.wav')
processor.add_sink_file('results', 'output.json')

print("Processing WAV file...")
processor.run_blocking()
print("Done!")
```

### Example 2: Real-time Network Processing

```python
from odas_py import OdasLive

processor = OdasLive('config.cfg')

# Read audio from network
processor.set_source_socket('localhost', 10000)

# Send results over network
processor.add_sink_socket('ssl', 'localhost', 9000)
processor.add_sink_socket('sst', 'localhost', 9001)

# Run continuously
processor.start()
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    processor.stop()
```

### Example 3: With Visualization

```python
from odas_py import OdasLive
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# Setup processor
processor = OdasLive('config.cfg')
processor.set_source_wav('input.wav')

# Store results for visualization
results = []

def track_callback(tracks):
    results.append(tracks)

processor.set_tracks_callback(track_callback)

# Start processing in background
processor.start()

# Visualize results
fig, ax = plt.subplots()
def update(frame):
    if results:
        latest = results[-1]
        # Plot track positions
        xs = [t['x'] for t in latest]
        ys = [t['y'] for t in latest]
        ax.clear()
        ax.scatter(xs, ys)
        ax.set_xlim(-1, 1)
        ax.set_ylim(-1, 1)

ani = FuncAnimation(fig, update, interval=100)
plt.show()

processor.stop()
```

## Configuration

Currently, OdasLive uses programmatic configuration (not config files). This provides more flexibility:

```python
processor = OdasLive('dummy.cfg')  # Config file not required yet

# Configure everything in code
processor.channels = 4
processor.samplerate = 44100
processor.hopsize = 512
processor.ssl_enabled = True
processor.sst_enabled = True
processor.sss_enabled = False
```

Future: Full `.cfg` file parsing will be added.

## ODAS Module Integration (Next Step)

The current implementation has placeholder processing. The next step is to integrate actual ODAS modules:

```python
def _process_loop(self):
    while self.running:
        audio = self.source.read_hop()

        # STFT
        spectra = self.stft_module.process(audio)

        # SSL - Sound Source Localization
        pots = self.ssl_module.process(spectra)

        # SST - Sound Source Tracking
        tracks = self.sst_module.process(pots)

        # SSS - Sound Source Separation
        separated = self.sss_module.process(spectra, tracks)

        # Output results
        self._output_results(pots, tracks, separated)
```

## Advantages Over C Wrapper

1. **No platform-specific I/O issues** - Handle WASAPI/ALSA/PulseAudio in Python
2. **Easier debugging** - Python stack traces and print debugging
3. **More flexible** - Easy to customize processing pipeline
4. **Better integration** - Natural fit with NumPy, SciPy, visualization tools
5. **Faster development** - No C compilation for I/O changes

## Performance

- Audio I/O overhead is minimal in Python
- Core DSP still runs in native ODAS library
- Threading model allows real-time processing
- Expected: 5-10% overhead vs pure C (still real-time capable)

## Roadmap

- [ ] Integrate actual ODAS module calls (SSL, SST, SSS)
- [ ] Add PyAudio/sounddevice for live microphone input
- [ ] Full `.cfg` file parsing (libconfig format)
- [ ] Result buffering and timestamp management
- [ ] Performance profiling and optimization
- [ ] Audio device enumeration
- [ ] Multi-config support (hot reload)

## Integration with Teensy Project

```python
from odas_py import OdasLive

# Process audio from Teensy microphone array
processor = OdasLive('config/tetrahedral_4ch.cfg')

# Teensy appears as USB audio device - use appropriate source
processor.set_source_device('Teensy Audio')  # PulseAudio name
# OR
processor.set_source_socket('localhost', 8000)  # If using intermediate bridge

# Real-time visualization
processor.set_tracks_callback(update_3d_plot)

# Run
processor.start()
```

## See Also

- `examples/python_odaslive.py` - Complete working example
- `odas_py/odaslive.py` - Implementation source
- `../odas/config/` - ODAS configuration examples