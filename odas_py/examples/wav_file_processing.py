#!/usr/bin/env python3
"""
WAV file processing example with ODAS-Py

Demonstrates how to process a WAV file for offline DOA analysis
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from odas_py import OdasProcessor


def process_wav_file(wav_file: str, config_file: str, duration: float = None):
    """
    Process a WAV file through ODAS

    Args:
        wav_file: Path to input WAV file
        config_file: Path to ODAS config file
        duration: Max duration to process (None = entire file)
    """
    wav_path = Path(wav_file)
    if not wav_path.exists():
        print(f"Error: WAV file not found: {wav_file}")
        return 1

    config_path = Path(config_file)
    if not config_path.exists():
        print(f"Error: Config file not found: {config_file}")
        return 1

    print("=" * 60)
    print("ODAS-Py WAV File Processing")
    print("=" * 60)
    print(f"Input:  {wav_file}")
    print(f"Config: {config_file}")

    # Note: For WAV file input, you need to configure the config file
    # to use a file source instead of live audio input

    processor = OdasProcessor(str(config_path))

    print("\nProcessing WAV file...")
    if duration:
        processor.run_for_duration(duration)
    else:
        # Process entire file - in practice you'd want to detect EOF
        # This is a simplified example
        processor.run_for_duration(60.0)

    print("\nProcessing complete!")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='Process WAV file with ODAS',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('wav_file', help='Input WAV file')
    parser.add_argument('--config', '-c',
                        default='../odas/config/tetrahedral_4ch.cfg',
                        help='ODAS config file')
    parser.add_argument('--duration', '-d', type=float,
                        help='Max duration to process (seconds)')

    args = parser.parse_args()

    return process_wav_file(args.wav_file, args.config, args.duration)


if __name__ == '__main__':
    sys.exit(main())