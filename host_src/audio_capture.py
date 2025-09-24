"""
Audio capture module for Teensy ambisonic microphone array.
Handles USB audio interface detection and streaming.
"""

import sounddevice as sd
import numpy as np
import json
from typing import Optional, Callable, Dict, Any
import time


class TeensyAudioCapture:
    """Handles audio capture from Teensy USB audio device."""

    def __init__(self, config_file: str = "array_geometry.json"):
        """Initialize audio capture with configuration."""
        self.load_config(config_file)
        self.device_id = None
        self.stream = None
        self.callback_func = None
        self.is_running = False

    def load_config(self, config_file: str):
        """Load array configuration from JSON file."""
        try:
            with open(config_file, 'r') as f:
                self.config = json.load(f)
            self.sample_rate = self.config['sample_rate']
            self.num_channels = len(self.config['positions'])
            print(f"Loaded config: {self.config['name']} - {self.num_channels} channels @ {self.sample_rate}Hz")
        except FileNotFoundError:
            print(f"Warning: {config_file} not found, using defaults")
            self.sample_rate = 44100
            self.num_channels = 4
            self.config = {"name": "default", "positions": [[0,0,0]] * 4}

    def find_teensy_device(self) -> Optional[int]:
        """Find Teensy audio device by name."""
        devices = sd.query_devices()

        print("Available audio devices:")
        for i, device in enumerate(devices):
            print(f"  {i}: {device['name']} (in:{device['max_input_channels']}, out:{device['max_output_channels']})")

        # Look for Teensy device
        for i, device in enumerate(devices):
            name_lower = device['name'].lower()
            if ('teensy' in name_lower and device['max_input_channels'] >= self.num_channels):
                print(f"Found Teensy device: {device['name']} (ID: {i})")
                return i

        print("No suitable Teensy device found!")
        return None

    def set_audio_callback(self, callback: Callable[[np.ndarray, float], None]):
        """Set callback function for audio processing."""
        self.callback_func = callback

    def start_capture(self, block_size: int = 1024) -> bool:
        """Start audio capture stream."""
        if self.device_id is None:
            self.device_id = self.find_teensy_device()
            if self.device_id is None:
                return False

        def audio_callback(indata, frames, time_info, status):
            if status:
                print(f"Audio status: {status}")

            # Convert int16 to float64 and call user callback
            if self.callback_func and indata.shape[1] >= self.num_channels:
                audio_data = indata[:, :self.num_channels].astype(np.float64)
                timestamp = time_info.inputBufferAdcTime
                self.callback_func(audio_data, timestamp)

        try:
            self.stream = sd.InputStream(
                device=self.device_id,
                channels=self.num_channels,
                samplerate=self.sample_rate,
                blocksize=block_size,
                dtype='int16',
                callback=audio_callback
            )

            self.stream.start()
            self.is_running = True
            print(f"Started audio capture: {block_size} samples @ {self.sample_rate}Hz")
            return True

        except Exception as e:
            print(f"Error starting audio capture: {e}")
            return False

    def stop_capture(self):
        """Stop audio capture stream."""
        if self.stream and self.is_running:
            self.stream.stop()
            self.stream.close()
            self.is_running = False
            print("Stopped audio capture")

    def get_device_info(self) -> Dict[str, Any]:
        """Get information about the selected audio device."""
        if self.device_id is not None:
            return sd.query_devices(self.device_id)
        return {}


if __name__ == "__main__":
    # Simple test of audio capture
    def test_callback(audio_data: np.ndarray, timestamp: float):
        # Calculate RMS levels for each channel
        rms_levels = np.sqrt(np.mean(audio_data**2, axis=0))
        level_bars = [''.join(['=' if rms > (i/20) else ' ' for i in range(20)]) for rms in rms_levels]

        print(f"\\r{timestamp:.3f} | " + " | ".join([f"Ch{i}:[{bar}]" for i, bar in enumerate(level_bars)]), end="")

    capture = TeensyAudioCapture()
    capture.set_audio_callback(test_callback)

    if capture.start_capture(block_size=512):
        print("Press Ctrl+C to stop...")
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass

    capture.stop_capture()