"""
Python implementation of ODAS Live processing

This is a pure Python implementation of the odaslive demo,
providing real-time audio processing with ODAS.
"""

import json
import socket
import threading
import time
import wave
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List, Tuple
import numpy as np

try:
    from . import _odas_core
    _HAS_ODAS = True
except ImportError:
    _HAS_ODAS = False
    import warnings
    warnings.warn("ODAS C extension not available, will use simulation mode")

try:
    import pyaudio
    _HAS_PYAUDIO = True
except ImportError:
    _HAS_PYAUDIO = False
    import warnings
    warnings.warn("PyAudio not available, live audio capture disabled")


def list_audio_devices() -> List[Dict[str, Any]]:
    """
    List all available PyAudio input devices

    Returns:
        List of device info dictionaries with keys:
        - index: Device index
        - name: Device name
        - channels: Max input channels
        - sample_rate: Default sample rate
    """
    if not _HAS_PYAUDIO:
        print("PyAudio not available. Install with: pip install pyaudio")
        return []

    pa = pyaudio.PyAudio()
    devices = []

    try:
        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            # Only include devices with input channels
            if info.get('maxInputChannels', 0) > 0:
                devices.append({
                    'index': i,
                    'name': info.get('name', 'Unknown'),
                    'channels': info.get('maxInputChannels', 0),
                    'sample_rate': int(info.get('defaultSampleRate', 0))
                })
    finally:
        pa.terminate()

    return devices


def print_audio_devices():
    """Print formatted list of available audio input devices"""
    devices = list_audio_devices()

    if not devices:
        print("No audio input devices found")
        return

    print("\nAvailable Audio Input Devices:")
    print("=" * 80)
    print(f"{'Index':<6} {'Channels':<10} {'Sample Rate':<12} {'Name'}")
    print("-" * 80)

    for dev in devices:
        print(f"{dev['index']:<6} {dev['channels']:<10} {dev['sample_rate']:<12} {dev['name']}")

    print("=" * 80)
    print(f"\nTotal: {len(devices)} device(s)")
    print("\nUsage: processor.set_source_pyaudio(device_index=N)")
    print("   or: processor.set_source_pyaudio(device_name='substring')")


class OdasConfig:
    """Parse and manage ODAS configuration files"""

    def __init__(self, config_file: str):
        self.config_file = Path(config_file)

        if self.config_file.exists():
            # Parse config file (libconfig format)
            # For now, we'll need a Python libconfig parser or convert to JSON
            self.config = self._parse_config()
        else:
            # Allow missing config for manual configuration
            self.config = {}

    def _parse_config(self) -> Dict[str, Any]:
        """Parse libconfig format (simplified for now)"""
        # TODO: Full libconfig parser or require JSON configs
        return {}

    def get(self, key: str, default=None):
        """Get configuration value"""
        return self.config.get(key, default)


