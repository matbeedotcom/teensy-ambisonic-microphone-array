# Live Audio Capture with ODAS-Py

Real-time sound source localization and tracking with live audio input.

## Features

✅ **PyAudio Integration** - Direct capture from USB audio devices
✅ **Device Auto-Detection** - Automatic Teensy device discovery
✅ **Real-Time Processing** - ~85 fps on typical hardware
✅ **Multiple Input Sources** - WAV files, sockets, or live audio
✅ **Device Enumeration** - List and select from available devices

## Quick Start

### 1. List Available Devices

```python
from odas_py import print_audio_devices

# Show all audio input devices
print_audio_devices()
```

Output:
```
Available Audio Input Devices:
================================================================================
Index  Channels   Sample Rate  Name
--------------------------------------------------------------------------------
3      4          44100        Digital Audio Interface (Teensy Audio 4CH)
...
================================================================================
```

### 2. Basic Live Processing

```python
from odas_py import OdasLive

# Define microphone array geometry
mic_positions = {
    'mic_0': [0.025, 0.025, 0.025],
    'mic_1': [0.025, -0.025, -0.025],
    'mic_2': [-0.025, 0.025, -0.025],
    'mic_3': [-0.025, -0.025, 0.025],
}

# Create processor
processor = OdasLive(
    mic_positions=mic_positions,
    n_channels=4,
    frame_size=512,
    sample_rate=44100,
    enable_tracking=False  # Set True for source tracking
)

# Connect to audio device (automatic Teensy detection)
processor.set_source_pyaudio(device_name="Teensy")

# Or use specific device index
# processor.set_source_pyaudio(device_index=3)

# Set up callback
def on_sources(pots):
    active_sources = [p for p in pots if p['value'] > 0.1]
    for src in active_sources:
        print(f"Source: x={src['x']:.2f}, y={src['y']:.2f}, z={src['z']:.2f}, "
              f"confidence={src['value']:.2f}")

processor.set_pots_callback(on_sources)

# Start processing
processor.start()

# Run for 10 seconds (or use Ctrl+C to stop)
import time
try:
    time.sleep(10)
except KeyboardInterrupt:
    pass

processor.stop()
processor.close()
```

### 3. With Source Tracking (SST)

```python
processor = OdasLive(
    mic_positions=mic_positions,
    n_channels=4,
    frame_size=512,
    sample_rate=44100,
    enable_tracking=True  # Enable tracking
)

processor.set_source_pyaudio(device_name="Teensy")

# Track callback receives persistent source IDs
def on_tracks(tracks):
    for track in tracks:
        print(f"Track {track['id']}: "
              f"pos=({track['x']:.2f}, {track['y']:.2f}, {track['z']:.2f}) "
              f"activity={track['activity']:.2f}")

processor.set_tracks_callback(on_tracks)
processor.start()
```

## Complete Examples

### Interactive Device Selection

See `example_live_audio.py` for a complete interactive example with:
- Device selection menu
- Real-time source display
- Spherical coordinate conversion (azimuth/elevation)
- Progress indicators

### Simple Test

See `test_live_audio.py` for a minimal test that:
- Auto-detects Teensy device
- Processes audio for 5 seconds
- Displays frame processing stats

## Device Selection Methods

### Method 1: Automatic by Name
```python
# Find first device with "Teensy" in name
processor.set_source_pyaudio(device_name="Teensy")

# Also works with partial names
processor.set_source_pyaudio(device_name="USB Audio")
```

### Method 2: By Device Index
```python
# Use specific device index from print_audio_devices()
processor.set_source_pyaudio(device_index=3)
```

### Method 3: Default Device
```python
# Use system default input device
processor.set_source_pyaudio()
```

## Performance

Typical performance with Teensy 4CH USB Audio:

- **Frame Rate**: ~85 fps
- **Latency**: ~11-12 ms per frame
- **CPU Usage**: Low (ODAS is optimized C code)
- **Memory**: ~10-15 MB

**Note**: Frame rate = Sample Rate / Frame Size = 44100 / 512 ≈ 86 fps

## Troubleshooting

### No Audio Devices Found

Check that PyAudio is installed:
```bash
pip install pyaudio
```

### Teensy Not Detected

1. Ensure Teensy is connected and powered
2. Check it appears in Windows Device Manager as "Teensy Audio"
3. Try different USB ports
4. Run `print_audio_devices()` to see all devices

### Buffer Overruns

If you see audio glitches:
- Increase `frame_size` (e.g., 1024 or 2048)
- Close other audio applications
- Check CPU usage

### Low Frame Rate

- Verify Teensy firmware is running
- Check sample rate matches (44100 Hz)
- Monitor system resources

## API Reference

### OdasLive.set_source_pyaudio()

```python
def set_source_pyaudio(
    device_index: Optional[int] = None,
    device_name: Optional[str] = None
)
```

**Parameters:**
- `device_index`: PyAudio device index (from `list_audio_devices()`)
- `device_name`: Substring to search for in device names (case-insensitive)

**Examples:**
```python
processor.set_source_pyaudio()  # Default device
processor.set_source_pyaudio(device_name="Teensy")  # By name
processor.set_source_pyaudio(device_index=3)  # By index
```

### list_audio_devices()

```python
def list_audio_devices() -> List[Dict[str, Any]]
```

Returns list of devices with keys: `index`, `name`, `channels`, `sample_rate`

### print_audio_devices()

```python
def print_audio_devices()
```

Prints formatted table of available audio input devices.

## Integration with Teensy Project

The live audio feature is specifically designed for the Teensy Ambisonic Microphone:

1. **Automatic Detection**: Finds "Teensy Audio" devices automatically
2. **4-Channel Support**: Matches the tetrahedral array configuration
3. **Sample Rate**: 44.1 kHz (standard for Teensy Audio)
4. **USB Audio**: Works with Teensy's USB audio descriptor
5. **Real-Time**: Low latency for interactive applications

## Next Steps

- See `example_live_audio.py` for complete working example
- Check `TODO.md` for upcoming visualization features
- Explore `example_quickstart.py` for WAV file processing

## Performance Tips

1. **Frame Size**: 512 samples = good balance of latency and efficiency
2. **Callbacks**: Keep processing in callbacks minimal
3. **Threading**: Callbacks run in the processing thread
4. **Buffer Size**: PyAudio automatically handles buffering
5. **Stop Cleanly**: Always call `processor.stop()` and `processor.close()`

---

**Status**: ✅ Live audio capture is fully operational (2025-09-30)

**Compatible With**:
- Windows 10/11 ✅
- Teensy 4.1 USB Audio ✅
- PyAudio 0.2.14+ ✅
- Python 3.8+ ✅