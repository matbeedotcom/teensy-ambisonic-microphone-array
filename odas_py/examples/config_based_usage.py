#!/usr/bin/env python3
"""
Config-based ODAS-Py example using OdasProcessor

Demonstrates using ODAS with a configuration file (.cfg)
for processing real-time or file-based audio
"""

import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from odas_py import OdasProcessor, HAS_C_EXTENSION


def main():
    print("=" * 60)
    print("ODAS-Py Config-Based Processing Example")
    print("=" * 60)
    print()

    # Check if C extension is available
    if not HAS_C_EXTENSION:
        print("ERROR: C extension not available")
        print("OdasProcessor requires the native extension")
        return 1

    # Path to ODAS configuration file
    config_file = Path(__file__).parent / "config" / "tetrahedral_4ch.cfg"

    if not config_file.exists():
        print(f"Error: Config file not found: {config_file}")
        print()
        print("Please ensure the config file exists at:")
        print(f"  {config_file}")
        return 1

    print(f"Using config file: {config_file.name}")
    print()

    # Validate configuration
    print("Validating config...")
    try:
        is_valid = OdasProcessor.validate_config(str(config_file))
        if not is_valid:
            print("Config validation failed!")
            return 1
    except AttributeError:
        # validate_config may not exist in wrapper
        print("Skipping validation (not available in wrapper)")
    except Exception as e:
        print(f"Config validation error: {e}")
        return 1

    print("Config validated successfully")
    print()

    # Create processor
    print("Creating ODAS processor...")
    try:
        processor = OdasProcessor(str(config_file))
        print("Processor created successfully")
        print()
    except RuntimeError as e:
        print(f"Failed to create processor: {e}")
        print()
        print("Common issues:")
        print("  - Config file syntax errors")
        print("  - Audio device not available")
        print("  - Socket ports already in use")
        return 1

    # Start processing
    print("Starting audio processing...")
    print("(This will use the audio source configured in the .cfg file)")
    print()

    try:
        processor.start()

        if processor.is_running():
            print("Processor is running!")
            print()
            print("Results will be sent to the sinks configured in the .cfg file:")
            print("  - SSL results: socket 127.0.0.1:9001 (JSON)")
            print("  - SST results: socket 127.0.0.1:9000 (JSON)")
            print("  - Separated audio: socket 127.0.0.1:10000 (raw)")
            print()
            print("Processing for 10 seconds...")
            print("Press Ctrl+C to stop early")

            # Process for a fixed duration
            time.sleep(10.0)

            print()
            print("Stopping processor...")
            processor.stop()

            # Wait for clean shutdown
            time.sleep(0.5)

            if not processor.is_running():
                print("Processor stopped successfully")

        else:
            print("ERROR: Processor failed to start")
            return 1

    except KeyboardInterrupt:
        print()
        print()
        print("Interrupted by user, stopping...")
        processor.stop()
        time.sleep(0.5)
    except Exception as e:
        print(f"Error during processing: {e}")
        try:
            processor.stop()
        except:
            pass
        return 1

    print()
    print("=" * 60)
    print("Example completed successfully!")
    print("=" * 60)
    print()
    print("Note: To receive and visualize results, you need to:")
    print("  1. Listen on the configured socket ports")
    print("  2. Parse the JSON/raw data formats")
    print("  3. Use the OdasLive API for callback-based results")
    print()
    print("For easier result handling, see:")
    print("  - examples/example_live_audio.py (callback-based)")
    print("  - examples/example_quickstart.py (OdasLive API)")

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
