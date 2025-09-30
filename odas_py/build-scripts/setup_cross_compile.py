#!/usr/bin/env python3
"""
Setup helper for cross-compiling ODAS Python extensions.
Automatically downloads MinGW-w64 if needed when building on Windows.

Usage in setup.py:
    from build_scripts.setup_cross_compile import setup_mingw_env

    class BuildExtension(build_ext):
        def build_extensions(self):
            if sys.platform == 'win32':
                setup_mingw_env()
            super().build_extensions()
"""

import os
import sys
import subprocess
from pathlib import Path

def get_mingw_path():
    """Get or download portable MinGW-w64 toolchain."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    mingw_dir = project_root / 'mingw-portable' / 'mingw64'

    # Check if already installed
    gcc_exe = mingw_dir / 'bin' / 'gcc.exe'
    if gcc_exe.exists():
        print(f"Using existing MinGW-w64 at {mingw_dir}")
        return mingw_dir

    # Download MinGW
    print("MinGW-w64 not found, downloading...")
    download_script = script_dir / 'download_mingw_portable.py'

    try:
        subprocess.run([
            sys.executable,
            str(download_script),
            '--install-dir', str(project_root / 'mingw-portable')
        ], check=True)
    except subprocess.CalledProcessError:
        print("ERROR: Failed to download MinGW-w64")
        return None

    if gcc_exe.exists():
        return mingw_dir
    else:
        return None

def setup_mingw_env():
    """Setup environment for MinGW cross-compilation."""
    mingw_dir = get_mingw_path()
    if not mingw_dir:
        raise RuntimeError("Could not setup MinGW-w64 toolchain")

    # Add MinGW to PATH
    mingw_bin = str(mingw_dir / 'bin')
    if mingw_bin not in os.environ['PATH']:
        os.environ['PATH'] = mingw_bin + os.pathsep + os.environ['PATH']
        print(f"Added {mingw_bin} to PATH")

    # Set compiler environment variables
    os.environ['CC'] = 'gcc'
    os.environ['CXX'] = 'g++'
    os.environ['AR'] = 'ar'
    os.environ['RANLIB'] = 'ranlib'

    return mingw_dir

def get_cmake_toolchain_file():
    """Get CMake toolchain file for MinGW cross-compilation."""
    script_dir = Path(__file__).parent
    toolchain_file = script_dir / 'toolchain-mingw-portable.cmake'

    if not toolchain_file.exists():
        # Generate it
        mingw_dir = get_mingw_path()
        if mingw_dir:
            from download_mingw_portable import create_cmake_toolchain
            create_cmake_toolchain(mingw_dir, toolchain_file)

    return toolchain_file if toolchain_file.exists() else None

class MinGWCMakeExtension:
    """
    Helper class for building CMake extensions with MinGW.

    Usage:
        from setuptools import setup, Extension
        from setuptools.command.build_ext import build_ext

        class CMakeBuild(build_ext):
            def run(self):
                helper = MinGWCMakeExtension()
                helper.configure_cmake(self)
                super().run()
    """

    def __init__(self):
        self.mingw_dir = None
        self.toolchain_file = None

    def configure_cmake(self, build_ext_cmd):
        """Configure CMake for MinGW cross-compilation."""
        if sys.platform != 'win32':
            return  # Only needed on Windows

        # Setup MinGW
        self.mingw_dir = setup_mingw_env()
        self.toolchain_file = get_cmake_toolchain_file()

        # Add CMake arguments for cross-compilation
        if not hasattr(build_ext_cmd, 'cmake_args'):
            build_ext_cmd.cmake_args = []

        if self.toolchain_file:
            build_ext_cmd.cmake_args.extend([
                f'-DCMAKE_TOOLCHAIN_FILE={self.toolchain_file}',
                '-DCMAKE_BUILD_TYPE=Release',
            ])

        print("CMake configured for MinGW cross-compilation")

def main():
    """Test the setup."""
    print("Testing MinGW setup...")
    mingw_dir = setup_mingw_env()
    print(f"MinGW directory: {mingw_dir}")

    toolchain = get_cmake_toolchain_file()
    print(f"Toolchain file: {toolchain}")

    # Test gcc
    try:
        result = subprocess.run(['gcc', '--version'], capture_output=True, text=True)
        print("\nGCC version:")
        print(result.stdout)
    except FileNotFoundError:
        print("ERROR: gcc not found in PATH")

if __name__ == '__main__':
    main()
