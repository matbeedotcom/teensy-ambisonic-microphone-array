# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Teensy 4.1-based 8-channel ambisonic microphone array system for 3D audio capture and Direction of Arrival (DOA) estimation. The system uses a master/slave Teensy configuration with INMP441 I2S microphones arranged in a tetrahedral geometry.

## Commands

### Host Software (Python DOA Processing)
```bash
# Install dependencies
cd host_src
pip install -r requirements.txt

# Test audio capture
python audio_capture.py

# Test DOA processing
python doa_processing.py

# Launch visualization GUI
python doa_visualizer.py
```

### Teensy Firmware
```bash
# Arduino CLI is included in bin/arduino-cli
# Compile and upload using Arduino IDE with Teensyduino
# Master firmware: teensy_src/teensy_ambisonic_microphone.ino
# Slave firmware: teensy_src/slave.ino
```

### Mechanical Design
```bash
# Generate STL files for 3D printing
cd mechanical
python generate_stl.py

# Or use OpenSCAD directly
openscad tetrahedron_frame.scad
```

## Architecture

### System Components
1. **Master Teensy**: Captures 4 local I2S microphones + receives 4 channels via TDM from slave → 8-channel USB audio
2. **Slave Teensy**: Captures 4 remote I2S microphones → sends via TDM to master
3. **Host Processing**: Python applications for DOA estimation using GCC-PHAT, SRP-PHAT, and least-squares algorithms
4. **Visualization**: Real-time PyQt5 GUI showing sound direction, channel levels, and sound classification

### Critical Files and Their Relationships

**Array Geometry Configuration**
- `host_src/array_geometry.json` - Defines microphone positions matching the mechanical design
- `mechanical/tetrahedron_frame.scad` - Physical array with vertices at ±25mm (43.3mm radius from center)
- These MUST stay synchronized - tetrahedral with 70.7mm edge length

**Audio Pipeline**
1. `teensy_src/teensy_ambisonic_microphone.ino` - Master captures audio, manages TDM slave
2. `teensy_src/AudioOutputTDM_Slave.cpp` - Custom TDM implementation for inter-Teensy communication
3. `host_src/audio_capture.py` - Receives USB audio stream from Teensy
4. `host_src/doa_processing.py` - Processes multi-channel audio for DOA estimation
5. `host_src/doa_visualizer.py` - Real-time visualization of results

**USB Descriptor Patches**
- `teensy_src/patches/usb_desc.c` - Modified for 8-channel USB audio
- Must be applied to Teensy Audio Library before compilation

### Key Technical Details

**Audio Specifications**
- Sample Rate: 44.1 kHz
- Channels: 8 (4 local + 4 from slave)
- Microphones: INMP441 I2S digital MEMS
- Inter-board: TDM protocol on SAI1

**DOA Processing Parameters**
- Maximum time delay: ~9 samples (0.21ms) for 70.7mm array spacing
- Spherical grid: 2520 directions at 5° resolution
- GCC-PHAT window: Hanning with regularization ε=1e-12

**Channel Mapping**
- Channels 0-3: Master's local I2S microphones
- Channels 4-7: Slave's microphones via TDM
- Position mapping defined in `array_geometry.json`

## Development Notes

### When Modifying Array Geometry
1. Update both `host_src/array_geometry.json` AND `mechanical/tetrahedron_frame.scad`
2. Recalculate maximum lag samples in DOA processor
3. Verify channel mapping matches physical wiring

### When Working with Teensy Firmware
- The custom TDM slave implementation in `AudioOutputTDM_Slave.cpp` is critical for inter-board communication
- USB descriptor patches must be applied to Teensy Audio Library
- Both master and slave need synchronized sample rates

### When Testing DOA Algorithms
- Use `python doa_processing.py` for synthetic signal testing
- Clap near each microphone to verify channel mapping
- Check confidence thresholds for your environment

### Sound Classification
- `sound_classifier.py` identifies voice, music, claps, whistles, and noise
- Filtering by sound type helps isolate specific sources
- Classification uses spectral features and zero-crossing rate

## Common Issues and Solutions

### "Teensy Audio" device not found
- Ensure USB descriptor patches are applied
- Check both Teensy boards are powered and connected
- Device appears as "Digital Audio Interface (Teensy Audio 4CH)"

### Poor DOA accuracy
- Verify array geometry matches physical construction
- Check all 8 channels are receiving audio (use channel visualizer)
- Adjust speed_of_sound for temperature (c ≈ 331 + 0.6 × T°C)

### TDM communication issues
- Ensure proper wiring between master/slave SAI1 pins
- Verify both boards run at same sample rate
- Check slave.ino is uploaded to secondary Teensy