"""
Debug STFT processing to understand why SSL isn't detecting sources
"""

import sys
import numpy as np
from pathlib import Path
import wave

sys.path.insert(0, str(Path(__file__).parent))

from odas_py import OdasLive

def load_wav_file(filename, n_channels=4):
    """Load WAV file"""
    with wave.open(filename, 'rb') as wav:
        sample_rate = wav.getframerate()
        n_frames = wav.getnframes()
        n_ch = wav.getnchannels()
        sample_width = wav.getsampwidth()
        audio_bytes = wav.readframes(n_frames)

        print(f"  WAV info: {n_frames} frames, {n_ch} channels, {sample_width} bytes/sample, {sample_rate} Hz")

        # Convert based on sample width
        if sample_width == 4:
            audio = np.frombuffer(audio_bytes, dtype=np.int32).astype(np.float32)
            audio = audio / (2**31)  # Normalize to [-1, 1]
        elif sample_width == 2:
            audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
            audio = audio / (2**15)
        else:
            raise ValueError(f"Unsupported sample width: {sample_width}")

        # Reshape to (samples, channels)
        audio = audio.reshape(-1, n_ch)

        return audio, sample_rate

# Define tetrahedral array
mic_positions = {
    'mic_0': [0.025, 0.025, 0.025],
    'mic_1': [0.025, -0.025, -0.025],
    'mic_2': [-0.025, 0.025, -0.025],
    'mic_3': [-0.025, -0.025, 0.025],
}

# Load audio
wav_file = "../windows_odas_app/input_raw_4ch.wav"
print(f"Loading {wav_file}...")
audio, sample_rate = load_wav_file(wav_file, n_channels=4)
print(f"Audio shape: {audio.shape}, sample_rate: {sample_rate}")
print(f"Audio range: [{audio.min():.6f}, {audio.max():.6f}]")
print(f"Audio RMS per channel: {[np.sqrt(np.mean(audio[:, ch]**2)) for ch in range(4)]}")

# Create processor
processor = OdasLive(
    mic_positions=mic_positions,
    n_channels=4,
    frame_size=512,
    sample_rate=44100,
    enable_tracking=False,
    enable_separation=False
)

if not processor.odas_pipeline:
    print("ERROR: ODAS C extension not available")
    sys.exit(1)

# Process frames - need to skip initial frames for STFT to warm up
frame_size = 512
n_warmup_frames = 2  # Skip first 2 frames for STFT to initialize
n_test_frames = 60  # Test more frames to see patterns

print(f"\nProcessing {n_warmup_frames + n_test_frames} frames (first {n_warmup_frames} for warmup)...")
print("=" * 80)

for frame_idx in range(n_warmup_frames + n_test_frames):
    start_idx = frame_idx * frame_size
    end_idx = start_idx + frame_size

    if end_idx > len(audio):
        break

    frame = audio[start_idx:end_idx, :]

    # Process
    result = processor.odas_pipeline.process(frame)

    # Skip warmup frames from output
    if frame_idx < n_warmup_frames:
        continue

    # Check frame statistics
    frame_rms = np.sqrt(np.mean(frame**2))
    frame_max = np.max(np.abs(frame))

    print(f"\nFrame {frame_idx}:")
    print(f"  Input RMS: {frame_rms:.6f}, Max: {frame_max:.6f}")

    # Check pots
    pots = result['pots']
    max_pot_value = max([p['value'] for p in pots]) if pots else 0
    active_pots = [p for p in pots if p['value'] > 0.01]

    print(f"  SSL: {len(active_pots)} active pots (max value: {max_pot_value:.6f})")

    if active_pots:
        for i, pot in enumerate(active_pots[:3]):
            print(f"    Pot {i}: value={pot['value']:.4f}, "
                  f"pos=({pot['x']:.3f}, {pot['y']:.3f}, {pot['z']:.3f})")

print("\n" + "=" * 80)
print("Debug complete")
