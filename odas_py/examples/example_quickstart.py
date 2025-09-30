#!/usr/bin/env python3
"""
ODAS-Py Quick Start Example

This example demonstrates basic usage of ODAS-Py for sound source localization
with a tetrahedral microphone array.
"""

import numpy as np
from odas_py.odaslive import OdasLive

# =============================================================================
# Configuration
# =============================================================================

# Define your microphone array geometry (in meters)
# This example uses a tetrahedral array with 25mm spacing
MIC_POSITIONS = {
    'mic_0': [0.025, 0.025, 0.025],      # Front-top-right
    'mic_1': [0.025, -0.025, -0.025],    # Front-bottom-left
    'mic_2': [-0.025, 0.025, -0.025],    # Back-top-left
    'mic_3': [-0.025, -0.025, 0.025],    # Back-bottom-right
}

# Audio configuration
N_CHANNELS = 4
FRAME_SIZE = 512
SAMPLE_RATE = 44100

# =============================================================================
# Example 1: Process WAV File
# =============================================================================

def example_wav_processing():
    """Process a WAV file and print detected sources"""
    print("=" * 60)
    print("Example 1: Processing WAV File")
    print("=" * 60)

    # Create processor
    processor = OdasLive(
        mic_positions=MIC_POSITIONS,
        n_channels=N_CHANNELS,
        frame_size=FRAME_SIZE,
        sample_rate=SAMPLE_RATE
    )

    # Set up callback to print sources
    def on_sources(pots):
        """Called for each processed frame"""
        active_sources = [p for p in pots if p['value'] > 0.1]  # Filter weak sources
        if active_sources:
            print(f"Frame: {len(active_sources)} source(s) detected")
            for i, source in enumerate(active_sources):
                print(f"  Source {i+1}: position=({source['x']:.3f}, {source['y']:.3f}, {source['z']:.3f}) "
                      f"confidence={source['value']:.3f}")

    processor.set_pots_callback(on_sources)

    # Set audio source (replace with your WAV file)
    wav_file = "test_audio.wav"  # 4-channel, 44.1kHz WAV file
    try:
        processor.set_source_wav(wav_file)
    except Exception as e:
        print(f"Could not load WAV file: {e}")
        print("Please provide a 4-channel WAV file")
        return

    # Process audio
    print("\nProcessing...")
    processor.run_blocking()
    processor.close()

    print("\nDone!")


# =============================================================================
# Example 2: Process Synthetic Signal
# =============================================================================

def example_synthetic_signal():
    """Generate and process a test signal"""
    print("\n" + "=" * 60)
    print("Example 2: Processing Synthetic Signal")
    print("=" * 60)

    # Create processor
    processor = OdasLive(
        mic_positions=MIC_POSITIONS,
        n_channels=N_CHANNELS,
        frame_size=FRAME_SIZE,
        sample_rate=SAMPLE_RATE
    )

    # Generate test signal: 1 second of 1kHz tone
    print("\nGenerating test signal...")
    duration = 1.0  # seconds
    n_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n_samples, dtype=np.float32)
    frequency = 1000  # Hz

    # Create signal with slight phase differences between channels
    # (simulates source direction)
    audio = np.zeros((n_samples, N_CHANNELS), dtype=np.float32)
    for ch in range(N_CHANNELS):
        phase_shift = ch * 0.1  # Slight phase offset per channel
        audio[:, ch] = np.sin(2 * np.pi * frequency * t + phase_shift)

    print(f"Generated {duration}s of {frequency}Hz tone")

    # Process frame by frame
    print("\nProcessing...")
    n_frames = 0
    hop_size = FRAME_SIZE  # Process full frames

    for i in range(0, len(audio) - hop_size, hop_size):
        frame = audio[i:i+hop_size, :]

        # Process through ODAS
        if processor.odas_pipeline:
            result = processor.odas_pipeline.process(frame)

            # Print result for first frame
            if n_frames == 0:
                print(f"\nFirst frame result:")
                print(f"  Detected {len(result['pots'])} potential sources")
                for pot in result['pots']:
                    if pot['value'] > 0.01:
                        print(f"    Position: ({pot['x']:.3f}, {pot['y']:.3f}, {pot['z']:.3f}) "
                              f"Value: {pot['value']:.3f}")

        n_frames += 1

    print(f"\nProcessed {n_frames} frames successfully")


# =============================================================================
# Example 3: Process with Tracking (SSL + SST)
# =============================================================================

