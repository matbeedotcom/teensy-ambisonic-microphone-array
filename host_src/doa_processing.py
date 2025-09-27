"""
Direction of Arrival (DOA) processing using GCC-PHAT and SRP-PHAT algorithms.
Calculates azimuth and elevation angles from multichannel audio data.
"""

import numpy as np
from numpy.fft import rfft, irfft, fft, ifft
from scipy.signal import find_peaks, butter, filtfilt
from scipy.linalg import inv
from typing import List, Tuple, Optional, Dict, Union
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

        # Beamforming parameters
        self.steering_vectors_cache = {}
        self.mvdr_reg = 1e-6  # Regularization for MVDR covariance matrix

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

    def compute_steering_vector(self, azimuth: float, elevation: float, freq: float) -> np.ndarray:
        """
        Compute steering vector for given direction and frequency.

        Args:
            azimuth: Azimuth angle in degrees
            elevation: Elevation angle in degrees
            freq: Frequency in Hz

        Returns:
            Complex steering vector for all microphones
        """
        # Convert angles to unit vector
        el_rad = np.radians(elevation)
        az_rad = np.radians(azimuth)

        direction = np.array([
            np.cos(el_rad) * np.cos(az_rad),
            np.cos(el_rad) * np.sin(az_rad),
            np.sin(el_rad)
        ])

        # Compute delays for each microphone
        wavelength = self.speed_of_sound / freq
        k = 2 * np.pi / wavelength  # Wave number

        steering_vector = np.zeros(self.num_mics, dtype=complex)
        for i in range(self.num_mics):
            # Phase shift due to path difference
            path_diff = np.dot(direction, self.positions[i])
            steering_vector[i] = np.exp(1j * k * path_diff)

        return steering_vector

    def delay_and_sum_beamformer(self, audio_block: np.ndarray,
                                  azimuth: float, elevation: float) -> np.ndarray:
        """
        Delay-and-sum beamformer - simplest beamforming method.
        Applies delays to align signals from target direction and sums them.

        Args:
            audio_block: Multi-channel audio data [samples, channels]
            azimuth: Target azimuth angle in degrees
            elevation: Target elevation angle in degrees

        Returns:
            Beamformed output signal [samples]
        """
        if audio_block.shape[1] != self.num_mics:
            raise ValueError(f"Expected {self.num_mics} channels, got {audio_block.shape[1]}")

        # Convert angles to unit vector
        el_rad = np.radians(elevation)
        az_rad = np.radians(azimuth)

        direction = np.array([
            np.cos(el_rad) * np.cos(az_rad),
            np.cos(el_rad) * np.sin(az_rad),
            np.sin(el_rad)
        ])

        # Calculate delays for each microphone
        delays_seconds = np.zeros(self.num_mics)
        for i in range(self.num_mics):
            # Time for sound to travel from source to microphone
            delays_seconds[i] = -np.dot(direction, self.positions[i]) / self.speed_of_sound

        # Convert to sample delays
        delays_samples = delays_seconds * self.sample_rate

        # Apply fractional delay using frequency domain
        N = len(audio_block)
        output = np.zeros(N)

        for i in range(self.num_mics):
            # FFT of channel
            X = fft(audio_block[:, i])

            # Apply phase shift for fractional delay
            freqs = np.fft.fftfreq(N, 1/self.sample_rate)
            phase_shift = np.exp(-2j * np.pi * freqs * delays_samples[i])
            X_delayed = X * phase_shift

            # IFFT and add to output
            delayed_signal = np.real(ifft(X_delayed))
            output += delayed_signal

        # Normalize by number of microphones
        output /= self.num_mics

        return output

    def mvdr_beamformer(self, audio_block: np.ndarray,
                        azimuth: float, elevation: float,
                        freq_range: Tuple[float, float] = (200, 4000)) -> np.ndarray:
        """
        Minimum Variance Distortionless Response (MVDR) adaptive beamformer.
        Minimizes output power while maintaining unity gain in target direction.

        Args:
            audio_block: Multi-channel audio data [samples, channels]
            azimuth: Target azimuth angle in degrees
            elevation: Target elevation angle in degrees
            freq_range: Frequency range to optimize over (Hz)

        Returns:
            Beamformed output signal [samples]
        """
        if audio_block.shape[1] != self.num_mics:
            raise ValueError(f"Expected {self.num_mics} channels, got {audio_block.shape[1]}")

        N = len(audio_block)

        # Apply window to reduce spectral leakage
        window = np.hanning(N)
        audio_windowed = audio_block * window[:, np.newaxis]

        # FFT of all channels
        X = fft(audio_windowed, axis=0)

        # Frequency bins
        freqs = np.fft.fftfreq(N, 1/self.sample_rate)

        # Find bins within frequency range
        freq_mask = (np.abs(freqs) >= freq_range[0]) & (np.abs(freqs) <= freq_range[1])

        # Output spectrum
        Y = np.zeros(N, dtype=complex)

        for k in range(N):
            if not freq_mask[k]:
                # Outside frequency range, just average
                Y[k] = np.mean(X[k, :])
                continue

            # Compute steering vector for this frequency
            freq = np.abs(freqs[k])
            if freq < 1:  # Avoid DC
                Y[k] = np.mean(X[k, :])
                continue

            steering_vec = self.compute_steering_vector(azimuth, elevation, freq)

            # Estimate covariance matrix at this frequency bin
            # Using single snapshot (instantaneous)
            x_k = X[k, :].reshape(-1, 1)
            R = np.outer(x_k, np.conj(x_k))

            # Add regularization for stability
            R_reg = R + self.mvdr_reg * np.eye(self.num_mics)

            # MVDR weights: w = (R^-1 * a) / (a^H * R^-1 * a)
            # where a is the steering vector
            try:
                R_inv = inv(R_reg)
                numerator = R_inv @ steering_vec.reshape(-1, 1)
                denominator = np.conj(steering_vec.reshape(1, -1)) @ numerator
                weights = numerator / (denominator + self.eps)

                # Apply weights
                Y[k] = (np.conj(weights.T) @ X[k, :])[0, 0]
            except:
                # Fallback to simple averaging if matrix inversion fails
                Y[k] = np.mean(X[k, :])

        # IFFT to get time domain output
        output = np.real(ifft(Y))

        return output

    def broadband_mvdr_beamformer(self, audio_block: np.ndarray,
                                  azimuth: float, elevation: float,
                                  block_size: int = 512) -> np.ndarray:
        """
        Broadband MVDR beamformer using block processing.
        Better for real-time applications.

        Args:
            audio_block: Multi-channel audio data [samples, channels]
            azimuth: Target azimuth angle in degrees
            elevation: Target elevation angle in degrees
            block_size: Processing block size

        Returns:
            Beamformed output signal [samples]
        """
        N = len(audio_block)
        num_blocks = N // block_size
        output = np.zeros(N)

        # Estimate global covariance matrix
        R_global = np.zeros((self.num_mics, self.num_mics), dtype=complex)

        for b in range(num_blocks):
            start = b * block_size
            end = start + block_size
            block = audio_block[start:end, :]

            # Window the block
            window = np.hanning(block_size)
            block_windowed = block * window[:, np.newaxis]

            # FFT
            X = fft(block_windowed, axis=0)

            # Accumulate covariance
            for k in range(block_size // 2):  # Only positive frequencies
                x_k = X[k, :].reshape(-1, 1)
                R_global += np.outer(x_k, np.conj(x_k))

        # Normalize covariance
        R_global /= (num_blocks * block_size // 2)
        R_global += self.mvdr_reg * np.eye(self.num_mics)

        # Process blocks with fixed weights
        for b in range(num_blocks):
            start = b * block_size
            end = start + block_size
            block = audio_block[start:end, :]

            # Apply MVDR with global covariance
            block_output = self._apply_mvdr_weights(block, R_global, azimuth, elevation)

            # Overlap-add (simple rectangular window here)
            output[start:end] = block_output

        return output

    def _apply_mvdr_weights(self, block: np.ndarray, R: np.ndarray,
                           azimuth: float, elevation: float) -> np.ndarray:
        """
        Helper function to apply MVDR weights to a block.
        """
        block_size = len(block)
        window = np.hanning(block_size)
        block_windowed = block * window[:, np.newaxis]

        # FFT
        X = fft(block_windowed, axis=0)
        Y = np.zeros(block_size, dtype=complex)

        freqs = np.fft.fftfreq(block_size, 1/self.sample_rate)

        for k in range(block_size):
            freq = np.abs(freqs[k])
            if freq < 10:  # Skip very low frequencies
                Y[k] = np.mean(X[k, :])
                continue

            # Steering vector
            steering_vec = self.compute_steering_vector(azimuth, elevation, freq)

            # MVDR weights
            try:
                R_inv = inv(R)
                numerator = R_inv @ steering_vec.reshape(-1, 1)
                denominator = np.conj(steering_vec.reshape(1, -1)) @ numerator
                weights = numerator / (denominator + self.eps)

                Y[k] = (np.conj(weights.T) @ X[k, :])[0, 0]
            except:
                Y[k] = np.mean(X[k, :])

        return np.real(ifft(Y))

    def superdirective_beamformer(self, audio_block: np.ndarray,
                                  azimuth: float, elevation: float,
                                  white_noise_gain_constraint: float = -10) -> np.ndarray:
        """
        Superdirective beamformer optimized for maximum directivity.
        Includes white noise gain constraint for robustness.

        Args:
            audio_block: Multi-channel audio data [samples, channels]
            azimuth: Target azimuth angle in degrees
            elevation: Target elevation angle in degrees
            white_noise_gain_constraint: Maximum white noise gain in dB

        Returns:
            Beamformed output signal [samples]
        """
        # Convert white noise gain constraint to linear
        wng_linear = 10 ** (white_noise_gain_constraint / 10)

        N = len(audio_block)
        output = np.zeros(N)

        # Process in frequency domain
        window = np.hanning(N)
        audio_windowed = audio_block * window[:, np.newaxis]
        X = fft(audio_windowed, axis=0)
        Y = np.zeros(N, dtype=complex)

        freqs = np.fft.fftfreq(N, 1/self.sample_rate)

        for k in range(N):
            freq = np.abs(freqs[k])
            if freq < 10:
                Y[k] = np.mean(X[k, :])
                continue

            # Steering vector
            steering_vec = self.compute_steering_vector(azimuth, elevation, freq)

            # Diffuse noise coherence matrix (sinc function for spherical noise field)
            Gamma = np.zeros((self.num_mics, self.num_mics), dtype=complex)
            for i in range(self.num_mics):
                for j in range(self.num_mics):
                    if i == j:
                        Gamma[i, j] = 1.0
                    else:
                        dist = np.linalg.norm(self.positions[i] - self.positions[j])
                        kr = 2 * np.pi * freq * dist / self.speed_of_sound
                        Gamma[i, j] = np.sinc(kr / np.pi)  # sinc(x) = sin(πx)/(πx)

            # Regularize with white noise gain constraint
            Gamma_reg = Gamma + wng_linear * np.eye(self.num_mics)

            # Superdirective weights
            try:
                Gamma_inv = inv(Gamma_reg)
                numerator = Gamma_inv @ steering_vec.reshape(-1, 1)
                denominator = np.conj(steering_vec.reshape(1, -1)) @ numerator
                weights = numerator / (denominator + self.eps)

                Y[k] = (np.conj(weights.T) @ X[k, :])[0, 0]
            except:
                Y[k] = np.mean(X[k, :])

        output = np.real(ifft(Y))
        return output


if __name__ == "__main__":
    # Test the DOA processor with synthetic data
    processor = DOAProcessor()

    # Create synthetic test signal with multiple sources
    N = 2048  # Longer signal for better beamforming
    t = np.arange(N) / processor.sample_rate

    # Source 1: Target at 45° azimuth, 30° elevation (1kHz tone)
    target_az, target_el = 45.0, 30.0
    target_direction = np.array([
        np.cos(np.radians(target_el)) * np.cos(np.radians(target_az)),
        np.cos(np.radians(target_el)) * np.sin(np.radians(target_az)),
        np.sin(np.radians(target_el))
    ])

    # Source 2: Interference at -60° azimuth, 0° elevation (800Hz tone)
    interf_az, interf_el = -60.0, 0.0
    interf_direction = np.array([
        np.cos(np.radians(interf_el)) * np.cos(np.radians(interf_az)),
        np.cos(np.radians(interf_el)) * np.sin(np.radians(interf_az)),
        np.sin(np.radians(interf_el))
    ])

    # Generate test signals
    target_signal = np.sin(2 * np.pi * 1000 * t)  # 1kHz tone
    interf_signal = 0.8 * np.sin(2 * np.pi * 800 * t)  # 800Hz tone (slightly weaker)

    test_audio = np.zeros((N, processor.num_mics))

    # Add target source
    for i in range(processor.num_mics):
        delay_time = np.dot(target_direction, processor.positions[i]) / processor.speed_of_sound
        delay_samples = int(delay_time * processor.sample_rate)

        if delay_samples >= 0:
            test_audio[delay_samples:, i] += target_signal[:-delay_samples] if delay_samples > 0 else target_signal
        else:
            test_audio[:delay_samples, i] += target_signal[-delay_samples:]

    # Add interference source
    for i in range(processor.num_mics):
        delay_time = np.dot(interf_direction, processor.positions[i]) / processor.speed_of_sound
        delay_samples = int(delay_time * processor.sample_rate)

        if delay_samples >= 0:
            test_audio[delay_samples:, i] += interf_signal[:-delay_samples] if delay_samples > 0 else interf_signal
        else:
            test_audio[:delay_samples, i] += interf_signal[-delay_samples:]

    # Add ambient noise
    for i in range(processor.num_mics):
        test_audio[:, i] += np.random.normal(0, 0.05, N)

    print("=" * 60)
    print("DOA ESTIMATION TESTS")
    print("=" * 60)

    # Test SRP-PHAT
    az_srp, el_srp, conf_srp = processor.srp_phat_doa(test_audio)
    print(f"SRP-PHAT: Az={az_srp:.1f}°, El={el_srp:.1f}° (confidence={conf_srp:.3f})")

    # Test TDOA + Least squares
    tdoas = processor.compute_tdoa_estimates(test_audio)
    az_ls, el_ls, conf_ls = processor.least_squares_doa(tdoas)
    print(f"Least-squares: Az={az_ls:.1f}°, El={el_ls:.1f}° (confidence={conf_ls:.3f})")

    print(f"Target source: Az={target_az}°, El={target_el}° (1kHz)")
    print(f"Interference: Az={interf_az}°, El={interf_el}° (800Hz)")

    print("\n" + "=" * 60)
    print("BEAMFORMING TESTS")
    print("=" * 60)

    # Test delay-and-sum beamformer
    print("\n1. Delay-and-Sum Beamformer:")
    beamformed_das = processor.delay_and_sum_beamformer(test_audio, target_az, target_el)

    # Calculate SNR improvement
    mixed_power = np.mean(test_audio ** 2)
    beamformed_power = np.mean(beamformed_das ** 2)

    # Estimate target and interference in beamformed output
    fft_beam = np.abs(np.fft.rfft(beamformed_das))
    freqs = np.fft.rfftfreq(len(beamformed_das), 1/processor.sample_rate)

    idx_1khz = np.argmin(np.abs(freqs - 1000))
    idx_800hz = np.argmin(np.abs(freqs - 800))

    target_gain = fft_beam[idx_1khz] / N
    interf_suppression = fft_beam[idx_800hz] / N

    print(f"   Target (1kHz) relative amplitude: {target_gain:.3f}")
    print(f"   Interference (800Hz) relative amplitude: {interf_suppression:.3f}")
    print(f"   Interference suppression: {20*np.log10(interf_suppression/target_gain):.1f} dB")

    # Test MVDR beamformer
    print("\n2. MVDR Adaptive Beamformer:")
    beamformed_mvdr = processor.mvdr_beamformer(test_audio, target_az, target_el)

    fft_mvdr = np.abs(np.fft.rfft(beamformed_mvdr))
    target_gain_mvdr = fft_mvdr[idx_1khz] / N
    interf_suppression_mvdr = fft_mvdr[idx_800hz] / N

    print(f"   Target (1kHz) relative amplitude: {target_gain_mvdr:.3f}")
    print(f"   Interference (800Hz) relative amplitude: {interf_suppression_mvdr:.3f}")
    print(f"   Interference suppression: {20*np.log10(interf_suppression_mvdr/target_gain_mvdr):.1f} dB")

    # Test broadband MVDR
    print("\n3. Broadband MVDR Beamformer:")
    beamformed_bb_mvdr = processor.broadband_mvdr_beamformer(test_audio, target_az, target_el)

    fft_bb_mvdr = np.abs(np.fft.rfft(beamformed_bb_mvdr))
    target_gain_bb = fft_bb_mvdr[idx_1khz] / N
    interf_suppression_bb = fft_bb_mvdr[idx_800hz] / N

    print(f"   Target (1kHz) relative amplitude: {target_gain_bb:.3f}")
    print(f"   Interference (800Hz) relative amplitude: {interf_suppression_bb:.3f}")
    print(f"   Interference suppression: {20*np.log10(interf_suppression_bb/target_gain_bb):.1f} dB")

    # Test superdirective beamformer
    print("\n4. Superdirective Beamformer:")
    beamformed_super = processor.superdirective_beamformer(test_audio, target_az, target_el)

    fft_super = np.abs(np.fft.rfft(beamformed_super))
    target_gain_super = fft_super[idx_1khz] / N
    interf_suppression_super = fft_super[idx_800hz] / N

    print(f"   Target (1kHz) relative amplitude: {target_gain_super:.3f}")
    print(f"   Interference (800Hz) relative amplitude: {interf_suppression_super:.3f}")
    print(f"   Interference suppression: {20*np.log10(interf_suppression_super/target_gain_super):.1f} dB")

    print("\n" + "=" * 60)
    print("Beamforming successfully implemented!")