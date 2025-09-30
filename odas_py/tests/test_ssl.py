#!/usr/bin/env python3
"""
Test script for ODAS SSL module

This script tests the SSL (Sound Source Localization) pipeline with a WAV file.
"""

import numpy as np
from odas_py.odaslive import OdasLive

# Define tetrahedral microphone array geometry (matching your Teensy array)
# Positions in meters - tetrahedral with 25mm from center
mic_positions = {
    'mic_0': [0.025, 0.025, 0.025],      # Front-top-right
    'mic_1': [0.025, -0.025, -0.025],    # Front-bottom-left
    'mic_2': [-0.025, 0.025, -0.025],    # Back-top-left
    'mic_3': [-0.025, -0.025, 0.025],    # Back-bottom-right
}

def test_ssl_pipeline():
    """Test SSL pipeline with WAV file"""
    print("=" * 60)
    print("Testing ODAS SSL Pipeline")
    print("=" * 60)

    # Create ODAS processor
    print("\n1. Initializing ODAS pipeline...")
    try:
        processor = OdasLive(
            mic_positions=mic_positions,
            n_channels=4,
            frame_size=512,
            sample_rate=44100
        )
        print("   ✓ ODAS pipeline initialized successfully")

        if processor.odas_pipeline:
            print("   ✓ Using real ODAS C extension")
        else:
            print("   ⚠ Using simulation mode (C extension not available)")

    except Exception as e:
        print(f"   ✗ Failed to initialize: {e}")
        return False

    # Set up audio source
    print("\n2. Setting up audio source...")
    wav_file = "../windows_odas_app/input_raw_4ch.wav"
    try:
        processor.set_source_wav(wav_file)
        print(f"   ✓ WAV file loaded: {wav_file}")
    except Exception as e:
        print(f"   ✗ Failed to load WAV file: {e}")
        return False

    # Set up callback to collect results
    results_list = []

    def pots_callback(pots):
        results_list.append(pots)
        if len(results_list) <= 5:  # Print first few results
            print(f"   Frame {len(results_list)}: {len(pots)} sources detected")
            for i, pot in enumerate(pots):
                if pot['value'] > 0.1:
                    print(f"      Source {i}: ({pot['x']:.3f}, {pot['y']:.3f}, {pot['z']:.3f}) " +
                          f"value={pot['value']:.3f}")

    processor.set_pots_callback(pots_callback)

    # Process audio
    print("\n3. Processing audio...")
    try:
        processor.run_blocking()
        print(f"   ✓ Processing complete")
        print(f"   ✓ Processed {len(results_list)} frames")
    except Exception as e:
        print(f"   ✗ Processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        processor.close()

    # Analyze results
    print("\n4. Results summary:")
    if len(results_list) > 0:
        print(f"   Total frames: {len(results_list)}")

        # Count frames with active sources
        active_frames = sum(1 for frame in results_list
                           if any(p['value'] > 0.1 for p in frame.get('pots', frame)))
        print(f"   Frames with active sources: {active_frames}")

        # Find max energy
        max_energy = 0.0
        max_pos = None
        for frame in results_list:
            pots = frame.get('pots', frame)
            if isinstance(pots, list):
                for pot in pots:
                    if pot['value'] > max_energy:
                        max_energy = pot['value']
                        max_pos = (pot['x'], pot['y'], pot['z'])

        if max_pos:
            print(f"   Maximum energy: {max_energy:.3f} at position {max_pos}")

    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("=" * 60)
    return True


def test_simple_pipeline():
    """Test pipeline with generated test signal"""
    print("\n" + "=" * 60)
    print("Testing ODAS Pipeline with Generated Signal")
    print("=" * 60)

    print("\n1. Creating test signal...")
    # Generate 1 second of audio at 44.1kHz
    sample_rate = 44100
    duration = 1.0
    n_samples = int(sample_rate * duration)
    n_channels = 4

    # Create a simple sine wave on all channels
    t = np.linspace(0, duration, n_samples, dtype=np.float32)
    frequency = 1000  # 1kHz tone
    audio = np.sin(2 * np.pi * frequency * t).reshape(-1, 1)
    audio = np.tile(audio, (1, n_channels)).astype(np.float32)
    print(f"   ✓ Generated {duration}s of {frequency}Hz tone, shape: {audio.shape}")

    print("\n2. Initializing ODAS pipeline...")
    try:
        processor = OdasLive(
            mic_positions=mic_positions,
            n_channels=4,
            frame_size=512,
            sample_rate=44100
        )
        print("   ✓ Pipeline initialized")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False

    print("\n3. Processing frames...")
    if not processor.odas_pipeline:
        print("   ⚠ C extension not available, skipping")
        return False

    hop_size = 512  # Must match frame_size
    n_frames = 0
    try:
        for i in range(0, len(audio) - hop_size, hop_size):
            frame = audio[i:i+hop_size, :]
            if frame.shape[0] == hop_size:
                result = processor.odas_pipeline.process(frame)
                n_frames += 1
                if n_frames == 1:
                    print(f"   Frame 1 result: {result}")

        print(f"   ✓ Processed {n_frames} frames")
    except Exception as e:
        print(f"   ✗ Processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("Simple test completed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    import sys

    # Run simple test first
    success = test_simple_pipeline()

    # Then run full WAV test
    if success:
        success = test_ssl_pipeline()

    sys.exit(0 if success else 1)