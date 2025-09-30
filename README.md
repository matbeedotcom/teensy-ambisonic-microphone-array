# Teensy Ambisonic Microphone Array

A real-time 3D audio capture and direction-of-arrival (DOA) system using Teensy 4.1 and MEMS microphones.

## Overview

This project implements an 8-channel tetrahedral microphone array for spatial audio applications. Four INMP441 digital MEMS microphones capture sound from all directions, enabling real-time sound source localization with visual feedback.

### Key Features

- **8-channel audio capture** via dual Teensy 4.1 boards (master/slave configuration)
- **Real-time DOA estimation** using GCC-PHAT and SRP-PHAT algorithms
- **Sound classification** to filter and track specific audio types (voice, music, claps)
- **Live visualization** with 2D/3D directional plots and channel monitoring
- **3D-printable frame** with integrated wire management

## System Architecture

```
┌─────────────┐     I2S      ┌──────────────┐     USB Audio    ┌──────────────┐
│ 4x INMP441  ├─────────────►│ Master Teensy├────────────────►│              │
│ Microphones │              │     4.1      │                  │   Host PC    │
└─────────────┘              └──────┬───────┘                  │   (Python)   │
                                     │ TDM                      │              │
┌─────────────┐     I2S      ┌──────┴───────┐                  │ ┌──────────┐ │
│ 4x INMP441  ├─────────────►│ Slave Teensy │                  │ │   DOA    │ │
│ Microphones │              │     4.1      │                  │ │Processing│ │
└─────────────┘              └──────────────┘                  │ └──────────┘ │
                                                                └──────────────┘
```

## Hardware Requirements

- 2× Teensy 4.1 boards
- 8× INMP441 I2S MEMS microphone breakout boards
- 3D printer for tetrahedral frame (70.7mm edge length)
- Wire for I2S and TDM connections
- USB cables for power and data

## Quick Start

### 1. Assemble Hardware

Print the tetrahedral frame and mount microphones:
```bash
cd mechanical
python generate_stl.py  # Creates STL files for 3D printing
```

Follow the [assembly guide](mechanical/assembly_instructions.md) for wiring details.

### 2. Flash Firmware

Upload firmware to both Teensy boards:
- **Master**: `teensy_src/teensy_ambisonic_microphone.ino`
- **Slave**: `teensy_src/slave.ino`

Note: Requires [Teensyduino](https://www.pjrc.com/teensy/teensyduino.html) with USB descriptor patches from `teensy_src/patches/`.

### 3. Install Host Software

```bash
cd host_src
pip install -r requirements.txt
```

### 4. Run DOA Visualization

```bash
python doa_visualizer.py
```

Click "Start" to begin real-time sound source tracking.

## Features in Detail

### Direction of Arrival Algorithms

- **GCC-PHAT**: Fast cross-correlation for time-delay estimation
- **SRP-PHAT**: Robust beamforming-based localization
- **Least-Squares**: Traditional triangulation from time differences

### Sound Classification

Automatically identifies and filters:
- Human voice
- Music
- Claps/transients
- Whistles
- Background noise

### Array Geometry

Regular tetrahedron configuration:
- 43.3mm radius (center to vertex)
- 109.5° angular separation between microphones
- Omnidirectional coverage with minimal blind spots

## Project Structure

```
teensy_ambisonic_microphone/
├── teensy_src/        # Teensy firmware (master/slave)
├── host_src/          # Python DOA processing and visualization
├── mechanical/        # 3D-printable frame design (OpenSCAD)
└── pcb/              # KiCad PCB designs
```

## Performance

- **Sample rate**: 44.1 kHz
- **Latency**: ~23ms (1024 sample blocks)
- **Angular resolution**: 5° grid spacing
- **Update rate**: 20 Hz visualization
- **Maximum trackable distance**: Limited by SNR, typically 3-5 meters indoors

## Applications

- Acoustic scene analysis
- Smart home voice control
- Robotics navigation
- Virtual reality audio
- Acoustic research
- Educational demonstrations

## Contributing

Contributions welcome! Areas of interest:
- Multi-source tracking
- Beamforming implementation
- Raspberry Pi host support
- ROS integration

## License

MIT License - See LICENSE file for details

## Acknowledgments

Built with:
- [Teensy Audio Library](https://www.pjrc.com/teensy/td_libs_Audio.html)
- [INMP441 MEMS Microphones](https://invensense.tdk.com/products/digital/inmp441/)
- Scientific Python stack (NumPy, SciPy, Matplotlib)

## Resources

- [Direction of Arrival Estimation](https://en.wikipedia.org/wiki/Direction_of_arrival)
- [Ambisonic Audio](https://en.wikipedia.org/wiki/Ambisonics)
- [GCC-PHAT Algorithm](https://doi.org/10.1109/TASSP.1976.1162830)
