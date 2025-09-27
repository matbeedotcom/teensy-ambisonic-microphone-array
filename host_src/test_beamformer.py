#!/usr/bin/env python3
"""
Simple test script for beamforming functionality.
Tests the beamforming algorithms without requiring audio hardware.
"""

import numpy as np
import matplotlib.pyplot as plt
from doa_processing import DOAProcessor
import sounddevice as sd

def simulate_array_recording(num_mics=8, duration=1.0, sample_rate=44100,
                           source_az=45, source_el=30, source_freq=1000):
    """Simulate multi-channel recording with a source at given direction."""

    processor = DOAProcessor()
    N = int(duration * sample_rate)
    t = np.arange(N) / sample_rate

    # Convert source direction to unit vector
    el_rad = np.radians(source_el)
    az_rad = np.radians(source_az)

    direction = np.array([
        np.cos(el_rad) * np.cos(az_rad),
        np.cos(el_rad) * np.sin(az_rad),
        np.sin(el_rad)
    ])

    # Generate source signal
    source_signal = np.sin(2 * np.pi * source_freq * t)

    # Add some noise sources
    noise1 = 0.3 * np.sin(2 * np.pi * 500 * t)  # 500Hz noise
    noise2 = 0.2 * np.sin(2 * np.pi * 2000 * t)  # 2kHz noise

    # Create multi-channel recording
    audio = np.zeros((N, processor.num_mics))

    for i in range(processor.num_mics):
        # Calculate delay for target source
        delay_time = np.dot(direction, processor.positions[i]) / processor.speed_of_sound
        delay_samples = int(delay_time * processor.sample_rate)

        # Apply delay to source
        if delay_samples >= 0:
            audio[delay_samples:, i] = source_signal[:-delay_samples] if delay_samples > 0 else source_signal
        else:
            audio[:delay_samples, i] = source_signal[-delay_samples:]

        # Add noise with random delays
        noise_delay = np.random.randint(-10, 10)
        if noise_delay >= 0:
            audio[noise_delay:, i] += noise1[:-noise_delay] if noise_delay > 0 else noise1
        else:
            audio[:noise_delay, i] += noise1[-noise_delay:]

        # Add ambient noise
        audio[:, i] += np.random.normal(0, 0.05, N)

    return audio, processor


def test_beamforming():
    """Test all beamforming methods."""

    print("Generating simulated 8-channel recording...")
    print("Source: 1kHz tone at Az=45°, El=30°")
    print("Interference: 500Hz noise from random directions")
    print("-" * 60)

    # Generate test signal
    audio, processor = simulate_array_recording(
        source_az=45, source_el=30, source_freq=1000
    )

    # First, estimate DOA
    print("\nEstimating Direction of Arrival:")
    az_srp, el_srp, conf_srp = processor.srp_phat_doa(audio)
    print(f"  SRP-PHAT: Az={az_srp:.1f}°, El={el_srp:.1f}° (conf={conf_srp:.3f})")

    tdoas = processor.compute_tdoa_estimates(audio)
    az_tdoa, el_tdoa, conf_tdoa = processor.least_squares_doa(tdoas)
    print(f"  TDOA-LS:  Az={az_tdoa:.1f}°, El={el_tdoa:.1f}° (conf={conf_tdoa:.3f})")

    # Use best DOA estimate for beamforming
    target_az = az_srp if conf_srp > conf_tdoa else az_tdoa
    target_el = el_srp if conf_srp > conf_tdoa else el_tdoa

    print(f"\nUsing estimated direction: Az={target_az:.1f}°, El={target_el:.1f}°")
    print("-" * 60)

    # Test each beamforming method
    print("\nTesting Beamforming Methods:")

    methods = [
        ("Original (averaged)", np.mean(audio, axis=1)),
        ("Delay-and-Sum", processor.delay_and_sum_beamformer(audio, target_az, target_el)),
        ("MVDR", processor.mvdr_beamformer(audio, target_az, target_el)),
        ("Broadband MVDR", processor.broadband_mvdr_beamformer(audio, target_az, target_el)),
        ("Superdirective", processor.superdirective_beamformer(audio, target_az, target_el))
    ]

    # Analyze results
    sample_rate = processor.sample_rate
    freqs = np.fft.rfftfreq(len(audio), 1/sample_rate)

    # Find frequency indices
    idx_500 = np.argmin(np.abs(freqs - 500))
    idx_1000 = np.argmin(np.abs(freqs - 1000))
    idx_2000 = np.argmin(np.abs(freqs - 2000))

    results = []

    for name, output in methods:
        # Compute spectrum
        spectrum = np.abs(np.fft.rfft(output))

        # Measure power at key frequencies
        power_500 = spectrum[idx_500]
        power_1000 = spectrum[idx_1000]
        power_2000 = spectrum[idx_2000]

        # Calculate SNR (1kHz vs noise)
        noise_power = (power_500 + power_2000) / 2
        snr = 20 * np.log10(power_1000 / (noise_power + 1e-10))

        results.append({
            'name': name,
            'output': output,
            'spectrum': spectrum,
            'snr': snr
        })

        print(f"\n  {name:20s}")
        print(f"    Target (1kHz):  {power_1000:.1f}")
        print(f"    Noise (500Hz):  {power_500:.1f}")
        print(f"    Noise (2kHz):   {power_2000:.1f}")
        print(f"    SNR improvement: {snr:.1f} dB")

    # Plot results
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    fig.suptitle("Beamforming Performance Comparison", fontsize=14)

    for idx, result in enumerate(results):
        if idx >= 6:
            break

        row = idx // 3
        col = idx % 3
        ax = axes[row, col]

        # Plot spectrum (0-3kHz)
        freq_mask = freqs <= 3000
        ax.semilogy(freqs[freq_mask], result['spectrum'][freq_mask])
        ax.set_title(f"{result['name']}\nSNR: {result['snr']:.1f} dB")
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Magnitude")
        ax.grid(True, alpha=0.3)

        # Mark key frequencies
        ax.axvline(500, color='r', linestyle='--', alpha=0.5, label='Noise')
        ax.axvline(1000, color='g', linestyle='--', alpha=0.5, label='Target')
        ax.axvline(2000, color='r', linestyle='--', alpha=0.5)

        if idx == 0:
            ax.legend()

    plt.tight_layout()
    plt.show()

    print("\n" + "=" * 60)
    print("Beamforming test complete!")
    print("\nBest performing method:", max(results, key=lambda x: x['snr'])['name'])

    # Optional: Play the beamformed audio
    play_audio = input("\nPlay beamformed audio? (y/n): ")
    if play_audio.lower() == 'y':
        print("\nPlaying original (averaged) audio...")
        sd.play(results[0]['output'], sample_rate)
        sd.wait()

        best_result = max(results[1:], key=lambda x: x['snr'])
        print(f"\nPlaying {best_result['name']} beamformed audio...")
        sd.play(best_result['output'], sample_rate)
        sd.wait()


if __name__ == "__main__":
    test_beamforming()