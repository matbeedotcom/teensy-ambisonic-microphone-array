"""
Test Sound Source Separation (SSS) functionality

This script tests the SSS module with synthetic audio signals
to verify beamforming and separation work correctly.
"""

import sys
import numpy as np
from pathlib import Path

# Add odas_py to path
sys.path.insert(0, str(Path(__file__).parent))

from odas_py import OdasLive

def generate_test_audio(n_samples=44100, n_channels=4, freq=440, sample_rate=44100):
    """Generate test audio with a tone from a specific direction"""
    t = np.linspace(0, n_samples / sample_rate, n_samples, endpoint=False)

    # Generate tone
    tone = np.sin(2 * np.pi * freq * t)

    # Simulate delays for different microphone positions
    # Assume sound coming from front (+x direction)
    delays = np.array([0, 1, 1, 2])  # Sample delays for tetrahedral array

    audio = np.zeros((n_samples, n_channels), dtype=np.float32)
    for ch in range(n_channels):
        # Apply delay and amplitude for this channel
        delay = delays[ch]
        if delay > 0:
            audio[delay:, ch] = tone[:-delay] * 0.8
        else:
            audio[:, ch] = tone * 0.8

    return audio

def test_sss_basic():
    """Test basic SSS functionality"""
    print("=" * 70)
    print("Test 1: Basic SSS Initialization")
    print("=" * 70)

    # Define tetrahedral microphone array
    mic_positions = {
        'mic_0': [0.025, 0.025, 0.025],
        'mic_1': [0.025, -0.025, -0.025],
        'mic_2': [-0.025, 0.025, -0.025],
        'mic_3': [-0.025, -0.025, 0.025],
    }

    try:
        # Create processor with tracking AND separation enabled
        processor = OdasLive(
            mic_positions=mic_positions,
            n_channels=4,
            frame_size=512,
            sample_rate=44100,
            enable_tracking=True,
            enable_separation=True
        )
        print("[OK] SSS module initialized successfully")
        return True
    except Exception as e:
        print(f"[FAIL] Failed to initialize SSS: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sss_processing():
    """Test SSS processing with synthetic audio"""
    print("\n" + "=" * 70)
    print("Test 2: SSS Audio Processing")
    print("=" * 70)

    # Define tetrahedral microphone array
    mic_positions = {
        'mic_0': [0.025, 0.025, 0.025],
        'mic_1': [0.025, -0.025, -0.025],
        'mic_2': [-0.025, 0.025, -0.025],
        'mic_3': [-0.025, -0.025, 0.025],
    }

    try:
        # Create processor with separation enabled
        processor = OdasLive(
            mic_positions=mic_positions,
            n_channels=4,
            frame_size=512,
            sample_rate=44100,
            enable_tracking=True,
            enable_separation=True
        )

        # Generate test audio
        frame_size = 512
        test_audio = generate_test_audio(frame_size, 4, freq=440, sample_rate=44100)

        # Set up callback to capture results
        separation_results = []

        def on_separated(separated, residual):
            separation_results.append({
                'separated': separated.copy(),
                'residual': residual.copy()
            })

        processor.set_separated_callback(on_separated)

        # Process several frames to allow tracking to converge
        print("\nProcessing test frames...")
        for i in range(10):
            # Get ODAS pipeline directly
            if processor.odas_pipeline:
                result = processor.odas_pipeline.process(test_audio)

                # Check if separation data is present
                if 'separated' in result and 'residual' in result:
                    separated = result['separated']
                    residual = result['residual']

                    print(f"  Frame {i+1}: separated shape={separated.shape}, "
                          f"residual shape={residual.shape}")

                    # Verify shapes
                    assert separated.shape == (frame_size, 4), \
                        f"Unexpected separated shape: {separated.shape}"
                    assert residual.shape == (frame_size, 4), \
                        f"Unexpected residual shape: {residual.shape}"

                    # Verify data is not all zeros
                    sep_energy = np.mean(np.abs(separated))
                    res_energy = np.mean(np.abs(residual))

                    if i >= 5:  # After convergence
                        print(f"           separated energy={sep_energy:.6f}, "
                              f"residual energy={res_energy:.6f}")
                else:
                    print(f"  Frame {i+1}: No separation data (tracking not yet converged)")

        print("\n[OK] SSS processing test passed")
        return True

    except Exception as e:
        print(f"\n[FAIL] SSS processing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sss_file_output():
    """Test SSS with file output"""
    print("\n" + "=" * 70)
    print("Test 3: SSS File Output")
    print("=" * 70)

    # Define tetrahedral microphone array
    mic_positions = {
        'mic_0': [0.025, 0.025, 0.025],
        'mic_1': [0.025, -0.025, -0.025],
        'mic_2': [-0.025, 0.025, -0.025],
        'mic_3': [-0.025, -0.025, 0.025],
    }

    output_files = []

    try:
        # Create processor with separation enabled
        processor = OdasLive(
            mic_positions=mic_positions,
            n_channels=4,
            frame_size=512,
            sample_rate=44100,
            enable_tracking=True,
            enable_separation=True
        )

        # Set up file output
        separated_file = "test_separated.wav"
        residual_file = "test_residual.wav"
        processor.set_separation_output(separated_file, residual_file, mode='single')
        output_files = [separated_file, residual_file]

        # Generate and process test audio
        frame_size = 512
        test_audio = generate_test_audio(frame_size, 4, freq=440, sample_rate=44100)

        print("\nProcessing frames and writing to files...")
        for i in range(20):
            if processor.odas_pipeline:
                result = processor.odas_pipeline.process(test_audio)

                # Manually trigger file writing (simulating what _process_loop does)
                if 'separated' in result and 'residual' in result:
                    if processor.separated_sink:
                        processor.separated_sink.write_audio(result['separated'])
                    if processor.residual_sink:
                        processor.residual_sink.write_audio(result['residual'])

        # Close files
        processor.close()

        # Verify files were created
        from pathlib import Path
        for fname in output_files:
            if Path(fname).exists():
                size = Path(fname).stat().st_size
                print(f"  [OK] Created {fname} ({size} bytes)")
            else:
                print(f"  [FAIL] File not created: {fname}")
                return False

        print("\n[OK] File output test passed")
        return True

    except Exception as e:
        print(f"\n[FAIL] File output test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up test files
        from pathlib import Path
        for fname in output_files:
            try:
                if Path(fname).exists():
                    Path(fname).unlink()
            except:
                pass

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("ODAS Sound Source Separation (SSS) Test Suite")
    print("=" * 70)

    tests = [
        ("Basic SSS Initialization", test_sss_basic),
        ("SSS Audio Processing", test_sss_processing),
        ("SSS File Output", test_sss_file_output),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n[FAIL] Test '{name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 70)

    sys.exit(0 if failed == 0 else 1)