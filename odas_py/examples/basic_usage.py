#!/usr/bin/env python3
"""
Basic ODAS-Py usage example

Demonstrates simple sound source localization using the Python bindings
"""

import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from odas_py import OdasProcessor


def main():
    # Path to ODAS configuration file
    # Adjust this path to point to your config file
    config_file = "../odas/config/tetrahedral_4ch.cfg"

    if not Path(config_file).exists():
        config_file = "../../odas/config/tetrahedral_4ch.cfg"

    if not Path(config_file).exists():
        print(f"Error: Config file not found")
        print("Please specify a valid ODAS config file")
        return 1

    print("=" * 60)
    print("ODAS-Py Basic Usage Example")
    print("=" * 60)

    # Validate configuration
    print(f"\nValidating config: {config_file}")
    if not OdasProcessor.validate_config(config_file):
        print("Config validation failed!")
        return 1

    print("Config validated successfully")

    # Create processor
    print("\nCreating ODAS processor...")
    processor = OdasProcessor(config_file)
    print(f"Processor created: {processor}")

    # Start processing
    print("\nStarting audio processing...")
    processor.start()

    if processor.is_running():
        print("✓ Processor is running")
    else:
        print("✗ Processor failed to start")
        return 1

    # Run for 30 seconds
    duration = 30
    print(f"\nProcessing audio for {duration} seconds...")
    print("Results will be output according to config file sinks")
    print("(Press Ctrl+C to stop early)")

    try:
        for i in range(duration):
            time.sleep(1)
            if (i + 1) % 5 == 0:
                print(f"  {i + 1}s elapsed...")
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")

    # Stop processing
    print("\nStopping processor...")
    processor.stop()

    if not processor.is_running():
        print("✓ Processor stopped successfully")
    else:
        print("✗ Processor still running")
        return 1

    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)

    return 0


def context_manager_example():
    """
    Alternative example using context manager (with statement)
    """
    config_file = "../odas/config/tetrahedral_4ch.cfg"

    print("Context manager example:")

    with OdasProcessor(config_file) as processor:
        print(f"Processing with {processor}")
        time.sleep(10)
        # Processor automatically stops when exiting context

    print("Processor automatically stopped")


if __name__ == '__main__':
    sys.exit(main())