#!/usr/bin/env python3
"""
Python OdasLive Example

Demonstrates using the pure Python implementation of odaslive
for real-time audio processing with ODAS.
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from odas_py.odaslive import OdasLive


def pots_callback(pots):
    """Callback for potential sound sources (SSL results)"""
    print(f"SSL: {len(pots)} potential sources detected")
    for i, pot in enumerate(pots):
        print(f"  Source {i}: x={pot.get('x', 0):.2f}, y={pot.get('y', 0):.2f}, z={pot.get('z', 0):.2f}")


def tracks_callback(tracks):
    """Callback for tracked sound sources (SST results)"""
    print(f"SST: {len(tracks)} tracked sources")
    for track in tracks:
        track_id = track.get('id', -1)
        x = track.get('x', 0)
        y = track.get('y', 0)
        z = track.get('z', 0)
        print(f"  Track {track_id}: ({x:.2f}, {y:.2f}, {z:.2f})")


def main():
    """Main demo"""

    print("=" * 60)
    print("Python OdasLive Demo")
    print("=" * 60)

    # Check for WAV file argument
    if len(sys.argv) > 1:
        wav_file = sys.argv[1]
    else:
        wav_file = "../windows_odas_app/input_raw_4ch.wav"

    if not Path(wav_file).exists():
        print(f"Error: WAV file not found: {wav_file}")
        print("Usage: python python_odaslive.py [input.wav]")
        return 1

    # Configuration (simplified - would normally come from .cfg file)
    config_file = "dummy.cfg"  # Not used yet

    # Create processor
    print(f"\nProcessing: {wav_file}")
    processor = OdasLive(config_file)

    # Configure source
    processor.set_source_wav(wav_file)

    # Configure sinks
    processor.add_sink_stdout("ssl_results")
    processor.add_sink_file("tracks", "tracks_output.json")

    # Set callbacks
    processor.set_pots_callback(pots_callback)
    processor.set_tracks_callback(tracks_callback)

    print("\nStarting processing...")
    print("(Results will be printed to console and saved to tracks_output.json)")
    print()

    try:
        # Run in blocking mode
        processor.run_blocking()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    finally:
        processor.close()

    print("\nProcessing complete!")
    return 0


def threaded_example():
    """
    Alternative example using background thread
    """
    config_file = "dummy.cfg"
    processor = OdasLive(config_file)

    # Setup
    processor.set_source_wav("input.wav")
    processor.add_sink_stdout("results")

    # Start in background
    processor.start()

    # Do other work while processing
    print("Processing in background...")
    for i in range(10):
        time.sleep(1)
        print(f"Main thread working... {i}/10")

    # Stop
    processor.stop()
    processor.close()


def socket_example():
    """
    Example using network sockets
    """
    config_file = "dummy.cfg"
    processor = OdasLive(config_file)

    # Read audio from network
    processor.set_source_socket("localhost", 10000)

    # Send results over network
    processor.add_sink_socket("ssl", "localhost", 9000)
    processor.add_sink_socket("sst", "localhost", 9001)

    # Run
    with processor:
        processor.run_blocking()


if __name__ == '__main__':
    sys.exit(main())