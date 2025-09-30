# Audio Capture and Output

Capture audio to WAV files while performing real-time DOA estimation.

## Features

✅ **Multi-Channel WAV Output** - Save all microphone channels to file
✅ **Separate Channel Files** - Individual WAV file per channel
✅ **Real-Time Capture** - Capture while processing DOA
✅ **High Quality** - 16-bit PCM at original sample rate

## Quick Start

### Capture to Separate Channel Files

```python
from odas_py import OdasLive

# Configure microphone array
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
    sample_rate=44100
)

# Set audio source
processor.set_source_pyaudio(device_name="Teensy")

# Enable audio capture to separate files
processor.set_audio_output("recording.wav", mode='multi')
# Creates: recording_ch0.wav, recording_ch1.wav, recording_ch2.wav, recording_ch3.wav

# Process for 10 seconds
import time
processor.start()
time.sleep(10)
processor.stop()
processor.close()
```

### Capture to Single Multi-Channel File

```python
# Enable audio capture to single 4-channel file
processor.set_audio_output("recording.wav", mode='single')
# Creates: recording.wav (4-channel interleaved)

processor.start()
time.sleep(10)
processor.stop()
processor.close()
```

## Output Modes

### `mode='multi'` - Separate Files (Recommended)

- Creates one file per channel: `filename_ch0.wav`, `filename_ch1.wav`, etc.
- Each file is mono (1 channel)
- Easy to play and edit in standard audio software
- Individual channel analysis

### `mode='single'` - Single File

- Creates one multi-channel WAV file
- All channels interleaved
- Smaller total file size
- Requires multi-channel capable audio software

## Complete Example

See `example_capture_audio.py` for a complete working example with:
- Device selection
- Progress monitoring
- File size reporting
- Error handling

## File Specifications

**Format**: WAV (RIFF WAVE)
**Encoding**: PCM 16-bit signed integer
**Sample Rate**: 44100 Hz (matches input)
**Channels**: 1 (mono) in 'multi' mode, 4 in 'single' mode
**Byte Order**: Little-endian

## Usage Tips

### 1. Capture While Processing

Audio capture happens simultaneously with DOA processing:

```python
processor.set_audio_output("capture.wav", mode='multi')
processor.set_pots_callback(my_callback)  # DOA results callback
processor.start()
```

Both audio files and DOA results are generated in real-time.

### 2. Recording Duration

The capture continues as long as the processor is running:

```python
# Record for specific duration
processor.start()
time.sleep(60)  # 60 seconds
processor.stop()

# Or run until interrupted
processor.start()
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    processor.stop()
```

### 3. File Size Estimation

Approximate file size per second:
- **1 channel**: ~88 KB/s (44100 Hz × 2 bytes)
- **4 channels (separate)**: ~352 KB/s total
- **4 channels (single)**: ~352 KB/s

Example: 10 seconds = ~880 KB per channel = ~3.5 MB total

### 4. Verifying Captured Audio

```python
import wave

# Check a captured file
w = wave.open("recording_ch0.wav", 'rb')
print(f"Channels: {w.getnchannels()}")
print(f"Sample rate: {w.getframerate()} Hz")
print(f"Duration: {w.getnframes() / w.getframerate():.1f}s")
w.close()
```

## Use Cases

### 1. Debugging and Validation

Capture audio to verify:
- Microphone array is working
- Channels are correctly mapped
- Audio levels are appropriate
- No clipping or distortion

### 2. Creating Test Datasets

Record audio samples for:
- Algorithm development
- Performance testing
- Training machine learning models
- Sharing with others

### 3. Offline Processing

Capture live audio, then process later:

```python
# Capture
processor.set_source_pyaudio(device_name="Teensy")
processor.set_audio_output("dataset.wav", mode='multi')
processor.start()
time.sleep(300)  # 5 minutes
processor.stop()

# Later: Process from files
processor2 = OdasLive(...)
processor2.set_source_wav("dataset_ch0.wav")  # Process first channel
processor2.run_blocking()
```

### 4. Multi-Stage Processing

1. Capture raw audio
2. Apply preprocessing
3. Run DOA estimation
4. Save results and audio together

## API Reference

### `OdasLive.set_audio_output(filename, mode='single')`

Enable audio output to WAV file(s).

**Parameters:**
- `filename` (str): Output filename
- `mode` (str): 'single' for multi-channel WAV, 'multi' for separate files

**Examples:**
```python
# Separate channel files
processor.set_audio_output("recording.wav", mode='multi')

# Single multi-channel file
processor.set_audio_output("recording.wav", mode='single')

# With path
processor.set_audio_output("data/capture_2024.wav", mode='multi')
```

**Notes:**
- Must be called before `start()`
- Files are created immediately on first audio frame
- Files are properly closed when `close()` is called
- Overwrites existing files

## Combining Features

### Capture + Live DOA + Tracking

```python
processor = OdasLive(
    mic_positions=mic_positions,
    n_channels=4,
    frame_size=512,
    sample_rate=44100,
    enable_tracking=True  # Enable tracking
)

processor.set_source_pyaudio(device_name="Teensy")
processor.set_audio_output("session.wav", mode='multi')

# Both callbacks and audio output work simultaneously
processor.set_pots_callback(lambda pots: print(f"Sources: {len(pots)}"))
processor.set_tracks_callback(lambda tracks: print(f"Tracks: {len(tracks)}"))

processor.start()
time.sleep(30)
processor.stop()
processor.close()

# Results:
# - session_ch0.wav, session_ch1.wav, etc. (audio files)
# - Real-time DOA and tracking data via callbacks
```

## Troubleshooting

### Files Not Created

- Check that processor is actually running (`processor.start()` called)
- Verify write permissions in output directory
- Ensure filename doesn't contain invalid characters

### Files Are Empty

- Confirm audio source is providing data
- Check if processing loop is running (callbacks being called)
- Verify no exceptions in processing loop

### Choppy Audio

- Reduce `frame_size` for lower latency
- Close other applications using audio
- Check CPU usage

### Wrong Duration

- Ensure `processor.stop()` is called to flush buffers
- Call `processor.close()` to properly close files

## Performance

Audio writing is very fast:
- Minimal CPU overhead (~1-2%)
- No impact on DOA processing performance
- Async I/O handled by Python's `wave` module
- Suitable for long recordings

## Future Enhancements

Planned features (see TODO.md):
- [ ] Sound source separation (SSS module)
- [ ] Separated audio per tracked source
- [ ] Real-time beamforming output
- [ ] Compressed audio formats (MP3, FLAC)
- [ ] Streaming to network

---

**Status**: ✅ Audio capture fully operational (2025-09-30)

**See Also**:
- `LIVE_AUDIO.md` - Live audio input documentation
- `example_capture_audio.py` - Complete capture example
- `example_live_audio.py` - Live processing example