def example_with_tracking():
    """Enable tracking to follow moving sources"""
    print("\n" + "=" * 60)
    print("Example 3: Processing with Source Tracking")
    print("=" * 60)

    # Create processor with tracking enabled
    processor = OdasLive(
        mic_positions=MIC_POSITIONS,
        n_channels=N_CHANNELS,
        frame_size=FRAME_SIZE,
        sample_rate=SAMPLE_RATE,
        enable_tracking=True  # Enable SST module
    )

    if not processor.odas_pipeline:
        print("ODAS C extension not available")
        return

    print("\nTracking enabled - sources will be assigned persistent IDs")

    # Generate moving source simulation
    duration = 2.0
    n_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n_samples, dtype=np.float32)
    frequency = 1000

    # Amplitude modulation simulates moving source
    amplitude_mod = np.abs(np.sin(2 * np.pi * 0.5 * t))
    audio = np.sin(2 * np.pi * frequency * t) * amplitude_mod
    audio = audio.reshape(-1, 1)
    audio = np.tile(audio, (1, N_CHANNELS)).astype(np.float32)

    # Process and track
    print("\nProcessing...")
    n_frames = 0
    tracks_detected = []

    hop_size = FRAME_SIZE
    for i in range(0, len(audio) - hop_size, hop_size):
        frame = audio[i:i+hop_size, :]
        result = processor.odas_pipeline.process(frame)

        # Check for tracked sources
        if 'tracks' in result and len(result['tracks']) > 0:
            tracks_detected.append(result['tracks'])
            if n_frames % 20 == 0:  # Print every 20th frame
                print(f"  Frame {n_frames}: {len(result['tracks'])} tracked source(s)")
                for track in result['tracks']:
                    print(f"    Track ID {track['id']}: activity={track['activity']:.2f}")

        n_frames += 1

    print(f"\nProcessed {n_frames} frames")
    print(f"Tracks detected in {len(tracks_detected)} frames")

    # Analyze unique tracks
    if tracks_detected:
        unique_ids = set()
        for frame_tracks in tracks_detected:
            for track in frame_tracks:
                unique_ids.add(track['id'])
        print(f"Unique tracked sources: {len(unique_ids)}")


# =============================================================================
# Example 4: Sound Source Separation (SSL + SST + SSS)
# =============================================================================

def example_with_separation():
    """Enable separation to extract individual sources"""
    print("\n" + "=" * 60)
    print("Example 4: Sound Source Separation")
    print("=" * 60)

    # Create processor with tracking AND separation enabled
    processor = OdasLive(
        mic_positions=MIC_POSITIONS,
        n_channels=N_CHANNELS,
        frame_size=FRAME_SIZE,
        sample_rate=SAMPLE_RATE,
        enable_tracking=True,      # Required for separation
        enable_separation=True      # Enable beamforming/separation
    )

    if not processor.odas_pipeline:
        print("ODAS C extension not available")
        return

    print("\nSeparation enabled - will beamform toward tracked sources")
    print("Output: separated (beamformed) + residual (noise/other sources)")

    # Generate test signal
    duration = 1.0
    n_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n_samples, dtype=np.float32)
    frequency = 1000

    # Create signal
    audio = np.zeros((n_samples, N_CHANNELS), dtype=np.float32)
    for ch in range(N_CHANNELS):
        phase_shift = ch * 0.1
        audio[:, ch] = np.sin(2 * np.pi * frequency * t + phase_shift) * 0.5

    # Process and separate
    print("\nProcessing with separation...")
    n_frames = 0
    separation_results = []

    hop_size = FRAME_SIZE
    for i in range(0, len(audio) - hop_size, hop_size):
        frame = audio[i:i+hop_size, :]
        result = processor.odas_pipeline.process(frame)

        # Check for separated audio
        if 'separated' in result and 'residual' in result:
            separated = result['separated']
            residual = result['residual']

            # Calculate energy
            sep_energy = np.mean(np.abs(separated))
            res_energy = np.mean(np.abs(residual))

            separation_results.append({
                'separated_energy': sep_energy,
                'residual_energy': res_energy
            })

            if n_frames % 20 == 0:  # Print every 20th frame
                print(f"  Frame {n_frames}: "
                      f"separated={sep_energy:.4f}, residual={res_energy:.4f}")

        n_frames += 1

    print(f"\nProcessed {n_frames} frames with separation")

    if separation_results:
        avg_sep = np.mean([r['separated_energy'] for r in separation_results])
        avg_res = np.mean([r['residual_energy'] for r in separation_results])
        print(f"Average separated energy: {avg_sep:.4f}")
        print(f"Average residual energy: {avg_res:.4f}")
        print(f"Separation ratio: {avg_sep/avg_res:.2f}x" if avg_res > 0 else "N/A")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("\nODAS-Py Quick Start Examples")
    print("============================\n")

    # Run examples
    try:
        # Example 1: WAV file (optional - comment out if no WAV file available)
        # example_wav_processing()

        # Example 2: Synthetic signal (always works)
        example_synthetic_signal()

        # Example 3: Tracking (requires C extension)
        example_with_tracking()

        # Example 4: Separation (requires C extension)
        example_with_separation()

        print("\n" + "=" * 60)
        print("All examples completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()