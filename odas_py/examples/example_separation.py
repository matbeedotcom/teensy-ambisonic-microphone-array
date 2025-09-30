"""
Example: Sound Source Separation with ODAS

This example demonstrates how to use the SSS (Sound Source Separation) module
to extract individual sound sources from a multi-channel microphone array.

Requirements:
- Multi-channel audio file or live audio device
- ODAS-Py with SSS support (enable_separation=True)
"""

import sys
import numpy as np
from pathlib import Path

# Add odas_py to path
sys.path.insert(0, str(Path(__file__).parent))

from odas_py import OdasLive, print_audio_devices


def example_separation_from_wav():
    """
    Example 1: Process WAV file and separate sources

    This example reads a multi-channel WAV file, tracks sound sources,
    and outputs separated audio for each tracked source.
    """
    print("=" * 70)
    print("Example 1: Sound Source Separation from WAV File")
    print("=" * 70)

    # Define tetrahedral microphone array geometry
    mic_positions = {
        'mic_0': [0.025, 0.025, 0.025],
        'mic_1': [0.025, -0.025, -0.025],
        'mic_2': [-0.025, 0.025, -0.025],
        'mic_3': [-0.025, -0.025, 0.025],
    }

    # Create processor with tracking AND separation enabled
    processor = OdasLive(
        mic_positions=mic_positions,
        n_channels=4,
        frame_size=512,
        sample_rate=44100,
        enable_tracking=True,      # Required for separation
        enable_separation=True      # Enable beamforming/separation
    )

    # Set input WAV file
    input_file = "../windows_odas_app/input_raw_4ch.wav"
    if not Path(input_file).exists():
        print(f"Input file not found: {input_file}")
        print("Please provide a 4-channel WAV file")
        return

    processor.set_source_wav(input_file)

    # Set output files for separated audio
    processor.set_separation_output(
        separated_file="separated_sources.wav",
        residual_file="residual_noise.wav",
        mode='single'  # Single multi-channel file
    )

    # Set up callbacks to monitor results
    def on_tracks(tracks):
        active_tracks = [t for t in tracks if t['activity'] > 0.5]
        if active_tracks:
            print(f"  Tracking {len(active_tracks)} source(s):")
            for track in active_tracks:
                print(f"    ID {track['id']}: "
                      f"direction=({track['x']:.2f}, {track['y']:.2f}, {track['z']:.2f}), "
                      f"activity={track['activity']:.2f}")

    def on_separated(separated, residual):
        # Monitor separated audio energy
        sep_energy = np.mean(np.abs(separated))
        res_energy = np.mean(np.abs(residual))
        print(f"  Separated energy: {sep_energy:.4f}, Residual energy: {res_energy:.4f}")

    processor.set_tracks_callback(on_tracks)
    processor.set_separated_callback(on_separated)

    print(f"\nProcessing {input_file}...")
    print("Press Ctrl+C to stop\n")

    try:
        processor.run_blocking()
    except KeyboardInterrupt:
        print("\nStopped by user")

    processor.close()

    print("\nOutput files:")
    print("  - separated_sources.wav: Beamformed audio pointing at tracked sources")
    print("  - residual_noise.wav: Remaining audio (noise, other sources)")


def example_live_separation():
    """
    Example 2: Real-time source separation from live audio

    This example captures audio from a USB audio device (e.g., Teensy),
    tracks sources in real-time, and saves separated audio to files.
    """
    print("\n" + "=" * 70)
    print("Example 2: Real-Time Sound Source Separation")
    print("=" * 70)

    # Show available audio devices
    print("\nAvailable audio input devices:")
    print_audio_devices()

    # Define tetrahedral microphone array
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
        sample_rate=44100,
        enable_tracking=True,
        enable_separation=True
    )

    # Set audio source (automatically find Teensy device)
    try:
        processor.set_source_pyaudio(device_name="Teensy")
        print("\n✓ Found Teensy audio device")
    except:
        print("\n⚠ Teensy not found, using default audio device")
        try:
            processor.set_source_pyaudio()
        except Exception as e:
            print(f"✗ Failed to open audio device: {e}")
            return

    # Enable separation output
    processor.set_separation_output(
        separated_file="live_separated.wav",
        residual_file="live_residual.wav",
        mode='single'
    )

    # Also save raw input for comparison
    processor.set_audio_output("live_input.wav", mode='single')

    # Set up monitoring callbacks
    frame_count = [0]

    def on_tracks(tracks):
        active = [t for t in tracks if t['activity'] > 0.5]
        if active and frame_count[0] % 50 == 0:  # Print every 50 frames
            print(f"\n[{frame_count[0]:05d}] Active sources: {len(active)}")
            for track in active:
                print(f"  Source {track['id']}: "
                      f"azimuth={np.arctan2(track['y'], track['x']) * 180/np.pi:.1f}°, "
                      f"activity={track['activity']:.2f}")

    def on_separated(separated, residual):
        frame_count[0] += 1
        if frame_count[0] % 100 == 0:  # Print every 100 frames
            sep_rms = np.sqrt(np.mean(separated**2))
            res_rms = np.sqrt(np.mean(residual**2))
            snr = 20 * np.log10(sep_rms / (res_rms + 1e-10))
            print(f"[{frame_count[0]:05d}] Separation SNR: {snr:.1f} dB")

    processor.set_tracks_callback(on_tracks)
    processor.set_separated_callback(on_separated)

    print("\nStarting real-time processing...")
    print("Press Ctrl+C to stop\n")

    try:
        processor.start()
        # Keep running
        import time
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\nStopping...")

    processor.stop()
    processor.close()

    print("\nOutput files saved:")
    print("  - live_input.wav: Raw multi-channel input")
    print("  - live_separated.wav: Separated sources")
    print("  - live_residual.wav: Residual noise")


def example_separation_modes():
    """
    Example 3: Different separation modes

    ODAS SSS supports multiple separation algorithms:
    - 'd': Delay-and-Sum (DDS) - Simple beamforming
    - 'g': Generalized Sidelobe Canceller (GSS) - Advanced separation

    This example shows how to configure different modes.
    """
    print("\n" + "=" * 70)
    print("Example 3: Separation Modes")
    print("=" * 70)

    print("""
The SSS module currently uses Delay-and-Sum (DDS) beamforming by default.

DDS works by:
1. Tracking source positions using SST (particle filter)
2. Computing time delays to steer beams toward each source
3. Applying delays and summing microphone signals
4. Producing separated audio for each tracked source

To use advanced modes (GSS, post-filtering), the C extension can be
configured with mode_sep='g' and mode_pf='m' or 's' parameters.
See src/odas_modules.c for configuration details.

Current implementation:
- mode_sep = 'd' (Delay-and-Sum)
- mode_pf = none (no post-filtering)
- Separation quality: Good for well-separated sources
- Latency: Low (~11ms per frame)
    """)


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("ODAS Sound Source Separation Examples")
    print("=" * 70)

    import sys

    if len(sys.argv) > 1:
        example_num = sys.argv[1]
        if example_num == "1":
            example_separation_from_wav()
        elif example_num == "2":
            example_live_separation()
        elif example_num == "3":
            example_separation_modes()
        else:
            print(f"Unknown example: {example_num}")
    else:
        print("""
Usage:
    python example_separation.py [example_number]

Examples:
    1 - Process WAV file and separate sources
    2 - Real-time separation from live audio
    3 - Separation modes explanation

For example:
    python example_separation.py 1
        """)