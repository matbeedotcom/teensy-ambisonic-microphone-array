# Ambisonic Microphone DOA Processing

This PC application processes audio from the Teensy ambisonic microphone array to calculate and visualize sound source directions in real-time.

## Features

- **Real-time Audio Capture**: Captures multi-channel audio from Teensy USB Audio device
- **GCC-PHAT Processing**: Computes Time Difference of Arrival (TDOA) using Generalized Cross-Correlation with Phase Transform
- **DOA Estimation**: Two algorithms available:
  - **SRP-PHAT**: Steered Response Power with Phase Transform (robust in reverberant environments)
  - **Least-Squares**: Traditional triangulation method (faster computation)
- **Live Visualization**: 2D polar and 3D spherical plots showing sound source directions
- **Configurable Array Geometry**: JSON-based microphone position configuration

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Connect your Teensy ambisonic microphone array via USB

## Usage

### Quick Start
```bash
# Test audio capture
python audio_capture.py

# Test DOA processing
python doa_processing.py

# Launch visualization GUI
python doa_visualizer.py
```

### Configuration

Edit `array_geometry.json` to match your microphone array:

```json
{
  "name": "your_array_name",
  "description": "Array description",
  "positions": [
    [x1, y1, z1],
    [x2, y2, z2],
    [x3, y3, z3],
    [x4, y4, z4]
  ],
  "sample_rate": 44100,
  "speed_of_sound": 343.0
}
```

Position coordinates are in meters, relative to array center.

## File Structure

- `audio_capture.py` - USB audio interface and streaming
- `doa_processing.py` - GCC-PHAT and DOA algorithms
- `doa_visualizer.py` - Real-time visualization GUI
- `array_geometry.json` - Microphone array configuration
- `requirements.txt` - Python dependencies

## Algorithm Details

### GCC-PHAT (Generalized Cross-Correlation with Phase Transform)

1. **Windowing**: Apply Hann window to reduce spectral leakage
2. **FFT**: Compute frequency domain representations
3. **Cross-spectrum**: Calculate X₁(f) × X₂*(f) for each microphone pair
4. **PHAT Weighting**: Normalize by magnitude: C(f) / |C(f)|
5. **IFFT**: Convert back to time domain to get correlation function
6. **Peak Detection**: Find maximum within physical delay constraints

### SRP-PHAT (Steered Response Power)

1. Create spherical grid of candidate directions (5° resolution)
2. For each direction, compute expected delays between microphone pairs
3. Sample cross-correlation functions at expected delays
4. Sum contributions from all microphone pairs
5. Select direction with maximum summed response

### Least-Squares DOA

1. Extract TDOA estimates from GCC-PHAT peaks
2. Grid search over spherical directions
3. For each direction, compute expected TDOAs
4. Find direction minimizing squared error with measured TDOAs

## Performance Notes

- **Block Size**: 1024 samples provides ~23ms latency at 44.1kHz
- **Grid Resolution**: 5° spacing gives good accuracy/speed tradeoff
- **Confidence Filtering**: Helps reject spurious detections in noisy conditions
- **Memory Usage**: ~50MB typical for real-time processing

## Troubleshooting

### Audio Device Not Found
1. Check USB connection to Teensy
2. Verify Teensy appears as "Teensy Audio" or similar in device list
3. Run `audio_capture.py` to see available devices

### Poor DOA Accuracy
1. Verify microphone array geometry in `array_geometry.json`
2. Check for consistent channel mapping (clap test near each mic)
3. Adjust `speed_of_sound` for temperature: c ≈ 331 + 0.6 × T°C
4. Try larger block size (2048) in noisy environments

### High CPU Usage
1. Reduce spherical grid resolution (use 10° instead of 5°)
2. Increase block size to reduce processing rate
3. Use least-squares method instead of SRP-PHAT

## Hardware Requirements

- **Teensy 4.1** with 4-8 channel audio streaming
- **INMP441 I2S microphones** in tetrahedral or planar arrangement
- **USB connection** for audio streaming
- **PC** with Python 3.7+ and audio drivers

## Future Enhancements

- Multiple simultaneous source tracking
- Adaptive beamforming
- Noise suppression and source separation
- Integration with room correction
- Export to common audio formats