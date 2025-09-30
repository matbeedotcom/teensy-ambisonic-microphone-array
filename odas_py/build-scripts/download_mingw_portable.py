#!/usr/bin/env python3
"""
Download portable MinGW-w64 toolchain for cross-compiling ODAS on Windows.
This allows Python's build system to compile C extensions without requiring
a full MinGW installation.
"""

import os
import sys
import urllib.request
import tarfile
import zipfile
import shutil
from pathlib import Path

# Portable MinGW-w64 releases
# Using both .7z (smaller) and .zip (easier to extract) options
MINGW_RELEASES = {
    'x86_64': {
        '7z': {
            'url': 'https://github.com/niXman/mingw-builds-binaries/releases/download/13.2.0-rt_v11-rev1/x86_64-13.2.0-release-posix-seh-msvcrt-rt_v11-rev1.7z',
            'filename': 'mingw64.7z',
        },
        'zip': {
            # WinLibs standalone build (alternative with .zip)
            'url': 'https://github.com/brechtsanders/winlibs_mingw/releases/download/15.2.0posix-13.0.0-msvcrt-r1/winlibs-x86_64-posix-seh-gcc-15.2.0-mingw-w64msvcrt-13.0.0-r1.zip',
            'filename': 'mingw64.zip',
        },
        'extract_dir': 'mingw64'
    },
    'i686': {
        '7z': {
            'url': 'https://github.com/niXman/mingw-builds-binaries/releases/download/13.2.0-rt_v11-rev1/i686-13.2.0-release-posix-dwarf-msvcrt-rt_v11-rev1.7z',
            'filename': 'mingw32.7z',
        },
        'extract_dir': 'mingw32'
    }
}

def download_file(url, dest):
    """Download a file with progress indicator."""
    print(f"Downloading {url}...")

    def reporthook(count, block_size, total_size):
        percent = int(count * block_size * 100 / total_size)
        sys.stdout.write(f"\r{percent}% [{count * block_size}/{total_size} bytes]")
        sys.stdout.flush()

    urllib.request.urlretrieve(url, dest, reporthook)
    print("\nDownload complete!")

def extract_7z(archive_path, extract_to):
    """Extract .7z archive using py7zr or fallback to system 7z."""
    import subprocess

    # Try py7zr first (Python library)
    try:
        import py7zr
        print("Extracting with py7zr...")
        with py7zr.SevenZipFile(archive_path, 'r') as archive:
            archive.extractall(path=extract_to)
        print("Extraction complete!")
        return True
    except ImportError:
        pass

    # Try system 7z command
    for cmd in ['7z', '7za', 'C:\\Program Files\\7-Zip\\7z.exe']:
        try:
            print(f"Extracting with {cmd}...")
            result = subprocess.run(
                [cmd, 'x', f'-o{extract_to}', str(archive_path), '-y'],
                check=True,
                capture_output=True,
                text=True
            )
            print("Extraction complete!")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue

    # All methods failed
    print("\nERROR: Cannot extract .7z file.")
    print("\nPlease install one of the following:")
    print("  1. py7zr:  pip install py7zr")
    print("  2. 7-Zip:  winget install 7zip.7zip")
    print("     or download from https://www.7-zip.org/")
    print("\nAlternatively, manually extract the archive:")
    print(f"  Archive: {archive_path}")
    print(f"  Extract to: {extract_to}")
    return False

