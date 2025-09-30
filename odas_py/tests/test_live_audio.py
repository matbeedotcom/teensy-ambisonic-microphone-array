#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick test of live audio capture"""

import sys
import io
import time

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, '.')

from odas_py import OdasLive, list_audio_devices

# Find Teensy device
print("Searching for Teensy Audio device...")
devices = list_audio_devices()
teensy_device = None

for dev in devices:
    if 'teensy' in dev['name'].lower() and dev['channels'] >= 4:
        teensy_device = dev
        break

if not teensy_device:
    print("ERROR: Teensy Audio device not found!")
    print("Available devices with 4+ channels:")
    for dev in devices:
        if dev['channels'] >= 4:
            print(f"  [{dev['index']}] {dev['name']} ({dev['channels']} ch)")
    sys.exit(1)

print(f"Found: [{teensy_device['index']}] {teensy_device['name']}")
print()

# Microphone positions
mic_positions = {
    'mic_0': [0.025, 0.025, 0.025],
    'mic_1': [0.025, -0.025, -0.025],
    'mic_2': [-0.025, 0.025, -0.025],
    'mic_3': [-0.025, -0.025, 0.025],
}

# Create processor
print("Creating ODAS processor...")
processor = OdasLive(
    mic_positions=mic_positions,
    n_channels=4,
    frame_size=512,
    sample_rate=44100,
    enable_tracking=False
)

if not processor.odas_pipeline:
    print("ERROR: ODAS C extension not available")
    sys.exit(1)

print("✓ Processor created")

# Set up audio source
print(f"Opening audio device {teensy_device['index']}...")
try:
    processor.set_source_pyaudio(device_index=teensy_device['index'])
    print("✓ Audio device opened")
except Exception as e:
    print(f"✗ Failed to open device: {e}")
    sys.exit(1)

# Set up callback
frame_count = [0]
last_print = [time.time()]

def on_sources(pots):
    frame_count[0] += 1
    active = [p for p in pots if p['value'] > 0.1]

    # Print every 0.5 seconds
    if time.time() - last_print[0] >= 0.5:
        print(f"  Frame {frame_count[0]}: {len(active)} active source(s)")
        last_print[0] = time.time()

processor.set_pots_callback(on_sources)

# Process for 5 seconds
print("\nProcessing audio for 5 seconds...")
print("(Make some noise near the microphones!)")
print()

try:
    processor.start()
    time.sleep(5)
except KeyboardInterrupt:
    print("\nInterrupted!")
finally:
    processor.stop()
    processor.close()

print(f"\n✓ Processed {frame_count[0]} frames successfully")
if frame_count[0] > 0:
    print(f"  Average: {frame_count[0]/5:.1f} fps")
    print("\n🎉 Live audio capture is working!")
else:
    print("\n⚠ Warning: No frames processed. Check if Teensy is streaming audio.")