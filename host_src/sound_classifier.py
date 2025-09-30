"""
Sound classification module for identifying audio types.
Uses frequency analysis and spectral features for classification.
"""

import numpy as np
from scipy import signal
from scipy.fftpack import fft
from typing import Tuple, Dict, List


class SoundClassifier:
    """Classifies audio into categories like voice, music, noise, etc."""

    def __init__(self, sample_rate: int = 44100):
        """Initialize the sound classifier.

        Args:
            sample_rate: Audio sample rate in Hz
        """
        self.sample_rate = sample_rate
        self.nyquist = sample_rate / 2

        # Sound type categories with their typical characteristics
        self.categories = {
            'voice': {
                'fundamental_range': (85, 350),  # Hz - typical voice fundamental frequency
                'formant_ranges': [(700, 1220), (1000, 2600), (2200, 3200)],  # Formant frequencies
                'spectral_centroid_range': (300, 3000),
                'zero_crossing_rate': (0.02, 0.15),
                'harmonicity_threshold': 0.7
            },
            'music': {
                'fundamental_range': (50, 2000),  # Hz - wider range for instruments
                'spectral_centroid_range': (200, 4000),
                'zero_crossing_rate': (0.05, 0.25),
                'harmonicity_threshold': 0.6,
                'rhythm_regularity_threshold': 0.5
            },
            'clap': {
                'spectral_centroid_range': (1500, 8000),  # High frequency content
                'zero_crossing_rate': (0.3, 0.7),
                'duration_range': (0.05, 0.3),  # seconds
                'attack_time': 0.01,  # Very short attack
                'harmonicity_threshold': 0.2  # Low harmonicity
            },
            'whistle': {
                'fundamental_range': (500, 4000),
                'spectral_centroid_range': (800, 4000),
                'harmonicity_threshold': 0.9,  # Very harmonic
                'bandwidth': 200  # Narrow bandwidth
            },
            'noise': {
                'spectral_centroid_range': (0, 20000),
                'zero_crossing_rate': (0.4, 1.0),
                'harmonicity_threshold': 0.3,
                'spectral_flatness_threshold': 0.5
            }
        }

        # Feature extraction parameters
        self.frame_size = 2048
        self.hop_size = 512

        # Classification thresholds
        self.confidence_threshold = 0.5

    def extract_features(self, audio_data: np.ndarray) -> Dict[str, float]:
        """Extract acoustic features from audio signal.

        Args:
            audio_data: Audio samples (mono)

        Returns:
            Dictionary of extracted features
        """
        features = {}

        # Ensure mono audio
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)

        # Normalize audio
        if np.max(np.abs(audio_data)) > 0:
            audio_data = audio_data / np.max(np.abs(audio_data))

        # 1. Zero Crossing Rate
        features['zcr'] = self._compute_zcr(audio_data)

        # 2. Spectral features
        freqs, magnitude_spectrum = self._compute_spectrum(audio_data)

        # Spectral centroid
        features['spectral_centroid'] = self._compute_spectral_centroid(freqs, magnitude_spectrum)

        # Spectral bandwidth
        features['spectral_bandwidth'] = self._compute_spectral_bandwidth(
            freqs, magnitude_spectrum, features['spectral_centroid']
        )

        # Spectral rolloff
        features['spectral_rolloff'] = self._compute_spectral_rolloff(freqs, magnitude_spectrum)

        # Spectral flatness (measure of how noise-like the signal is)
        features['spectral_flatness'] = self._compute_spectral_flatness(magnitude_spectrum)

        # 3. Fundamental frequency and harmonicity
        features['fundamental_freq'], features['harmonicity'] = self._estimate_pitch(audio_data)

        # 4. Energy and dynamics
        features['rms_energy'] = np.sqrt(np.mean(audio_data**2))
        features['peak_energy'] = np.max(np.abs(audio_data))
        features['energy_entropy'] = self._compute_energy_entropy(audio_data)

        # 5. Temporal features
        features['attack_time'] = self._compute_attack_time(audio_data)
        features['temporal_centroid'] = self._compute_temporal_centroid(audio_data)

        # 6. MFCC-like features (simplified)
        features['mfcc_mean'] = self._compute_simple_mfcc(audio_data)

        return features

    def classify(self, audio_data: np.ndarray) -> Tuple[str, float, Dict[str, float]]:
        """Classify audio into a category.

        Args:
            audio_data: Audio samples

        Returns:
            Tuple of (predicted_category, confidence, category_scores)
        """
        # Extract features
        features = self.extract_features(audio_data)

        # Score each category
        category_scores = {}

        for category, params in self.categories.items():
            score = 0.0
            weight_sum = 0.0

            # Check fundamental frequency (if applicable)
            if 'fundamental_range' in params and features['fundamental_freq'] > 0:
                if params['fundamental_range'][0] <= features['fundamental_freq'] <= params['fundamental_range'][1]:
                    score += 2.0
                weight_sum += 2.0

            # Check spectral centroid
            if 'spectral_centroid_range' in params:
                range_min, range_max = params['spectral_centroid_range']
                if range_min <= features['spectral_centroid'] <= range_max:
                    score += 1.5
                weight_sum += 1.5

            # Check zero crossing rate
            if 'zero_crossing_rate' in params:
                range_min, range_max = params['zero_crossing_rate']
                if range_min <= features['zcr'] <= range_max:
                    score += 1.0
                weight_sum += 1.0

            # Check harmonicity
            if 'harmonicity_threshold' in params:
                if category in ['voice', 'whistle', 'music']:
                    # High harmonicity expected
                    if features['harmonicity'] >= params['harmonicity_threshold']:
                        score += 1.5
                else:
                    # Low harmonicity expected
                    if features['harmonicity'] <= params['harmonicity_threshold']:
                        score += 1.0
                weight_sum += 1.5 if category in ['voice', 'whistle', 'music'] else 1.0

            # Special checks for specific categories
            if category == 'clap':
                # Check for short attack time
                if features['attack_time'] < params.get('attack_time', 0.01):
                    score += 1.0
                weight_sum += 1.0

                # Check for high frequency content
                if features['spectral_centroid'] > 1500:
                    score += 0.5
                weight_sum += 0.5

            elif category == 'voice':
                # Check for formant structure (simplified)
                if 300 <= features['spectral_centroid'] <= 3000:
                    if features['harmonicity'] > 0.6:
                        score += 1.0
                    weight_sum += 1.0

            elif category == 'noise':
                # Check spectral flatness
                if features['spectral_flatness'] > params.get('spectral_flatness_threshold', 0.5):
                    score += 1.0
                weight_sum += 1.0

            # Calculate normalized score
            if weight_sum > 0:
                category_scores[category] = score / weight_sum
            else:
                category_scores[category] = 0.0

        # Find best category
        best_category = max(category_scores, key=category_scores.get)
        confidence = category_scores[best_category]

        # If confidence is too low, classify as unknown
        if confidence < self.confidence_threshold:
            best_category = 'unknown'

        return best_category, confidence, category_scores

    def _compute_zcr(self, signal: np.ndarray) -> float:
        """Compute zero crossing rate."""
        zero_crossings = np.sum(np.abs(np.diff(np.sign(signal))) > 0)
        return zero_crossings / len(signal)

    def _compute_spectrum(self, signal: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Compute frequency spectrum."""
        # Apply window
        window = np.hanning(len(signal))
        windowed = signal * window

        # Compute FFT
        spectrum = np.abs(fft(windowed, n=self.frame_size))
        spectrum = spectrum[:self.frame_size // 2]

        # Frequency bins
        freqs = np.linspace(0, self.nyquist, len(spectrum))

        return freqs, spectrum

    def _compute_spectral_centroid(self, freqs: np.ndarray, spectrum: np.ndarray) -> float:
        """Compute spectral centroid (center of mass of spectrum)."""
        if np.sum(spectrum) == 0:
            return 0
        return np.sum(freqs * spectrum) / np.sum(spectrum)

    def _compute_spectral_bandwidth(self, freqs: np.ndarray, spectrum: np.ndarray,
                                   centroid: float) -> float:
        """Compute spectral bandwidth."""
        if np.sum(spectrum) == 0:
            return 0
        return np.sqrt(np.sum(((freqs - centroid) ** 2) * spectrum) / np.sum(spectrum))

    def _compute_spectral_rolloff(self, freqs: np.ndarray, spectrum: np.ndarray,
                                 rolloff_percent: float = 0.85) -> float:
        """Compute spectral rolloff frequency."""
        total_energy = np.sum(spectrum)
        cumulative_energy = np.cumsum(spectrum)
        rolloff_idx = np.where(cumulative_energy >= rolloff_percent * total_energy)[0]
        if len(rolloff_idx) > 0:
            return freqs[rolloff_idx[0]]
        return self.nyquist

    def _compute_spectral_flatness(self, spectrum: np.ndarray) -> float:
        """Compute spectral flatness (geometric mean / arithmetic mean)."""
        # Avoid log(0)
        spectrum_safe = spectrum[spectrum > 1e-10]
        if len(spectrum_safe) == 0:
            return 0

        geometric_mean = np.exp(np.mean(np.log(spectrum_safe)))
        arithmetic_mean = np.mean(spectrum_safe)

        if arithmetic_mean == 0:
            return 0
        return geometric_mean / arithmetic_mean

    def _estimate_pitch(self, signal: np.ndarray) -> Tuple[float, float]:
        """Estimate fundamental frequency and harmonicity using autocorrelation."""
        # Autocorrelation
        autocorr = np.correlate(signal, signal, mode='full')
        autocorr = autocorr[len(autocorr)//2:]

        # Normalize
        if autocorr[0] > 0:
            autocorr = autocorr / autocorr[0]

        # Find first peak after zero lag
        min_period = int(self.sample_rate / 500)  # 500 Hz max frequency
        max_period = int(self.sample_rate / 50)   # 50 Hz min frequency

        if max_period > len(autocorr):
            max_period = len(autocorr) - 1

        if min_period < max_period:
            autocorr_search = autocorr[min_period:max_period]
            if len(autocorr_search) > 0:
                peak_idx = np.argmax(autocorr_search)
                peak_lag = peak_idx + min_period
                harmonicity = autocorr_search[peak_idx]

                if harmonicity > 0.3:  # Threshold for valid pitch
                    fundamental_freq = self.sample_rate / peak_lag
                    return fundamental_freq, harmonicity

        return 0.0, 0.0

    def _compute_attack_time(self, signal: np.ndarray) -> float:
        """Compute attack time (time to reach peak energy)."""
        envelope = np.abs(signal)
        smoothed_envelope = np.convolve(envelope, np.ones(100)/100, mode='same')

        peak_idx = np.argmax(smoothed_envelope)
        peak_value = smoothed_envelope[peak_idx]

        # Find 10% and 90% of peak
        thresh_10 = 0.1 * peak_value
        thresh_90 = 0.9 * peak_value

        # Find indices
        idx_10 = np.where(smoothed_envelope[:peak_idx] >= thresh_10)[0]
        idx_90 = np.where(smoothed_envelope[:peak_idx] >= thresh_90)[0]

        if len(idx_10) > 0 and len(idx_90) > 0:
            attack_samples = idx_90[0] - idx_10[0]
            return attack_samples / self.sample_rate

        return 0.0

    def _compute_temporal_centroid(self, signal: np.ndarray) -> float:
        """Compute temporal centroid (center of mass in time)."""
        envelope = np.abs(signal)
        time_axis = np.arange(len(envelope)) / self.sample_rate

        if np.sum(envelope) == 0:
            return 0
        return np.sum(time_axis * envelope) / np.sum(envelope)

    def _compute_energy_entropy(self, signal: np.ndarray) -> float:
        """Compute energy entropy (measure of abrupt changes)."""
        frame_length = int(0.01 * self.sample_rate)  # 10ms frames
        n_frames = len(signal) // frame_length

        if n_frames == 0:
            return 0

        energies = []
        for i in range(n_frames):
            frame = signal[i*frame_length:(i+1)*frame_length]
            energies.append(np.sum(frame**2))

        energies = np.array(energies)
        if np.sum(energies) == 0:
            return 0

        # Normalize to probability distribution
        energies = energies / np.sum(energies)

        # Compute entropy
        entropy = -np.sum(energies * np.log2(energies + 1e-10))
        return entropy

    def _compute_simple_mfcc(self, signal: np.ndarray) -> float:
        """Compute simplified MFCC-like feature."""
        # This is a simplified version for demonstration
        # A full MFCC implementation would use mel-filterbanks and DCT

        freqs, spectrum = self._compute_spectrum(signal)

        # Simple mel-scale approximation
        mel_spectrum = np.log(spectrum + 1e-10)

        # Take mean of log-mel spectrum as simple feature
        return np.mean(mel_spectrum)

    def get_active_categories(self) -> List[str]:
        """Get list of available sound categories."""
        return list(self.categories.keys()) + ['unknown']