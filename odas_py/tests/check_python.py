#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Check Python version and DLL compatibility"""

import sys
import os

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("=" * 60)
print("Python Environment Check")
print("=" * 60)
print()

print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print(f"Python prefix: {sys.prefix}")
print()

# Check if this is Anaconda
is_anaconda = 'anaconda' in sys.version.lower() or 'conda' in sys.version.lower()
print(f"Is Anaconda: {is_anaconda}")
print()

# Check for python313.dll
if sys.platform == 'win32':
    python_dir = os.path.dirname(sys.executable)
    python_dll = f"python{sys.version_info.major}{sys.version_info.minor}.dll"

    # Check in executable directory
    dll_path = os.path.join(python_dir, python_dll)
    dll_exists = os.path.exists(dll_path)

    print(f"Expected DLL: {python_dll}")
    print(f"DLL location: {dll_path}")
    print(f"DLL exists: {dll_exists}")
    print()

    # Check what _odas_core.pyd was built against
    print("=" * 60)
    print("Built Extension Requirements")
    print("=" * 60)
    print()
    print("The _odas_core.pyd extension was built against:")
    print("  Python version: 3.13")
    print("  Python DLL: python313.dll")
    print("  Location: C:\\Python313")
    print()

    if sys.version_info.major == 3 and sys.version_info.minor == 13 and not is_anaconda:
        print("✓ Your Python version matches!")
    else:
        print("✗ Your Python version DOES NOT match")
        print()
        print("SOLUTION:")
        print("  1. Use C:\\Python313\\python.exe instead of anaconda python")
        print("  2. Or rebuild for your Python version:")
        print("     Edit build_windows_from_wsl.sh to use your Python path")
        print()
        print("To use the pre-built extension:")
        print(f"  C:\\Python313\\python.exe test_windows.py")