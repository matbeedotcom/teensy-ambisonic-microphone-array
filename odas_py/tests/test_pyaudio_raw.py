#!/usr/bin/env python3
"""Test raw PyAudio reading from Teensy"""

import pyaudio
import numpy as np
import time

# Find Teensy device
pa = pyaudio.PyAudio()
teensy_index = None

for i in range(pa.get_device_count()):
    info = pa.get_device_info_by_index(i)
    if 'teensy' in info['name'].lower() and info['maxInputChannels'] >= 4:
        teensy_index = i
        print(f"Found Teensy at index {i}: {info['name']}")
        print(f"  Channels: {info['maxInputChannels']}")
        print(f"  Sample rate: {info['defaultSampleRate']}")
        break

if teensy_index is None:
    print("Teensy not found!")
    pa.terminate()
    exit(1)

# Open stream
print("\nOpening stream...")
try:
    stream = pa.open(
        format=pyaudio.paInt16,
        channels=4,
        rate=44100,
        input=True,
        input_device_index=teensy_index,
        frames_per_buffer=512
    )
    print("✓ Stream opened")
except Exception as e:
    print(f"✗ Failed to open stream: {e}")
    pa.terminate()
    exit(1)

# Read a few frames
print("\nReading audio...")
frames_read = 0
try:
    for i in range(10):
        data = stream.read(512, exception_on_overflow=False)
        audio = np.frombuffer(data, dtype=np.int16).reshape(-1, 4)
        rms = np.sqrt(np.mean(audio.astype(float)**2))
        print(f"  Frame {i+1}: shape={audio.shape}, RMS level={rms:.1f}")
        frames_read += 1
        time.sleep(0.01)
except Exception as e:
    print(f"✗ Read error: {e}")

print(f"\n✓ Read {frames_read} frames")

# Clean up
stream.stop_stream()
stream.close()
pa.terminate()

if frames_read > 0:
    print("\n✓ PyAudio is working with Teensy!")
else:
    print("\n✗ Failed to read audio from Teensy")