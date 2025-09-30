#!/usr/bin/env python3
"""
Basic ODAS-Py usage example using OdasLive

Demonstrates simple sound source localization using the Python bindings
"""

import sys
import time
import numpy as np
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from odas_py import OdasLive, HAS_C_EXTENSION


def main():
    print("=" * 60)
    print("ODAS-Py Basic Usage Example")
    print("=" * 60)
    print()

    # Check if C extension is available
    if not HAS_C_EXTENSION:
        print("WARNING: C extension not available, using simulation mode")
        print("For full functionality, ensure _odas_core is built correctly")
        print()

    # Define tetrahedral microphone array geometry (in meters)
    # 70.7mm edge length tetrahedron, 43.3mm radius
    mic_positions = {
        'mic_0': [0.0433, 0.0, 0.025],      # Front vertex
        'mic_1': [-0.0433, 0.0, 0.025],     # Back vertex
        'mic_2': [0.0, 0.0433, -0.025],     # Right vertex
        'mic_3': [0.0, -0.0433, -0.025]     # Left vertex
    }

    # Create ODAS processor
    print("Creating ODAS processor...")
    processor = OdasLive(
        n_channels=4,
        sample_rate=44100,
        frame_size=512,
        mic_positions=mic_positions,
        enable_tracking=False,
        enable_separation=False
    )

    print("Processor created successfully")
    print(f"  Channels: {processor.n_channels}")
    print(f"  Sample rate: {processor.sample_rate} Hz")
    print(f"  Frame size: {processor.frame_size} samples")
    print(f"  Native pipeline: {processor.odas_pipeline is not None}")
    print()

    if not processor.odas_pipeline:
        print("NOTE: Running in simulation mode (no native processing)")
        print("Sound source localization will not be performed")
        print()
        return 0

    # Set up callback for localization results
    detected_sources = []

    def ssl_callback(pots):
        """Callback for potential sound sources"""
        # Filter sources with energy above threshold
        active_sources = [p for p in pots if p.get('value', 0) > 0.1]
        if active_sources:
            detected_sources.extend(active_sources)
            print(f"  Frame {len(detected_sources)}: {len(active_sources)} active source(s)")
            for i, pot in enumerate(active_sources):
                x, y, z = pot['x'], pot['y'], pot['z']
                val = pot.get('value', 0)
                # Convert to spherical (azimuth, elevation)
                r = np.sqrt(x**2 + y**2 + z**2)
                if r > 0:
                    azimuth = np.arctan2(y, x) * 180 / np.pi
                    elevation = np.arcsin(z / r) * 180 / np.pi
                    print(f"    Source {i+1}: Az={azimuth:6.1f}°, El={elevation:6.1f}°, E={val:.3f}")

    processor.set_pots_callback(ssl_callback)

    # Generate synthetic test signal (1kHz tone from direction [1, 0, 0])
    print("Generating synthetic test signal...")
    print("  1000 Hz tone, 2 seconds, simulated from front direction")
    print()

    duration = 2.0  # seconds
    num_frames = int(duration * processor.sample_rate / processor.frame_size)

    # Generate tone
    t = np.arange(processor.frame_size) / processor.sample_rate
    freq = 1000  # Hz

    print(f"Processing {num_frames} frames...")
    print()

    # Process frames
    for frame_idx in range(num_frames):
        # Generate audio frame
        # Simulate arrival time differences for source at [1, 0, 0]
        audio_frame = np.zeros((processor.frame_size, 4), dtype=np.float32)

        # Simple phase delay simulation
        for ch in range(4):
            phase_offset = 2 * np.pi * freq * (frame_idx * processor.frame_size + np.arange(processor.frame_size)) / processor.sample_rate
            audio_frame[:, ch] = 0.1 * np.sin(phase_offset)

        # Process through ODAS pipeline
        if processor.odas_pipeline:
            result = processor.odas_pipeline.process(audio_frame)
            if result and 'pots' in result:
                ssl_callback(result['pots'])

    print()
    print(f"Processing complete!")
    print(f"Total frames processed: {num_frames}")
    print(f"Active detections: {len(detected_sources)}")
    print()

    if detected_sources:
        print("Summary of detected sources:")
        # Average detection direction
        avg_x = np.mean([s['x'] for s in detected_sources])
        avg_y = np.mean([s['y'] for s in detected_sources])
        avg_z = np.mean([s['z'] for s in detected_sources])
        avg_val = np.mean([s.get('value', 0) for s in detected_sources])

        r = np.sqrt(avg_x**2 + avg_y**2 + avg_z**2)
        if r > 0:
            avg_azimuth = np.arctan2(avg_y, avg_x) * 180 / np.pi
            avg_elevation = np.arcsin(avg_z / r) * 180 / np.pi
            print(f"  Average direction: Az={avg_azimuth:6.1f}°, El={avg_elevation:6.1f}°")
            print(f"  Average energy: {avg_val:.3f}")

    print()
    print("=" * 60)
    print("Example completed successfully!")
    print("=" * 60)

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
