#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick test of audio capture"""

import sys
import io
import time
import os

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, '.')

from odas_py import OdasLive

# Microphone positions
mic_positions = {
    'mic_0': [0.025, 0.025, 0.025],
    'mic_1': [0.025, -0.025, -0.025],
    'mic_2': [-0.025, 0.025, -0.025],
    'mic_3': [-0.025, -0.025, 0.025],
}

print("Creating processor...")
processor = OdasLive(
    mic_positions=mic_positions,
    n_channels=4,
    frame_size=512,
    sample_rate=44100,
    enable_tracking=False
)

print("Opening audio device...")
processor.set_source_pyaudio(device_name="Teensy")

print("Setting up audio output...")
processor.set_audio_output("test_capture.wav", mode='multi')

frame_count = [0]
def on_sources(pots):
    frame_count[0] += 1

processor.set_pots_callback(on_sources)

print("\nCapturing for 3 seconds...")
processor.start()
time.sleep(3)
processor.stop()
processor.close()

print(f"\nCaptured {frame_count[0]} frames")

# Check files
for ch in range(4):
    fname = f"test_capture_ch{ch}.wav"
    if os.path.exists(fname):
        size = os.path.getsize(fname) / 1024
        print(f"  {fname}: {size:.1f} KB")
    else:
        print(f"  {fname}: NOT FOUND!")

print("\n✓ Audio capture test complete!")