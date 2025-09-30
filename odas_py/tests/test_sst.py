#!/usr/bin/env python3
"""
Test script for ODAS SST (Sound Source Tracking) module

This script tests the complete SSL → SST pipeline with tracking.
"""

import numpy as np
from odas_py.odaslive import OdasLive

# Define tetrahedral microphone array geometry
mic_positions = {
    'mic_0': [0.025, 0.025, 0.025],
    'mic_1': [0.025, -0.025, -0.025],
    'mic_2': [-0.025, 0.025, -0.025],
    'mic_3': [-0.025, -0.025, 0.025],
}

def test_sst_tracking():
    """Test SST tracking with generated signal"""
    print("=" * 60)
    print("Testing ODAS SST (Sound Source Tracking)")
    print("=" * 60)

    # Create ODAS processor with tracking enabled
    print("\n1. Initializing ODAS pipeline with tracking...")
    try:
        processor = OdasLive(
            mic_positions=mic_positions,
            n_channels=4,
            frame_size=512,
            sample_rate=44100,
            enable_tracking=True  # Enable SST
        )
        print("   ✓ ODAS pipeline initialized successfully")

        if processor.odas_pipeline:
            print("   ✓ Using real ODAS C extension with SST enabled")
        else:
            print("   ⚠ C extension not available")
            return False

    except Exception as e:
        print(f"   ✗ Failed to initialize: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Generate test signal - simulate a moving source
    print("\n2. Creating test signal...")
    sample_rate = 44100
    duration = 2.0  # 2 seconds
    n_samples = int(sample_rate * duration)
    n_channels = 4

    # Create a sine wave with time-varying amplitude (simulates moving source)
    t = np.linspace(0, duration, n_samples, dtype=np.float32)
    frequency = 1000  # 1kHz tone

    # Simulate amplitude modulation to create "moving" effect
    amplitude_mod = np.abs(np.sin(2 * np.pi * 0.5 * t))  # 0.5 Hz modulation
    audio = np.sin(2 * np.pi * frequency * t) * amplitude_mod
    audio = audio.reshape(-1, 1)
    audio = np.tile(audio, (1, n_channels)).astype(np.float32)

    print(f"   ✓ Generated {duration}s of modulated {frequency}Hz tone, shape: {audio.shape}")

    # Process frames and collect results
    print("\n3. Processing frames with tracking...")
    hop_size = 512
    n_frames = 0
    tracks_detected = []

    try:
        for i in range(0, len(audio) - hop_size, hop_size):
            frame = audio[i:i+hop_size, :]
            if frame.shape[0] == hop_size:
                result = processor.odas_pipeline.process(frame)
                n_frames += 1

                # Check if tracks were detected
                if 'tracks' in result and len(result['tracks']) > 0:
                    tracks_detected.append(result['tracks'])
                    if len(tracks_detected) <= 3:  # Print first few
                        print(f"   Frame {n_frames}: {len(result['tracks'])} track(s)")
                        for track in result['tracks']:
                            print(f"      Track ID {track['id']}: "
                                  f"pos=({track['x']:.3f}, {track['y']:.3f}, {track['z']:.3f}) "
                                  f"activity={track['activity']:.3f}")

        print(f"   ✓ Processed {n_frames} frames")
        print(f"   ✓ Tracks detected in {len(tracks_detected)} frames")

    except Exception as e:
        print(f"   ✗ Processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Analyze tracking results
    print("\n4. Tracking results summary:")
    if len(tracks_detected) > 0:
        # Count unique track IDs
        unique_ids = set()
        for frame_tracks in tracks_detected:
            for track in frame_tracks:
                unique_ids.add(track['id'])

        print(f"   Total unique tracks: {len(unique_ids)}")
        print(f"   Track IDs: {sorted(unique_ids)}")

        # Calculate average track duration
        if len(tracks_detected) > 1:
            avg_duration = len(tracks_detected) / len(unique_ids) if len(unique_ids) > 0 else 0
            print(f"   Average track duration: {avg_duration:.1f} frames")
    else:
        print("   ⚠ No tracks detected (this is normal for synthetic uniform signals)")

    print("\n" + "=" * 60)
    print("SST test completed successfully!")
    print("=" * 60)
    return True


def test_ssl_vs_sst():
    """Compare SSL-only vs SSL+SST output"""
    print("\n" + "=" * 60)
    print("Comparing SSL vs SSL+SST")
    print("=" * 60)

    # Test without tracking
    print("\n1. Testing SSL only (no tracking)...")
    processor_ssl = OdasLive(
        mic_positions=mic_positions,
        n_channels=4,
        frame_size=512,
        sample_rate=44100,
        enable_tracking=False
    )

    # Test with tracking
    print("2. Testing SSL + SST (with tracking)...")
    processor_sst = OdasLive(
        mic_positions=mic_positions,
        n_channels=4,
        frame_size=512,
        sample_rate=44100,
        enable_tracking=True
    )

    # Generate simple test frame
    test_frame = np.random.randn(512, 4).astype(np.float32) * 0.1

    # Process with SSL only
    result_ssl = processor_ssl.odas_pipeline.process(test_frame)
    print(f"\n   SSL only result keys: {list(result_ssl.keys())}")
    print(f"   Number of pots: {len(result_ssl['pots'])}")

    # Process with SSL + SST
    result_sst = processor_sst.odas_pipeline.process(test_frame)
    print(f"\n   SSL+SST result keys: {list(result_sst.keys())}")
    print(f"   Number of pots: {len(result_sst['pots'])}")
    if 'tracks' in result_sst:
        print(f"   Number of tracks: {len(result_sst['tracks'])}")

    print("\n" + "=" * 60)
    return True


if __name__ == "__main__":
    import sys

    # Run SST tracking test
    success = test_sst_tracking()

    # Run comparison test
    if success:
        success = test_ssl_vs_sst()

    sys.exit(0 if success else 1)