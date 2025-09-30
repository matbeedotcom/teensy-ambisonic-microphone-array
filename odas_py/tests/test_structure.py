#!/usr/bin/env python3
"""
Quick structure test for ODAS-Py (without building native extension)
"""

import sys
from pathlib import Path

def test_structure():
    """Verify directory structure and files exist"""

    print("ODAS-Py Structure Test")
    print("=" * 60)

    errors = []
    warnings = []

    # Check required files
    required_files = [
        'setup.py',
        'CMakeLists.txt',
        'README.md',
        'BUILD.md',
        'requirements.txt',
        'odas_py/__init__.py',
        'odas_py/odas_processor.py',
        'odas_py/version.py',
        'src/odas_core.c',
        'src/odas_wrapper.c',
        'include/odas_wrapper.h',
        'examples/basic_usage.py',
        'examples/wav_file_processing.py',
    ]

    print("\nChecking required files:")
    for file in required_files:
        path = Path(file)
        if path.exists():
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} - MISSING")
            errors.append(f"Missing file: {file}")

    # Check ODAS library
    print("\nChecking ODAS library:")
    odas_lib_paths = [
        '../odas/build/libodas.a',
        '../odas/build-mingw/libodas.a',
    ]

    odas_found = False
    for lib_path in odas_lib_paths:
        if Path(lib_path).exists():
            print(f"  ✓ Found: {lib_path}")
            odas_found = True
            break

    if not odas_found:
        print(f"  ⚠ ODAS library not found (need to build first)")
        warnings.append("ODAS library not built - required for compilation")

    # Check Python packages
    print("\nChecking Python dependencies:")
    try:
        import numpy
        print(f"  ✓ numpy {numpy.__version__}")
    except ImportError:
        print(f"  ✗ numpy - NOT INSTALLED")
        errors.append("NumPy not installed (pip install numpy)")

    # Try importing module (will fail if not built)
    print("\nChecking module import:")
    try:
        sys.path.insert(0, str(Path.cwd()))
        from odas_py import __version__
        print(f"  ✓ odas_py module structure OK (version {__version__})")

        try:
            from odas_py import OdasProcessor
            print(f"  ✓ OdasProcessor class available")
        except RuntimeError as e:
            if "native module not available" in str(e).lower():
                print(f"  ⚠ Native extension not built yet (expected)")
                warnings.append("Native extension not built - run build.sh to build")
            else:
                raise

    except Exception as e:
        print(f"  ✗ Import failed: {e}")
        errors.append(f"Module import error: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if errors:
        print(f"\n❌ {len(errors)} ERROR(S):")
        for error in errors:
            print(f"  - {error}")

    if warnings:
        print(f"\n⚠️  {len(warnings)} WARNING(S):")
        for warning in warnings:
            print(f"  - {warning}")

    if not errors:
        if warnings:
            print("\n✓ Structure is correct!")
            print("\nNext steps:")
            print("  1. Build ODAS library: cd ../odas && bash build_mingw.sh")
            print("  2. Build Python extension: bash build.sh")
            print("  3. Test: python3 examples/basic_usage.py")
        else:
            print("\n✅ All checks passed!")
            print("\nReady to use! Try:")
            print("  python3 examples/basic_usage.py")
        return 0
    else:
        print("\n❌ Fix errors above before proceeding")
        return 1

if __name__ == '__main__':
    sys.exit(test_structure())