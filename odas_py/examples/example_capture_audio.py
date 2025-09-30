#!/usr/bin/env python3
"""
Capture Audio Example

Demonstrates capturing audio to WAV files while performing DOA estimation.
This is useful for:
- Recording audio from the Teensy microphone array
- Debugging and validation
- Creating test datasets
- Future sound source separation
"""

import sys
import time
from odas_py import OdasLive

# =============================================================================
# Configuration
# =============================================================================

# Microphone array geometry (tetrahedral, 25mm spacing)
MIC_POSITIONS = {
    'mic_0': [0.025, 0.025, 0.025],
    'mic_1': [0.025, -0.025, -0.025],
    'mic_2': [-0.025, 0.025, -0.025],
    'mic_3': [-0.025, -0.025, 0.025],
}

# Processing options
N_CHANNELS = 4
FRAME_SIZE = 512
SAMPLE_RATE = 44100
DURATION_SECONDS = 10  # How long to capture

# Output options
OUTPUT_MODE = 'multi'  # 'single' for one multi-channel file, 'multi' for separate files
OUTPUT_FILE = 'captured_audio.wav'

# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 80)
    print("ODAS-Py Audio Capture Example")
    print("=" * 80)
    print()

    # Create processor
    print("Creating ODAS processor...")
    processor = OdasLive(
        mic_positions=MIC_POSITIONS,
        n_channels=N_CHANNELS,
        frame_size=FRAME_SIZE,
        sample_rate=SAMPLE_RATE,
        enable_tracking=False
    )

    if not processor.odas_pipeline:
        print("ERROR: ODAS C extension not available")
        return 1

    print("✓ Processor created")
    print()

    # Set up audio source
    print("Opening audio device...")
    try:
        processor.set_source_pyaudio(device_name="Teensy")
        print("✓ Using Teensy Audio device")
    except Exception as e:
        print(f"ERROR: Failed to open audio device: {e}")
        print("\nTry running: from odas_py import print_audio_devices; print_audio_devices()")
        return 1

    # Set up audio output
    print(f"\nSetting up audio output: {OUTPUT_FILE}")
    print(f"  Mode: {OUTPUT_MODE}")
    processor.set_audio_output(OUTPUT_FILE, mode=OUTPUT_MODE)

    if OUTPUT_MODE == 'multi':
        base = OUTPUT_FILE.rsplit('.', 1)[0]
        ext = OUTPUT_FILE.rsplit('.', 1)[1] if '.' in OUTPUT_FILE else 'wav'
        print(f"  Files: {base}_ch0.{ext}, {base}_ch1.{ext}, {base}_ch2.{ext}, {base}_ch3.{ext}")
    else:
        print(f"  File: {OUTPUT_FILE} ({N_CHANNELS}-channel)")

    # Set up callback for monitoring
    frame_count = [0]
    source_count = [0]
    last_print = [time.time()]

    def on_sources(pots):
        frame_count[0] += 1
        active = [p for p in pots if p['value'] > 0.1]
        if active:
            source_count[0] += len(active)

        # Print status every 0.5 seconds
        if time.time() - last_print[0] >= 0.5:
            elapsed = frame_count[0] / (SAMPLE_RATE / FRAME_SIZE)
            sys.stdout.write(f'\r  Recording: {elapsed:.1f}s / {DURATION_SECONDS}s | '
                           f'Frames: {frame_count[0]} | '
                           f'Active sources detected: {source_count[0]}        ')
            sys.stdout.flush()
            last_print[0] = time.time()

    processor.set_pots_callback(on_sources)

    # Start recording
    print()
    print("=" * 80)
    print(f"Recording for {DURATION_SECONDS} seconds...")
    print("(Press Ctrl+C to stop early)")
    print("=" * 80)
    print()

    try:
        processor.start()
        time.sleep(DURATION_SECONDS)
    except KeyboardInterrupt:
        print("\n\nStopping early...")
    finally:
        processor.stop()
        processor.close()

    # Summary
    print("\n")
    print("=" * 80)
    print("Recording Complete!")
    print("=" * 80)
    elapsed = frame_count[0] / (SAMPLE_RATE / FRAME_SIZE)
    print(f"\nCaptured {frame_count[0]} frames ({elapsed:.1f} seconds)")
    print(f"Average: {frame_count[0]/elapsed:.1f} fps")
    print(f"\nOutput files:")

    import os
    if OUTPUT_MODE == 'multi':
        base = OUTPUT_FILE.rsplit('.', 1)[0]
        ext = OUTPUT_FILE.rsplit('.', 1)[1] if '.' in OUTPUT_FILE else 'wav'
        for ch in range(N_CHANNELS):
            fname = f"{base}_ch{ch}.{ext}"
            if os.path.exists(fname):
                size = os.path.getsize(fname) / 1024  # KB
                print(f"  {fname} ({size:.1f} KB)")
    else:
        if os.path.exists(OUTPUT_FILE):
            size = os.path.getsize(OUTPUT_FILE) / 1024  # KB
            print(f"  {OUTPUT_FILE} ({size:.1f} KB)")

    print("\nYou can now:")
    print("  - Play the audio files to verify capture")
    print("  - Use them as input for processing: processor.set_source_wav('captured_audio_ch0.wav')")
    print("  - Analyze them with audio software")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())