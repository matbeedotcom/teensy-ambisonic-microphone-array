#!/usr/bin/env python3
"""
ODAS-Py Live Audio Example

Demonstrates real-time sound source localization with live audio input
from a microphone array (e.g., Teensy Ambisonic Microphone).
"""

import time
import sys
from odas_py import OdasLive, print_audio_devices

# =============================================================================
# Configuration
# =============================================================================

# Microphone array geometry (tetrahedral, 25mm spacing)
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

# Processing options
ENABLE_TRACKING = False     # Set to True for source tracking (SST)
ENABLE_SEPARATION = False   # Set to True for sound source separation (SSS) - requires ENABLE_TRACKING=True
DURATION_SECONDS = 30       # How long to process (0 = infinite)

# =============================================================================
# Device Selection
# =============================================================================

def select_audio_device():
    """
    Interactive device selection

    Returns:
        Device index or None for default
    """
    print("\n" + "=" * 80)
    print("ODAS-Py Live Audio Processing")
    print("=" * 80)

    # List available devices
    print_audio_devices()

    # Prompt for selection
    print("\nEnter device index (or press Enter for default, 'q' to quit):")
    choice = input("> ").strip()

    if choice.lower() == 'q':
        sys.exit(0)

    if choice == '':
        return None

    try:
        return int(choice)
    except ValueError:
        print(f"Invalid input '{choice}', using default device")
        return None


# =============================================================================
# Callback Functions
# =============================================================================

class SourceTracker:
    """Track and display detected sources"""

    def __init__(self):
        self.frame_count = 0
        self.last_print_time = time.time()
        self.print_interval = 0.5  # Print every 0.5 seconds
        self.detected_sources = []

    def on_sources(self, pots):
        """Called for each processed frame (SSL results)"""
        self.frame_count += 1

        # Filter sources with significant energy
        active_sources = [p for p in pots if p['value'] > 0.1]
        self.detected_sources = active_sources

        # Print periodically
        current_time = time.time()
        if current_time - self.last_print_time >= self.print_interval:
            self.print_status()
            self.last_print_time = current_time

    def on_tracks(self, tracks):
        """Called for each processed frame (SST results)"""
        # Update tracked sources
        if tracks:
            print(f"\n[Frame {self.frame_count}] Tracked sources:")
            for track in tracks:
                print(f"  Track ID {track['id']}: "
                      f"pos=({track['x']:.2f}, {track['y']:.2f}, {track['z']:.2f}) "
                      f"activity={track['activity']:.2f}")

    def print_status(self):
        """Print current processing status"""
        # Clear line and print
        sys.stdout.write('\r' + ' ' * 100 + '\r')

        if self.detected_sources:
            source_strs = []
            for i, src in enumerate(self.detected_sources[:3]):  # Show up to 3 sources
                # Convert to spherical coordinates for display
                import math
                x, y, z = src['x'], src['y'], src['z']

                # Calculate azimuth (degrees, 0=front, positive=right)
                azimuth = math.degrees(math.atan2(x, y))

                # Calculate elevation (degrees, 0=horizontal, positive=up)
                r_xy = math.sqrt(x*x + y*y)
                elevation = math.degrees(math.atan2(z, r_xy))

                source_strs.append(
                    f"S{i+1}[az={azimuth:+.0f}° el={elevation:+.0f}° "
                    f"conf={src['value']:.2f}]"
                )

            status = f"[Frame {self.frame_count}] {', '.join(source_strs)}"
        else:
            status = f"[Frame {self.frame_count}] No sources detected"

        sys.stdout.write(status)
        sys.stdout.flush()


# =============================================================================
# Main
# =============================================================================

def main():
    """Main processing function"""

    # Select audio device
    device_index = select_audio_device()

    # Create processor
    print("\nInitializing ODAS processor...")
    processor = OdasLive(
        mic_positions=MIC_POSITIONS,
        n_channels=N_CHANNELS,
        frame_size=FRAME_SIZE,
        sample_rate=SAMPLE_RATE,
        enable_tracking=ENABLE_TRACKING,
        enable_separation=ENABLE_SEPARATION
    )

    if not processor.odas_pipeline:
        print("ERROR: ODAS C extension not available")
        print("Please build the extension first (see BUILD_WINDOWS.md)")
        return 1

    # Set up callbacks
    tracker = SourceTracker()
    processor.set_pots_callback(tracker.on_sources)
    if ENABLE_TRACKING:
        processor.set_tracks_callback(tracker.on_tracks)

    # Set up separation output if enabled
    if ENABLE_SEPARATION:
        print("\nSound source separation enabled!")
        print("  - separated.wav: Beamformed audio toward tracked sources")
        print("  - residual.wav: Residual audio (noise/other sources)")
        processor.set_separation_output("separated.wav", "residual.wav", mode='single')

    # Configure audio source
    print("\nOpening audio device...")
    try:
        if device_index is None:
            # Try to find Teensy device automatically
            processor.set_source_pyaudio(device_name="Teensy")
            print("Using Teensy Audio device (auto-detected)")
        else:
            processor.set_source_pyaudio(device_index=device_index)
            print(f"Using device index {device_index}")
    except Exception as e:
        print(f"ERROR: Failed to open audio device: {e}")
        return 1

    # Start processing
    print("\n" + "=" * 80)
    print("Processing audio... (Press Ctrl+C to stop)")
    print("=" * 80)
    print()

    try:
        start_time = time.time()
        processor.start()

        # Run for specified duration (or infinite if 0)
        if DURATION_SECONDS > 0:
            time.sleep(DURATION_SECONDS)
            processor.stop()
        else:
            # Run until interrupted
            while True:
                time.sleep(1)

    except KeyboardInterrupt:
        print("\n\nStopping...")
        processor.stop()

    finally:
        # Clean up
        elapsed = time.time() - start_time
        print(f"\n\nProcessed {tracker.frame_count} frames in {elapsed:.1f} seconds")
        print(f"Average: {tracker.frame_count/elapsed:.1f} fps")
        processor.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())