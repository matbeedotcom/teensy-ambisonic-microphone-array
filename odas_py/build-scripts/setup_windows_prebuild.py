#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Setup script for using pre-built odas_py binaries on Windows
This avoids the need to rebuild with pip install
"""

import sys
import os
import shutil

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("=" * 60)
print("Setting up odas_py with pre-built binaries")
print("=" * 60)
print()

# Get site-packages directory
import site
site_packages = site.getsitepackages()[0]
print(f"Target directory: {site_packages}")
print()

# Source directory
script_dir = os.path.dirname(os.path.abspath(__file__))
source_dir = os.path.join(script_dir, 'odas_py')

# Check files exist
required_files = [
    '_odas_core.pyd',
    'libodas.dll',
    'libwinpthread-1.dll',
    '__init__.py',
    'odaslive.py',
    'version.py'
]

print("Checking required files...")
missing = []
for filename in required_files:
    filepath = os.path.join(source_dir, filename)
    if os.path.exists(filepath):
        size = os.path.getsize(filepath) / 1024
        print(f"  ✓ {filename:25s} ({size:.1f} KB)")
    else:
        print(f"  ✗ {filename:25s} MISSING!")
        missing.append(filename)

if missing:
    print()
    print("ERROR: Missing files. Please build first:")
    print("  bash build_windows_from_wsl.sh")
    sys.exit(1)

print()
print("Creating odas_py package in site-packages...")

# Create package directory
target_dir = os.path.join(site_packages, 'odas_py')
os.makedirs(target_dir, exist_ok=True)

# Copy all Python files and binaries
files_to_copy = [
    '__init__.py',
    'odaslive.py',
    'version.py',
    'odas_processor.py',
    '_odas_core.pyd',
    'libodas.dll',
    'libwinpthread-1.dll'
]

print(f"Copying files to {target_dir}...")
for filename in files_to_copy:
    src = os.path.join(source_dir, filename)
    dst = os.path.join(target_dir, filename)
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f"  ✓ Copied {filename}")

print()
print("Testing installation...")
try:
    # Force reimport
    if 'odas_py' in sys.modules:
        del sys.modules['odas_py']

    from odas_py import OdasLive, HAS_C_EXTENSION
    print(f"  ✓ Import successful")
    print(f"  ✓ C extension available: {HAS_C_EXTENSION}")

    if not HAS_C_EXTENSION:
        print()
        print("  ⚠ Warning: C extension not loading")
        print("  This usually means a DLL dependency issue")

except Exception as e:
    print(f"  ✗ Import failed: {e}")
    sys.exit(1)

print()
print("=" * 60)
print("✓ Installation complete!")
print("=" * 60)
print()
print("You can now use odas_py from anywhere:")
print("  python -c \"from odas_py import OdasLive; print('Works!')\"")
print()
print("To uninstall:")
print(f"  rmdir /s \"{target_dir}\"")