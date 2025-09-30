#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Quick test for tracking functionality"""

import sys
import os

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from odas_py import OdasLive

print("Testing ODAS tracking...")
print()

# Configuration
mic_positions = {
    'mic_0': [0.025, 0.025, 0.025],
    'mic_1': [0.025, -0.025, -0.025],
    'mic_2': [-0.025, 0.025, -0.025],
    'mic_3': [-0.025, -0.025, 0.025],
}

try:
    print("Creating processor with tracking...")
    processor = OdasLive(
        mic_positions=mic_positions,
        n_channels=4,
        frame_size=512,
        sample_rate=44100,
        enable_tracking=True
    )
    print("✓ Processor created")
    print()

    if not processor.odas_pipeline:
        print("✗ C extension not available")
        sys.exit(1)

    # Generate test signal
    print("Generating test signal...")
    n_samples = 512
    audio = np.random.randn(n_samples, 4).astype(np.float32) * 0.1
    print("✓ Signal generated")
    print()

    # Process one frame
    print("Processing frame...")
    result = processor.odas_pipeline.process(audio)
    print("✓ Frame processed")
    print()

    # Check result structure
    print("Result structure:")
    print(f"  Keys: {list(result.keys())}")
    if 'pots' in result:
        print(f"  Pots: {len(result['pots'])} detected")
    if 'tracks' in result:
        print(f"  Tracks: {len(result['tracks'])} tracked")
    else:
        print("  ⚠ No 'tracks' key in result")
    print()

    print("✓ Test completed successfully!")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)