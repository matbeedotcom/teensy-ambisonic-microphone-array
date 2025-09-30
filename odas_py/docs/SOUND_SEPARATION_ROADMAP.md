# Sound Source Separation (SSS) Roadmap

## Current Status

✅ **Audio Capture** - Raw multi-channel audio can now be saved to WAV files
✅ **DOA Estimation (SSL)** - Direction of arrival for sound sources
✅ **Source Tracking (SST)** - Persistent tracking of moving sources

⏳ **Source Separation (SSS)** - Not yet implemented

## What is Sound Source Separation?

SSS extracts individual sound sources from the multi-channel microphone array, producing:
- Separate audio stream for each tracked source
- Reduced cross-talk between sources
- Enhanced signal-to-noise ratio

Example: If two people are speaking simultaneously from different directions, SSS produces two separate audio files, one for each speaker.

## Current Workaround

Until SSS is implemented, you can:

1. **Capture Raw Audio**
   ```python
   processor.set_audio_output("capture.wav", mode='multi')
   processor.start()
   ```

2. **Track Source Directions**
   ```python
   def on_tracks(tracks):
       for track in tracks:
           print(f"Track {track['id']}: az={track['x']}, el={track['y']}")
   processor.set_tracks_callback(on_tracks)
   ```

3. **Post-Process with External Tools**
   - Use captured WAV files
   - Apply beamforming offline (e.g., with scipy, pyroomacoustics)
   - Filter by direction based on tracking data

## Implementation Plan

### Phase 1: ISTFT Module
- Add Inverse STFT for frequency → time domain conversion
- Required for converting separated frequency-domain signals to audio

### Phase 2: Basic Beamforming
- Delay-and-sum beamforming
- Simple directional filtering
- Output one beam per tracked source

### Phase 3: Advanced Separation
- Delay-and-Sum Separation (DDS)
- Generalized Sidelobe Canceller (GSC)
- Minimum Variance Distortionless Response (MVDR)

### Phase 4: Post-Filtering
- Multi-channel Spectral Subtraction (MS)
- Single-channel Spectral Subtraction (SS)
- Wiener filtering

## Technical Details

### ODAS SSS Module

The ODAS library includes a comprehensive SSS module (`mod_sss`) with:

**Separation Methods:**
- `'d'` - Delay-and-Sum (DDS)
- `'g'` - Generalized Sidelobe Canceller (GSS)

**Post-Filtering:**
- `'m'` - Multi-channel spectral subtraction
- `'s'` - Single-channel spectral subtraction

**Configuration Parameters:**
- Beamforming angles and patterns
- Adaptation parameters (mu, lambda)
- Noise estimation parameters
- Gain limits and thresholds

### Integration Challenges

1. **Complexity**: SSS module is large (~500 lines of config)
2. **Dependencies**: Requires many ODAS signal processing objects
3. **Configuration**: Many parameters need tuning per array geometry
4. **Testing**: Requires quality metrics to validate separation

## Estimated Timeline

- **Phase 1 (ISTFT)**: 1-2 days
- **Phase 2 (Basic Beamforming)**: 2-3 days
- **Phase 3 (Advanced Separation)**: 3-5 days
- **Phase 4 (Post-Filtering)**: 2-3 days
- **Testing & Tuning**: 2-3 days

**Total**: ~2-3 weeks for full implementation

## Alternative Approaches

### 1. Python-Based Beamforming

Implement simple beamforming in Python:

```python
def delay_and_sum_beamform(audio, mic_positions, target_direction):
    """Simple delay-and-sum beamformer"""
    # Calculate delays for each mic
    delays = calculate_delays(mic_positions, target_direction)

    # Apply delays and sum
    beamformed = np.zeros(len(audio))
    for ch, delay in enumerate(delays):
        beamformed += np.roll(audio[:, ch], delay)

    return beamformed / len(mic_positions)
```

**Pros:**
- Simple to implement
- No C extension changes needed
- Easy to understand and modify

**Cons:**
- Less efficient than ODAS C implementation
- Basic quality (no advanced algorithms)
- Per-frame processing overhead

### 2. External Tools Integration

Use existing Python libraries:

**pyroomacoustics:**
```python
import pyroomacoustics as pra

# Create microphone array
mic_array = pra.MicrophoneArray(mic_positions.T, fs=44100)

# Apply beamformer
beamformer = pra.Beamformer(mic_array, target_direction)
output = beamformer.process(audio)
```

**scipy:**
```python
from scipy.signal import fftconvolve

# Manual beamforming with scipy
# ... frequency domain processing
```

**Pros:**
- Leverage existing libraries
- Well-tested algorithms
- Active maintenance

**Cons:**
- Additional dependencies
- May not match ODAS quality
- Integration complexity

## Recommended Path Forward

### For Now: Audio Capture + Manual Processing

1. Use `set_audio_output()` to capture raw audio
2. Use `set_tracks_callback()` to get source directions
3. Post-process with preferred tool

### Near Future: Basic Beamforming

1. Add Python-based delay-and-sum beamformer
2. Output one audio file per tracked source
3. Good enough for many applications

### Long Term: Full ODAS SSS

1. Integrate complete SSS module from ODAS
2. All separation methods and post-filters
3. Optimal quality and performance

## References

- ODAS Documentation: https://github.com/introlab/odas
- pyroomacoustics: https://github.com/LCAV/pyroomacoustics
- Beamforming Tutorial: http://www.labbookpages.co.uk/audio/beamforming.html

## Status

**Current Capability**: ✅ Capture raw multi-channel audio
**Next Step**: ⏳ Implement ISTFT module
**Target Date**: TBD based on priority

---

**Note**: Sound source separation is a complex feature. The current audio capture provides a solid foundation for future development or external processing tools.

**See Also**:
- `AUDIO_CAPTURE.md` - Current audio output documentation
- `TODO.md` - Full feature roadmap
- `example_capture_audio.py` - Audio capture example