"""
Direction of Arrival (DOA) processing using GCC-PHAT and SRP-PHAT algorithms.
Calculates azimuth and elevation angles from multichannel audio data.
"""

import numpy as np
from numpy.fft import rfft, irfft
from scipy.signal import find_peaks
from typing import List, Tuple, Optional, Dict
import json


class DOAProcessor:
    """Direction of Arrival processor using GCC-PHAT and SRP-PHAT methods."""

    def __init__(self, config_file: str = "array_geometry.json"):
        """Initialize DOA processor with array geometry."""
        self.load_config(config_file)
        self.setup_spherical_grid()
        self.precompute_delay_tables()

        # Processing parameters
        self.eps = 1e-12  # Regularization for PHAT weighting
        self.max_lag_samples = self.calculate_max_lag_samples()

    def load_config(self, config_file: str):
        """Load array geometry and configuration."""
        with open(config_file, 'r') as f:
            config = json.load(f)

        self.positions = np.array(config['positions'], dtype=np.float64)
        self.num_mics = len(self.positions)
        self.sample_rate = config['sample_rate']
        self.speed_of_sound = config['speed_of_sound']

        # Generate all microphone pairs
        self.mic_pairs = [(i, j) for i in range(self.num_mics) for j in range(i+1, self.num_mics)]
        self.num_pairs = len(self.mic_pairs)

        print(f"DOA Processor initialized: {self.num_mics} mics, {self.num_pairs} pairs")

    def setup_spherical_grid(self, azimuth_step: float = 5.0, elevation_step: float = 5.0):
        """Create spherical grid for SRP-PHAT search."""
        azimuth_range = np.arange(-180, 180, azimuth_step)
        elevation_range = np.arange(-85, 86, elevation_step)  # Avoid exact poles

        self.grid_directions = []
        for elevation in elevation_range:
            for azimuth in azimuth_range:
                el_rad = np.radians(elevation)
                az_rad = np.radians(azimuth)

                # Convert spherical to Cartesian (unit vector)
                x = np.cos(el_rad) * np.cos(az_rad)
                y = np.cos(el_rad) * np.sin(az_rad)
                z = np.sin(el_rad)

                self.grid_directions.append([x, y, z, azimuth, elevation])

        self.grid_directions = np.array(self.grid_directions)
        self.num_grid_points = len(self.grid_directions)
        print(f"Created spherical grid: {self.num_grid_points} directions")

    def calculate_max_lag_samples(self) -> int:
        """Calculate maximum time delay in samples based on array geometry."""
        # Find maximum distance between any two microphones
        max_distance = 0
        for i in range(self.num_mics):
            for j in range(i+1, self.num_mics):
                dist = np.linalg.norm(self.positions[i] - self.positions[j])
                max_distance = max(max_distance, dist)

        max_time_delay = max_distance / self.speed_of_sound
        max_lag_samples = int(np.ceil(max_time_delay * self.sample_rate))

        # Add some margin for safety
        max_lag_samples = min(max_lag_samples + 5, 50)  # Cap at reasonable value
        print(f"Max lag: {max_lag_samples} samples ({max_time_delay*1000:.2f}ms)")

        return max_lag_samples

    def precompute_delay_tables(self):
        """Precompute expected delays for each direction on the grid."""
        self.delay_tables = {}
        scale_factor = self.sample_rate / self.speed_of_sound

        for pair_idx, (i, j) in enumerate(self.mic_pairs):
            # Vector from mic j to mic i
            baseline_vector = self.positions[i] - self.positions[j]

            # Expected time delays for each grid direction
            # Positive delay means signal arrives at mic i first
            time_delays = np.dot(self.grid_directions[:, :3], baseline_vector)
            sample_delays = np.round(time_delays * scale_factor).astype(int)

            self.delay_tables[pair_idx] = sample_delays

    def gcc_phat_single_pair(self, x1: np.ndarray, x2: np.ndarray) -> Tuple[np.ndarray, int]:
        """
        Compute GCC-PHAT cross-correlation between two signals.

        Args:
            x1, x2: Input signals (same length)

        Returns:
            correlation: Cross-correlation function
            peak_lag: Lag of maximum correlation peak
        """
        # Apply window to reduce spectral leakage
        window = np.hanning(len(x1))
        x1_windowed = x1 * window
        x2_windowed = x2 * window

        # Compute FFTs
        X1 = rfft(x1_windowed)
        X2 = rfft(x2_windowed)

        # Cross-spectrum
        cross_spectrum = X1 * np.conj(X2)

        # PHAT weighting (phase transform)
        phat_weights = cross_spectrum / (np.abs(cross_spectrum) + self.eps)

        # IFFT to get correlation function
        correlation = irfft(phat_weights)

        # Find peak within allowed lag range
        N = len(correlation)
        allowed_lags = min(self.max_lag_samples, N//2)

        # Check both positive and negative lags
        positive_lags = correlation[:allowed_lags+1]
        negative_lags = correlation[N-allowed_lags:]

        # Find peaks
        pos_peaks, _ = find_peaks(positive_lags)
        neg_peaks, _ = find_peaks(negative_lags)

        # Get best peak
        best_lag = 0
        best_value = correlation[0]

        if len(pos_peaks) > 0:
            best_pos_idx = pos_peaks[np.argmax(positive_lags[pos_peaks])]
            if positive_lags[best_pos_idx] > best_value:
                best_lag = best_pos_idx
                best_value = positive_lags[best_pos_idx]

        if len(neg_peaks) > 0:
            best_neg_idx = neg_peaks[np.argmax(negative_lags[neg_peaks])]
            neg_lag = N - allowed_lags + best_neg_idx
            if negative_lags[best_neg_idx] > best_value:
                best_lag = -(allowed_lags - best_neg_idx)
                best_value = negative_lags[best_neg_idx]

        return correlation, best_lag

    def compute_tdoa_estimates(self, audio_block: np.ndarray) -> np.ndarray:
        """
        Compute TDOA estimates for all microphone pairs.

        Args:
            audio_block: Multi-channel audio data [samples, channels]

        Returns:
            tdoa_estimates: Array of TDOA estimates for each pair [samples]
        """
        if audio_block.shape[1] != self.num_mics:
            raise ValueError(f"Expected {self.num_mics} channels, got {audio_block.shape[1]}")

        tdoa_estimates = np.zeros(self.num_pairs)

        for pair_idx, (i, j) in enumerate(self.mic_pairs):
            correlation, peak_lag = self.gcc_phat_single_pair(
                audio_block[:, i], audio_block[:, j]
            )
            tdoa_estimates[pair_idx] = peak_lag

        return tdoa_estimates

    def srp_phat_doa(self, audio_block: np.ndarray) -> Tuple[float, float, float]:
        """
        Perform SRP-PHAT DOA estimation.

        Args:
            audio_block: Multi-channel audio data [samples, channels]

        Returns:
            azimuth: Azimuth angle in degrees
            elevation: Elevation angle in degrees
            confidence: Confidence score
        """
        N = len(audio_block)
        window = np.hanning(N)

        # Compute windowed FFTs for all channels
        audio_windowed = audio_block * window[:, np.newaxis]
        X = rfft(audio_windowed, axis=0)

        # Accumulate SRP values for each grid direction
        srp_values = np.zeros(self.num_grid_points)

        for pair_idx, (i, j) in enumerate(self.mic_pairs):
            # Cross-spectrum with PHAT weighting
            cross_spectrum = X[:, i] * np.conj(X[:, j])
            phat_weights = cross_spectrum / (np.abs(cross_spectrum) + self.eps)

            # IFFT to get correlation
            correlation = irfft(phat_weights)

            # Sample correlation at expected delays for this pair
            expected_delays = self.delay_tables[pair_idx]

            # Wrap delays to valid indices
            valid_indices = expected_delays % N
            srp_contribution = correlation[valid_indices]

            srp_values += srp_contribution

        # Find maximum
        best_idx = np.argmax(srp_values)
        best_direction = self.grid_directions[best_idx]

        azimuth = best_direction[3]
        elevation = best_direction[4]
        confidence = srp_values[best_idx] / self.num_pairs  # Normalize

        return azimuth, elevation, confidence

    def least_squares_doa(self, tdoa_estimates: np.ndarray) -> Tuple[float, float, float]:
        """
        Perform least-squares DOA estimation using TDOA measurements.

        Args:
            tdoa_estimates: TDOA estimates for all pairs [samples]

        Returns:
            azimuth: Azimuth angle in degrees
            elevation: Elevation angle in degrees
            confidence: Confidence score (residual-based)
        """
        # Convert sample delays to time delays
        time_delays = tdoa_estimates / self.sample_rate

        best_error = float('inf')
        best_direction = None

        # Grid search over sphere
        for direction in self.grid_directions:
            unit_vector = direction[:3]

            # Compute expected TDOAs for this direction
            expected_tdoas = []
            for i, j in self.mic_pairs:
                baseline = self.positions[i] - self.positions[j]
                expected_delay = np.dot(unit_vector, baseline) / self.speed_of_sound
                expected_tdoas.append(expected_delay)

            expected_tdoas = np.array(expected_tdoas)

            # Compute residual error
            error = np.sum((time_delays - expected_tdoas) ** 2)

            if error < best_error:
                best_error = error
                best_direction = direction

        azimuth = best_direction[3]
        elevation = best_direction[4]
        confidence = 1.0 / (1.0 + best_error * 1000)  # Convert to confidence

        return azimuth, elevation, confidence


if __name__ == "__main__":
    # Test the DOA processor with synthetic data
    processor = DOAProcessor()

    # Create synthetic test signal (4 channels, 1024 samples)
    N = 1024
    t = np.arange(N) / processor.sample_rate

    # Simulate a source at 45° azimuth, 30° elevation
    true_az, true_el = 45.0, 30.0
    true_direction = np.array([
        np.cos(np.radians(true_el)) * np.cos(np.radians(true_az)),
        np.cos(np.radians(true_el)) * np.sin(np.radians(true_az)),
        np.sin(np.radians(true_el))
    ])

    # Generate test signal with appropriate delays
    base_signal = np.sin(2 * np.pi * 1000 * t)  # 1kHz tone
    test_audio = np.zeros((N, processor.num_mics))

    for i in range(processor.num_mics):
        # Calculate delay for this microphone
        delay_time = np.dot(true_direction, processor.positions[i]) / processor.speed_of_sound
        delay_samples = int(delay_time * processor.sample_rate)

        # Apply delay and add some noise
        if delay_samples >= 0:
            test_audio[delay_samples:, i] = base_signal[:-delay_samples] if delay_samples > 0 else base_signal
        else:
            test_audio[:delay_samples, i] = base_signal[-delay_samples:]

        test_audio[:, i] += np.random.normal(0, 0.1, N)  # Add noise

    # Test SRP-PHAT
    az_srp, el_srp, conf_srp = processor.srp_phat_doa(test_audio)
    print(f"SRP-PHAT: Az={az_srp:.1f}°, El={el_srp:.1f}° (confidence={conf_srp:.3f})")

    # Test TDOA + Least squares
    tdoas = processor.compute_tdoa_estimates(test_audio)
    az_ls, el_ls, conf_ls = processor.least_squares_doa(tdoas)
    print(f"Least-squares: Az={az_ls:.1f}°, El={el_ls:.1f}° (confidence={conf_ls:.3f})")

    print(f"True direction: Az={true_az}°, El={true_el}°")