class AudioSource:
    """Base class for audio sources"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.channels = config.get('channels', 4)
        self.samplerate = config.get('samplerate', 44100)
        self.hopsize = config.get('hopsize', 512)

    def read_hop(self) -> Optional[np.ndarray]:
        """Read one hop of audio data"""
        raise NotImplementedError()

    def close(self):
        """Close audio source"""
        pass


class WavFileSource(AudioSource):
    """Read audio from WAV file"""

    def __init__(self, config: Dict[str, Any], filename: str):
        super().__init__(config)
        self.filename = filename
        self.wav = wave.open(filename, 'rb')

        # Verify format
        if self.wav.getnchannels() != self.channels:
            raise ValueError(f"Expected {self.channels} channels, got {self.wav.getnchannels()}")
        if self.wav.getframerate() != self.samplerate:
            raise ValueError(f"Expected {self.samplerate} Hz, got {self.wav.getframerate()}")

    def read_hop(self) -> Optional[np.ndarray]:
        """Read one hop from WAV file"""
        frames = self.wav.readframes(self.hopsize)
        if len(frames) == 0:
            return None

        # Convert to float32 normalized [-1, 1]
        audio = np.frombuffer(frames, dtype=np.int16)
        audio = audio.astype(np.float32) / 32768.0

        # Reshape to (hopsize, channels)
        audio = audio.reshape(-1, self.channels)

        # Pad if necessary
        if audio.shape[0] < self.hopsize:
            padding = np.zeros((self.hopsize - audio.shape[0], self.channels), dtype=np.float32)
            audio = np.vstack([audio, padding])

        return audio

    def close(self):
        if self.wav:
            self.wav.close()


class SocketSource(AudioSource):
    """Read audio from network socket"""

    def __init__(self, config: Dict[str, Any], host: str, port: int):
        super().__init__(config)
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((host, port))
        self.bytes_per_sample = 2  # int16
        self.frame_size = self.hopsize * self.channels * self.bytes_per_sample

    def read_hop(self) -> Optional[np.ndarray]:
        """Read one hop from socket"""
        try:
            data = self.socket.recv(self.frame_size)
            if len(data) == 0:
                return None

            audio = np.frombuffer(data, dtype=np.int16)
            audio = audio.astype(np.float32) / 32768.0
            audio = audio.reshape(-1, self.channels)

            return audio
        except Exception as e:
            print(f"Socket read error: {e}")
            return None

    def close(self):
        if self.socket:
            self.socket.close()


class PyAudioSource(AudioSource):
    """Read audio from PyAudio device (live microphone/USB audio)"""

    def __init__(self, config: Dict[str, Any], device_index: Optional[int] = None,
                 device_name: Optional[str] = None):
        super().__init__(config)

        if not _HAS_PYAUDIO:
            raise RuntimeError("PyAudio not available. Install with: pip install pyaudio")

        self.pa = pyaudio.PyAudio()
        self.stream = None
        self.device_index = device_index

        # If device name provided, find matching device
        if device_name and device_index is None:
            self.device_index = self._find_device_by_name(device_name)
            if self.device_index is None:
                raise ValueError(f"Audio device '{device_name}' not found")

        # Get device info
        if self.device_index is not None:
            device_info = self.pa.get_device_info_by_index(self.device_index)
            max_channels = device_info.get('maxInputChannels', 0)
            if max_channels < self.channels:
                raise ValueError(f"Device has only {max_channels} input channels, need {self.channels}")

        # Open audio stream
        try:
            self.stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.samplerate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.hopsize,
                stream_callback=None  # Use blocking read mode
            )
        except Exception as e:
            self.pa.terminate()
            raise RuntimeError(f"Failed to open audio device: {e}")

    def _find_device_by_name(self, name: str) -> Optional[int]:
        """Find device index by name (case-insensitive substring match)"""
        name_lower = name.lower()
        for i in range(self.pa.get_device_count()):
            device_info = self.pa.get_device_info_by_index(i)
            device_name = device_info.get('name', '').lower()
            if name_lower in device_name and device_info.get('maxInputChannels', 0) > 0:
                return i
        return None

    def read_hop(self) -> Optional[np.ndarray]:
        """Read one hop from audio device"""
        if not self.stream or not self.stream.is_active():
            return None

        try:
            # Read audio data (blocking)
            data = self.stream.read(self.hopsize, exception_on_overflow=False)

            # Convert to float32 normalized [-1, 1]
            audio = np.frombuffer(data, dtype=np.int16)
            audio = audio.astype(np.float32) / 32768.0

            # Reshape to (hopsize, channels)
            audio = audio.reshape(-1, self.channels)

            return audio
        except Exception as e:
            print(f"PyAudio read error: {e}")
            return None

    def close(self):
        """Close audio stream and PyAudio"""
        if self.stream:
            if self.stream.is_active():
                self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        if self.pa:
            self.pa.terminate()
            self.pa = None


class AudioSink:
    """Base class for result sinks"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.format_type = config.get('format', 'json')

    def write(self, data: Dict[str, Any]):
        """Write result data"""
        raise NotImplementedError()

    def close(self):
        """Close sink"""
        pass


class FileSink(AudioSink):
    """Write results to file"""

    def __init__(self, config: Dict[str, Any], filename: str):
        super().__init__(config)
        self.filename = filename
        self.file = open(filename, 'w')

    def write(self, data: Dict[str, Any]):
        """Write JSON data to file"""
        json.dump(data, self.file)
        self.file.write('\n')
        self.file.flush()

    def close(self):
        if self.file:
            self.file.close()