def download_mingw(arch='x86_64', install_dir=None, prefer_zip=False):
    """Download and extract portable MinGW-w64."""
    if arch not in MINGW_RELEASES:
        print(f"ERROR: Unsupported architecture: {arch}")
        return None

    release_formats = MINGW_RELEASES[arch]

    if install_dir is None:
        install_dir = Path(__file__).parent.parent / 'mingw-portable'
    else:
        install_dir = Path(install_dir)

    install_dir.mkdir(parents=True, exist_ok=True)

    mingw_dir = install_dir / release_formats['extract_dir']

    # Check if already installed
    gcc_exe = mingw_dir / 'bin' / 'gcc.exe'
    if gcc_exe.exists():
        print(f"MinGW-w64 already installed at {mingw_dir}")
        return mingw_dir

    # Choose format: prefer .zip if requested or .7z not available
    format_order = ['zip', '7z'] if prefer_zip else ['7z', 'zip']

    for fmt in format_order:
        if fmt not in release_formats:
            continue

        release = release_formats[fmt]
        archive_path = install_dir / release['filename']

        # Download if not exists
        if not archive_path.exists():
            download_file(release['url'], archive_path)

        # Try to extract
        print(f"Extracting to {install_dir}...")

        if fmt == 'zip':
            try:
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(install_dir)
                print("Extraction complete!")
                success = True
            except Exception as e:
                print(f"Zip extraction failed: {e}")
                success = False
        else:  # .7z
            success = extract_7z(archive_path, install_dir)

        if success:
            # Check if extraction worked
            if gcc_exe.exists():
                print(f"MinGW-w64 installed successfully at {mingw_dir}")
                # Cleanup archive
                if archive_path.exists():
                    archive_path.unlink()
                return mingw_dir
            else:
                print(f"Warning: Extraction succeeded but gcc not found at {gcc_exe}")

    print("ERROR: Failed to download and extract MinGW-w64")
    return None

def create_cmake_toolchain(mingw_dir, output_file=None):
    """Create CMake toolchain file for the portable MinGW."""
    mingw_dir = Path(mingw_dir)

    if output_file is None:
        output_file = Path(__file__).parent / 'toolchain-mingw-portable.cmake'
    else:
        output_file = Path(output_file)

    # Convert to CMake-style path
    mingw_path_cmake = str(mingw_dir).replace('\\', '/')

    toolchain_content = f"""# CMake toolchain file for portable MinGW-w64
# Generated by download_mingw_portable.py

set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_SYSTEM_PROCESSOR x86_64)

# Specify the cross compiler
set(CMAKE_C_COMPILER "{mingw_path_cmake}/bin/x86_64-w64-mingw32-gcc.exe")
set(CMAKE_CXX_COMPILER "{mingw_path_cmake}/bin/x86_64-w64-mingw32-g++.exe")
set(CMAKE_RC_COMPILER "{mingw_path_cmake}/bin/x86_64-w64-mingw32-windres.exe")

# Where to find the target environment
set(CMAKE_FIND_ROOT_PATH "{mingw_path_cmake}")

# Adjust the behavior of FIND_XXX() commands
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)

# Specify the ranlib tool
set(CMAKE_RANLIB "{mingw_path_cmake}/bin/x86_64-w64-mingw32-ranlib.exe")
set(CMAKE_AR "{mingw_path_cmake}/bin/x86_64-w64-mingw32-ar.exe")

# Set the resource compiler
set(CMAKE_RC_COMPILE_OBJECT "<CMAKE_RC_COMPILER> -O coff <FLAGS> <DEFINES> <INCLUDES> <SOURCE> <OBJECT>")
"""

    output_file.write_text(toolchain_content)
    print(f"CMake toolchain file created: {output_file}")
    return output_file

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Download portable MinGW-w64 toolchain')
    parser.add_argument('--arch', default='x86_64', choices=['x86_64', 'i686'],
                        help='Target architecture (default: x86_64)')
    parser.add_argument('--install-dir', help='Installation directory (default: ../mingw-portable)')
    parser.add_argument('--toolchain-file', help='Output CMake toolchain file')
    parser.add_argument('--prefer-zip', action='store_true',
                        help='Prefer .zip over .7z format (easier to extract, but larger download)')

    args = parser.parse_args()

    mingw_dir = download_mingw(args.arch, args.install_dir, args.prefer_zip)
    if mingw_dir:
        create_cmake_toolchain(mingw_dir, args.toolchain_file)
        print("\nMinGW-w64 setup complete!")
        print(f"  Toolchain: {mingw_dir}")
        print(f"  Add to PATH: {mingw_dir / 'bin'}")
        return 0
    else:
        print("\nMinGW-w64 setup failed!")
        return 1

if __name__ == '__main__':
    sys.exit(main())
