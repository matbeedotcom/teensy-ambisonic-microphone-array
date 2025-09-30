# Sound Source Separation (SSS) - Quick Start

## Overview

ODAS-Py now supports Sound Source Separation (SSS), which allows you to:
- **Separate** individual sound sources from multi-channel microphone input
- **Beamform** toward tracked sources to extract their audio
- **Isolate** specific sources while suppressing background noise

## Key Fixes Implemented

Three critical bugs were fixed to enable SSS:

1. **Timestamp Increment**: ODAS modules check `timeStamp==0` to detect invalid frames. Now properly incremented.
2. **SST Timestamp Sync**: SST requires matching timestamps between pots and targets inputs.
3. **SSS Timestamp Sync**: SSS requires matching timestamps between spectra, powers, and tracks inputs.

## Basic Usage

```python
from odas_py import OdasLive

# Define microphone array geometry
mic_positions = {
    'mic_0': [0.025, 0.025, 0.025],
    'mic_1': [0.025, -0.025, -0.025],
    'mic_2': [-0.025, 0.025, -0.025],
    'mic_3': [-0.025, -0.025, 0.025],
}

# Create processor with SSS enabled
processor = OdasLive(
    mic_positions=mic_positions,
    n_channels=4,
    frame_size=512,
    sample_rate=44100,
    enable_tracking=True,      # Required for SSS
    enable_separation=True      # Enable SSS
)

# Process audio frames
audio_frame = ...  # Shape: (512, 4), dtype: float32

result = processor.odas_pipeline.process(audio_frame)

# Access results
pots = result['pots']              # SSL detections
tracks = result['tracks']           # Tracked sources
separated = result['separated']     # Beamformed audio toward sources
residual = result['residual']       # Residual/noise audio
```

## How It Works

### Pipeline Flow

```
Audio Input (4 channels)
    ↓
STFT (Time → Frequency)
    ↓
SSL (Sound Source Localization)
    ↓
SST (Sound Source Tracking)
    ↓
SSS (Sound Source Separation)
    ↓
ISTFT (Frequency → Time)
    ↓
Separated Audio Output
```

### SSS Algorithms

ODAS-Py uses **DGSS (Geometric Source Separation)** with **multi-channel spectral subtraction**:

- **mode_sep = 'g'**: DGSS beamforming (better for small arrays)
- **mode_pf = 'm'**: Multi-channel post-filtering

### Output Format

- **separated**: Beamformed audio pointing at tracked sources (512, 4)
- **residual**: Remaining audio (noise, untracked sources) (512, 4)

Both outputs are in time domain, ready for playback or further processing.

## Examples

See:
- `example_separation.py` - Full SSS examples
- `example_quickstart.py` - Example 4 demonstrates SSS
- `test_sss.py` - Comprehensive test suite

## Requirements

SSS **requires** tracking to be enabled:
```python
enable_tracking=True  # Must be True
enable_separation=True
```

SSS will only produce non-zero output when **active tracks exist**. With synthetic signals or silent audio, separated/residual may be zero.

## Configuration

Current SSS configuration matches `tetrahedral_4ch-b.cfg`:
- DGSS beamforming with λ=0.5, μ=0.01
- Multi-channel spectral subtraction
- gainMin=0.25, nThetas=360

## Troubleshooting

### Zero Separated Output
- **Cause**: No active tracked sources
- **Solution**: Use audio with clear, localized sound sources

### Timestamp Mismatch
- **Fixed**: All timestamp synchronization now handled automatically

### STFT Not Processing
- **Fixed**: Timestamp increment ensures STFT processes every frame

## Technical Details

### Timestamp Flow
1. `hops_in->timeStamp` incremented each frame
2. STFT copies timestamp to `spectra_out`
3. SSL copies timestamp to `pots_out`
4. SST requires `targets_in->timeStamp = pots_out->timeStamp`
5. SSS requires `powers_in->timeStamp = spectra_out->timeStamp`

All timestamp synchronization is now automatic.

## Status

✅ **WORKING**: SSS successfully produces separated audio
✅ **TESTED**: All critical bugs fixed
✅ **INTEGRATED**: Full pipeline SSL → SST → SSS → ISTFT functional
