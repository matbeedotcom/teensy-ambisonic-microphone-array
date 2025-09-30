"""
Basic SSL test to verify source detection is working
"""

import sys
import numpy as np
sys.path.insert(0, '.')

from odas_py import OdasLive

# Tetrahedral array
mic_positions = {
    'mic_0': [0.025, 0.025, 0.025],
    'mic_1': [0.025, -0.025, -0.025],
    'mic_2': [-0.025, 0.025, -0.025],
    'mic_3': [-0.025, -0.025, 0.025],
}

print("Creating ODAS processor...")
processor = OdasLive(
    mic_positions=mic_positions,
    n_channels=4,
    frame_size=512,
    sample_rate=44100,
    enable_tracking=False,
    enable_separation=False
)

print("Processor created successfully")

# Generate test signal - pure tone
t = np.linspace(0, 512/44100, 512, dtype=np.float32)
tone = np.sin(2 * np.pi * 1000 * t) * 0.5

# Replicate to all channels
audio = np.tile(tone.reshape(-1, 1), (1, 4))

print(f"\nProcessing 10 frames of 1kHz tone...")
print(f"Audio stats: min={audio.min():.3f}, max={audio.max():.3f}, mean={audio.mean():.6f}")

total_detections = 0
for i in range(10):
    result = processor.odas_pipeline.process(audio)

    # Count pots with value > threshold
    active_pots = [p for p in result['pots'] if p['value'] > 0.01]
    total_detections += len(active_pots)

    if i < 3 or len(active_pots) > 0:
        print(f"  Frame {i}: {len(active_pots)} detections")
        if active_pots:
            best = max(active_pots, key=lambda p: p['value'])
            print(f"    Best: ({best['x']:.3f}, {best['y']:.3f}, {best['z']:.3f}) value={best['value']:.6f}")

print(f"\nTotal detections across 10 frames: {total_detections}")

if total_detections == 0:
    print("\n[FAIL] SSL detected ZERO sources - not working!")
else:
    print(f"\n[OK] SSL detected sources in {total_detections} pot-frames")
