#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script for Windows odas_py installation
Run this to verify the C extension is working correctly
"""

import sys
import os

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add current directory to path so we can import odas_py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 50)
print("Testing odas_py Windows Installation")
print("=" * 50)
print()

# Test 1: Import the module
print("Test 1: Importing odas_py...")
try:
    from odas_py import OdasLive, HAS_C_EXTENSION
    print("✓ Import successful")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

print()

# Test 2: Check C extension
print("Test 2: Checking C extension...")
print(f"HAS_C_EXTENSION: {HAS_C_EXTENSION}")

if HAS_C_EXTENSION:
    print("✓ C extension is available")
    try:
        from odas_py import _odas_core
        print(f"  Extension file: {_odas_core.__file__}")
        print(f"  OdasPipeline class: {_odas_core.OdasPipeline}")
    except Exception as e:
        print(f"  Warning: Could not load C extension details: {e}")
else:
    print("✗ C extension not available - will use simulation mode")
    print()
    print("Troubleshooting:")
    print("  1. Check that _odas_core.pyd exists in odas_py/")
    print("  2. Check that libodas.dll exists in odas_py/")
    print("  3. Check that libwinpthread-1.dll exists in odas_py/")
    print("  4. Try rebuilding with: bash build_windows_from_wsl.sh")

print()

# Test 3: Check DLL files
print("Test 3: Checking required DLLs...")
dll_dir = os.path.join(os.path.dirname(__file__), 'odas_py')
required_files = [
    '_odas_core.pyd',
    'libodas.dll',
    'libwinpthread-1.dll'
]

all_present = True
for filename in required_files:
    filepath = os.path.join(dll_dir, filename)
    exists = os.path.exists(filepath)
    status = "✓" if exists else "✗"
    size = f"{os.path.getsize(filepath) / 1024:.1f} KB" if exists else "missing"
    print(f"  {status} {filename:25s} {size}")
    if not exists:
        all_present = False

print()

# Test 4: Create a simple processor
if HAS_C_EXTENSION:
    print("Test 4: Creating OdasLive processor...")
    try:
        mic_positions = {
            'mic_0': [0.025, 0.025, 0.025],
            'mic_1': [0.025, -0.025, -0.025],
            'mic_2': [-0.025, 0.025, -0.025],
            'mic_3': [-0.025, -0.025, 0.025],
        }

        processor = OdasLive(
            mic_positions=mic_positions,
            n_channels=4,
            frame_size=512,
            sample_rate=44100
        )
        print("✓ OdasLive processor created successfully")
        print(f"  Channels: {processor.n_channels}")
        print(f"  Sample rate: {processor.sample_rate} Hz")
        print(f"  Frame size: {processor.frame_size} samples")
    except Exception as e:
        print(f"✗ Failed to create processor: {e}")
        import traceback
        traceback.print_exc()

print()
print("=" * 50)
if HAS_C_EXTENSION and all_present:
    print("✓ All tests passed! odas_py is ready to use")
else:
    print("⚠ Some tests failed - check messages above")
print("=" * 50)