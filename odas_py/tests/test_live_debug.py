#!/usr/bin/env python3
"""Debug live audio processing"""

import sys
sys.path.insert(0, '.')

from odas_py import OdasLive
import time

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

print("Setting up audio source...")
processor.set_source_pyaudio(device_name="Teensy")

print("Setting up callback...")
frame_count = [0]
def on_sources(pots):
    frame_count[0] += 1
    print(f"Callback called! Frame {frame_count[0]}")

processor.set_pots_callback(on_sources)

print("Starting processor...")
print(f"Running flag: {processor.running}")
print(f"Thread: {processor.thread}")

processor.start()

print(f"After start - Running flag: {processor.running}")
print(f"After start - Thread: {processor.thread}")
print(f"Thread alive: {processor.thread.is_alive() if processor.thread else 'No thread'}")

print("\nWaiting 3 seconds...")
time.sleep(3)

print(f"\nFinal frame count: {frame_count[0]}")
print(f"Thread still alive: {processor.thread.is_alive() if processor.thread else 'No thread'}")

processor.stop()
processor.close()