class SocketSink(AudioSink):
    """Stream results over network socket"""

    def __init__(self, config: Dict[str, Any], host: str, port: int):
        super().__init__(config)
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((host, port))

    def write(self, data: Dict[str, Any]):
        """Send JSON data over socket"""
        msg = json.dumps(data) + '\n'
        self.socket.sendall(msg.encode('utf-8'))

    def close(self):
        if self.socket:
            self.socket.close()


class StdoutSink(AudioSink):
    """Print results to stdout"""

    def write(self, data: Dict[str, Any]):
        """Print JSON to stdout"""
        print(json.dumps(data))


class WavFileSink:
    """Write audio to WAV file(s)"""

    def __init__(self, filename: str, channels: int, sample_rate: int, mode='single'):
        """
        Initialize WAV file sink

        Args:
            filename: Output filename. For multi-channel mode, will append channel number
            channels: Number of audio channels
            sample_rate: Sample rate in Hz
            mode: 'single' (interleaved multi-channel) or 'multi' (separate files per channel)
        """
        self.filename = filename
        self.channels = channels
        self.sample_rate = sample_rate
        self.mode = mode
        self.wav_files = []

        if mode == 'single':
            # Single multi-channel WAV file
            self.wav_files.append(wave.open(filename, 'wb'))
            self.wav_files[0].setnchannels(channels)
            self.wav_files[0].setsampwidth(2)  # 16-bit
            self.wav_files[0].setframerate(sample_rate)
        elif mode == 'multi':
            # Separate file per channel
            base = filename.rsplit('.', 1)[0]
            ext = filename.rsplit('.', 1)[1] if '.' in filename else 'wav'
            for ch in range(channels):
                fname = f"{base}_ch{ch}.{ext}"
                wav = wave.open(fname, 'wb')
                wav.setnchannels(1)
                wav.setsampwidth(2)  # 16-bit
                wav.setframerate(sample_rate)
                self.wav_files.append(wav)

    def write_audio(self, audio: np.ndarray):
        """
        Write audio data

        Args:
            audio: Audio array of shape (samples, channels) as float32 [-1, 1]
        """
        # Convert float32 [-1, 1] to int16
        audio_int16 = (audio * 32767).astype(np.int16)

        if self.mode == 'single':
            # Write interleaved
            self.wav_files[0].writeframes(audio_int16.tobytes())
        elif self.mode == 'multi':
            # Write each channel separately
            for ch in range(self.channels):
                self.wav_files[ch].writeframes(audio_int16[:, ch].tobytes())

    def close(self):
        """Close all WAV files"""
        for wav in self.wav_files:
            if wav:
                wav.close()
        self.wav_files = []


class OdasLive:
    """
    Python implementation of ODAS Live

    This replaces the C odaslive demo with a pure Python implementation
    that uses ODAS library for processing but handles I/O in Python.
    """

    def __init__(self, config_file: str = None, mic_positions: Dict[str, list] = None,
                 n_channels: int = 4, frame_size: int = 512, sample_rate: int = 44100,
                 enable_tracking: bool = False, enable_separation: bool = False):
        """
        Initialize ODAS Live processor

        Args:
            config_file: Path to ODAS configuration file (optional, for future use)
            mic_positions: Dictionary of microphone positions {'mic_0': [x, y, z], ...}
            n_channels: Number of audio channels
            frame_size: STFT frame size
            sample_rate: Audio sample rate in Hz
            enable_tracking: Enable SST (Sound Source Tracking) module
            enable_separation: Enable SSS (Sound Source Separation) module (requires enable_tracking=True)
        """
        if config_file:
            self.config = OdasConfig(config_file)
        else:
            self.config = None

        self.source: Optional[AudioSource] = None
        self.sinks: Dict[str, AudioSink] = {}
        self.running = False
        self.thread: Optional[threading.Thread] = None

        # Audio output sinks
        self.audio_sink: Optional[WavFileSink] = None
        self.separated_sink: Optional[WavFileSink] = None
        self.residual_sink: Optional[WavFileSink] = None

        # Callbacks for results
        self.pots_callback: Optional[Callable] = None
        self.tracks_callback: Optional[Callable] = None
        self.separated_callback: Optional[Callable] = None

        # Initialize ODAS pipeline if available
        self.odas_pipeline = None
        self.enable_tracking = enable_tracking
        self.enable_separation = enable_separation

        if enable_separation and not enable_tracking:
            raise ValueError("Sound source separation requires enable_tracking=True")

        if _HAS_ODAS and mic_positions:
            pipeline_config = {
                'n_channels': n_channels,
                'frame_size': frame_size,
                'sample_rate': sample_rate,
                'mics': mic_positions,
                'enable_tracking': enable_tracking,
                'enable_separation': enable_separation
            }
            try:
                self.odas_pipeline = _odas_core.OdasPipeline(pipeline_config)
            except Exception as e:
                import warnings
                warnings.warn(f"Failed to initialize ODAS pipeline: {e}, using simulation mode")
                self.odas_pipeline = None

        # Store audio config
        self.n_channels = n_channels
        self.frame_size = frame_size
        self.sample_rate = sample_rate
        self.hop_size = frame_size  # Full frame for processing

    def set_source_wav(self, filename: str):
        """Set WAV file as audio source"""
        config = {
            'channels': self.n_channels,
            'samplerate': self.sample_rate,
            'hopsize': self.hop_size
        }
        self.source = WavFileSource(config, filename)

    def set_source_socket(self, host: str, port: int):
        """Set network socket as audio source"""
        config = {
            'channels': self.n_channels,
            'samplerate': self.sample_rate,
            'hopsize': self.hop_size
        }
        self.source = SocketSource(config, host, port)

    def set_source_pyaudio(self, device_index: Optional[int] = None,
                           device_name: Optional[str] = None):
        """
        Set PyAudio device as audio source (live audio capture)

        Args:
            device_index: PyAudio device index (optional)
            device_name: Device name substring to search for (optional)
                        e.g. "Teensy", "USB Audio", "Microphone"

        Examples:
            processor.set_source_pyaudio()  # Use default device
            processor.set_source_pyaudio(device_name="Teensy")  # Find Teensy device
            processor.set_source_pyaudio(device_index=3)  # Use device 3
        """
        if not _HAS_PYAUDIO:
            raise RuntimeError("PyAudio not available. Install with: pip install pyaudio")

        config = {
            'channels': self.n_channels,
            'samplerate': self.sample_rate,
            'hopsize': self.hop_size
        }
        self.source = PyAudioSource(config, device_index=device_index, device_name=device_name)

    def add_sink_file(self, name: str, filename: str):
        """Add file sink for results"""
        config = {'format': 'json'}
        self.sinks[name] = FileSink(config, filename)

    def add_sink_socket(self, name: str, host: str, port: int):
        """Add socket sink for results"""
        config = {'format': 'json'}
        self.sinks[name] = SocketSink(config, host, port)

    def add_sink_stdout(self, name: str):
        """Add stdout sink for results"""
        config = {'format': 'json'}
        self.sinks[name] = StdoutSink(config)

    def set_pots_callback(self, callback: Callable):
        """Set callback for potential sound sources (SSL results)"""
        self.pots_callback = callback

    def set_tracks_callback(self, callback: Callable):
        """Set callback for tracked sources (SST results)"""
        self.tracks_callback = callback

    def set_separated_callback(self, callback: Callable):
        """
        Set callback for separated audio (SSS results)

        Args:
            callback: Function that receives (separated_audio, residual_audio) arrays
                     separated_audio: shape (samples, channels) - beamformed audio
                     residual_audio: shape (samples, channels) - remainder
        """
        self.separated_callback = callback

    def set_separation_output(self, separated_file: str, residual_file: str = None, mode='single'):
        """
        Enable separated audio output to WAV file(s)

        Args:
            separated_file: Filename for separated (beamformed) audio
            residual_file: Filename for residual audio (optional, defaults to separated_file with _residual suffix)
            mode: 'single' (multi-channel interleaved) or 'multi' (separate files per channel)
        """
        if residual_file is None:
            base = separated_file.rsplit('.', 1)[0]
            ext = separated_file.rsplit('.', 1)[1] if '.' in separated_file else 'wav'
            residual_file = f"{base}_residual.{ext}"

        self.separated_sink = WavFileSink(separated_file, self.n_channels, self.sample_rate, mode)
        self.residual_sink = WavFileSink(residual_file, self.n_channels, self.sample_rate, mode)

    def set_audio_output(self, filename: str, mode='single'):
        """
        Enable audio output to WAV file(s)

        Args:
            filename: Output filename
            mode: 'single' for multi-channel WAV, 'multi' for separate files per channel

        Examples:
            processor.set_audio_output("captured.wav")  # 4-channel WAV
            processor.set_audio_output("captured.wav", mode='multi')  # captured_ch0.wav, ...
        """
        self.audio_sink = WavFileSink(
            filename=filename,
            channels=self.n_channels,
            sample_rate=self.sample_rate,
            mode=mode
        )

    def _process_loop(self):
        """Main processing loop (runs in thread)"""
        if not self.source:
            raise RuntimeError("No audio source configured")

        frame_count = 0

        try:
            while self.running:
                # Read audio hop
                audio = self.source.read_hop()
                if audio is None:
                    # End of stream
                    break

                # Write audio to file if sink is enabled
                if self.audio_sink:
                    self.audio_sink.write_audio(audio)

                # Process through ODAS pipeline
                if self.odas_pipeline:
                    try:
                        # Ensure audio is float32 and C-contiguous
                        audio_f32 = np.ascontiguousarray(audio, dtype=np.float32)
                        odas_results = self.odas_pipeline.process(audio_f32)

                        # Call callbacks with raw ODAS results
                        if self.pots_callback and 'pots' in odas_results:
                            self.pots_callback(odas_results['pots'])

                        if self.tracks_callback and 'tracks' in odas_results:
                            self.tracks_callback(odas_results['tracks'])

                        # Handle separated audio if available
                        if 'separated' in odas_results and 'residual' in odas_results:
                            separated = odas_results['separated']
                            residual = odas_results['residual']

                            # Call callback
                            if self.separated_callback:
                                self.separated_callback(separated, residual)

                            # Write to files
                            if self.separated_sink:
                                self.separated_sink.write_audio(separated)
                            if self.residual_sink:
                                self.residual_sink.write_audio(residual)

                        # Convert to standard format for sinks
                        results = self._format_results(odas_results, frame_count)
                    except Exception as e:
                        print(f"ODAS processing error: {e}")
                        import traceback
                        traceback.print_exc()
                        results = self._simulate_processing(audio, frame_count)
                else:
                    # Fallback to simulation if no ODAS available
                    results = self._simulate_processing(audio, frame_count)

                # Send to sinks
                for sink in self.sinks.values():
                    sink.write(results)

                frame_count += 1

        except Exception as e:
            print(f"Processing loop error: {e}")
            import traceback
            traceback.print_exc()

    def _format_results(self, odas_results: Dict[str, Any], frame_count: int) -> Dict[str, Any]:
        """Format ODAS results to standard output format"""
        # Extract pots and convert to source format
        pots = odas_results.get('pots', [])

        # Filter pots with significant energy
        sources = []
        for pot in pots:
            if pot['value'] > 0.1:  # Threshold for significant source
                sources.append({
                    'x': pot['x'],
                    'y': pot['y'],
                    'z': pot['z'],
                    'activity': pot['value']
                })

        return {
            'timeStamp': frame_count * self.hop_size / float(self.sample_rate),
            'src': sources
        }

    def _simulate_processing(self, audio: np.ndarray, frame_count: int) -> Dict[str, Any]:
        """Simulate ODAS processing (fallback when C extension not available)"""
        return {
            'timeStamp': frame_count * self.hop_size / float(self.sample_rate),
            'src': [
                {
                    'x': 0.0,
                    'y': 0.0,
                    'z': 0.0,
                    'activity': 0.0
                }
            ]
        }

    def start(self):
        """Start processing in background thread"""
        if self.running:
            raise RuntimeError("Already running")

        self.running = True
        self.thread = threading.Thread(target=self._process_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop processing"""
        if not self.running:
            return

        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)
            self.thread = None

    def run_blocking(self):
        """Run processing in current thread (blocking)"""
        if not self.source:
            raise RuntimeError("No audio source configured")

        self.running = True
        self._process_loop()

    def close(self):
        """Close all resources"""
        self.stop()

        if self.source:
            self.source.close()

        for sink in self.sinks.values():
            sink.close()

        if self.audio_sink:
            self.audio_sink.close()

        if self.separated_sink:
            self.separated_sink.close()

        if self.residual_sink:
            self.residual_sink.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        return False