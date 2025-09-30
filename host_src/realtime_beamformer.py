"""
Real-time beamforming application for Teensy Ambisonic Microphone Array.
Captures 8-channel audio, applies beamforming toward selected/detected direction,
and plays the enhanced audio through system output.
"""

import sys
import numpy as np
import sounddevice as sd
import queue
import threading
import wave
import datetime
import os
import time
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QPushButton, QLabel, QSlider, QComboBox,
                            QGroupBox, QGridLayout, QCheckBox, QSpinBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QBrush
import pyqtgraph as pg

from doa_processing import DOAProcessor


class AudioProcessor(QObject):
    """Handles audio capture, beamforming, and playback in separate thread."""

    # Signals for thread-safe communication
    doa_update = pyqtSignal(float, float, float)  # azimuth, elevation, confidence
    level_update = pyqtSignal(np.ndarray)  # channel levels

    def __init__(self, sample_rate=44100, block_size=512, channels=8):  # Smaller block for lower latency
        super().__init__()

        self.sample_rate = sample_rate
        self.block_size = block_size
        self.channels = channels

        # Device indices (will be set from GUI)
        self.input_device = None
        self.output_device = None

        # Sample rate settings
        self.input_sample_rate = sample_rate
        self.output_sample_rate = sample_rate
        self.output_format = np.float32


        # DOA processor (will be recreated with correct sample rate)
        self.doa_processor = None

        # Audio queues - smaller for tighter timing
        self.input_queue = queue.Queue(maxsize=3)  # Only a few blocks ahead
        self.output_queue = queue.Queue(maxsize=3)  # For audio callback only
        self.monitor_queue = queue.Queue(maxsize=10)  # For GUI visualization (larger buffer)

        # Processing parameters - optimized for real-time performance
        self.beamforming_enabled = True
        self.beamform_mode = "delay_sum"  # Start with fastest method: "delay_sum"
        self.auto_track = True  # Auto-track strongest source
        self.manual_azimuth = 0.0
        self.manual_elevation = 0.0

        # DOA estimation parameters - use fastest method
        self.doa_method = "tdoa_ls"  # Use faster "tdoa_ls" instead of "srp_phat"
        self.doa_update_interval = 20  # Update DOA every N blocks (less frequent)
        self.doa_block_counter = 0

        # Current DOA estimate
        self.current_azimuth = 0.0
        self.current_elevation = 0.0
        self.current_confidence = 0.0

        # Processing thread control
        self.running = False
        self.processing_thread = None

        # Audio stream
        self.duplex_stream = None

        # Debug recording
        self.debug_recording = False
        self.debug_input_enabled = False
        self.debug_output_enabled = False
        self.debug_input_file = None
        self.debug_output_file = None
        self.debug_input_data = []
        self.debug_output_data = []


    @staticmethod
    def get_audio_devices():
        """Get list of available audio devices."""
        devices = sd.query_devices()
        input_devices = []
        output_devices = []

        for idx, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                input_devices.append({
                    'index': idx,
                    'name': device['name'],
                    'channels': device['max_input_channels'],
                    'sample_rate': device['default_samplerate']
                })
            if device['max_output_channels'] > 0:
                output_devices.append({
                    'index': idx,
                    'name': device['name'],
                    'channels': device['max_output_channels'],
                    'sample_rate': device['default_samplerate']
                })

        return input_devices, output_devices

    def start_debug_recording(self, record_input=True, record_output=True):
        """Start debug recording of audio streams."""
        if self.debug_recording:
            return

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_dir = "debug_audio"
        os.makedirs(debug_dir, exist_ok=True)

        self.debug_recording = True
        self.debug_input_enabled = record_input
        self.debug_output_enabled = record_output
        self.debug_input_data = []
        self.debug_output_data = []

        if record_input:
            self.debug_input_file = os.path.join(debug_dir, f"input_raw_{timestamp}.wav")
            print(f"Starting input debug recording: {self.debug_input_file}")

        if record_output:
            self.debug_output_file = os.path.join(debug_dir, f"output_processed_{timestamp}.wav")
            print(f"Starting output debug recording: {self.debug_output_file}")

    def stop_debug_recording(self):
        """Stop debug recording and save files."""
        if not self.debug_recording:
            return

        self.debug_recording = False
        sample_rate = self.input_sample_rate or self.sample_rate

        # Save input recording
        if self.debug_input_enabled and self.debug_input_data:
            try:
                input_audio = np.concatenate(self.debug_input_data, axis=0)
                self._save_debug_wav(self.debug_input_file, input_audio, sample_rate, is_input=True)
                print(f"Saved input debug recording: {self.debug_input_file}")
            except Exception as e:
                print(f"Error saving input debug: {e}")

        # Save output recording
        if self.debug_output_enabled and self.debug_output_data:
            try:
                output_audio = np.concatenate(self.debug_output_data, axis=0)
                self._save_debug_wav(self.debug_output_file, output_audio, sample_rate, is_input=False)
                print(f"Saved output debug recording: {self.debug_output_file}")
            except Exception as e:
                print(f"Error saving output debug: {e}")

        # Clear data
        self.debug_input_data = []
        self.debug_output_data = []

    def _save_debug_wav(self, filename, audio_data, sample_rate, is_input=True):
        """Save audio data to WAV file."""
        if len(audio_data) == 0:
            return

        # Ensure proper data type and range
        if is_input:
            # Input is int16, convert for WAV
            if audio_data.dtype == np.int16:
                audio_data = audio_data.astype(np.float32) / 32767.0

        # Ensure audio is in proper range [-1, 1]
        audio_data = np.clip(audio_data, -1.0, 1.0)

        # Convert to int16 for WAV file
        audio_data = (audio_data * 32767).astype(np.int16)

        # Get channel count
        if len(audio_data.shape) == 1:
            channels = 1
            frames = len(audio_data)
        else:
            channels = audio_data.shape[1]
            frames = audio_data.shape[0]

        # Write WAV file
        with wave.open(filename, 'wb') as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(int(sample_rate))
            wav_file.writeframes(audio_data.tobytes())

    def duplex_callback(self, indata, outdata, frames, time_info, status):
        """Fast real-time callback: queue input, dequeue processed output."""
        if status:
            print(f"Duplex status: {status}")

        try:
            # Convert input to float32 (avoid conversion if already float32)
            if indata.dtype == np.int16:
                audio_block = indata.astype(np.float32) / 32767.0
            else:
                audio_block = indata.astype(np.float32, copy=False)

            # Push input into queue (drop oldest if full)
            try:
                self.input_queue.put_nowait(audio_block)
            except queue.Full:
                # Drop oldest block if queue is full
                try:
                    self.input_queue.get_nowait()
                    self.input_queue.put_nowait(audio_block)
                except queue.Empty:
                    pass

            # Get processed output (or silence if none)
            try:
                processed = self.output_queue.get_nowait()
            except queue.Empty:
                processed = np.zeros((frames, 2), dtype=np.float32)

            # Match frame count
            if processed.shape[0] < frames:
                pad = np.zeros((frames - processed.shape[0], 2), dtype=np.float32)
                processed = np.vstack([processed, pad])
            elif processed.shape[0] > frames:
                processed = processed[:frames, :]

            # Ensure stereo output
            if len(processed.shape) == 1:
                processed = np.column_stack([processed, processed])
            elif processed.shape[1] == 1:
                processed = np.column_stack([processed[:, 0], processed[:, 0]])

            # Output (already float32, just ensure range and copy)
            outdata[:] = np.clip(processed, -1.0, 1.0).astype(np.float32, copy=False)

            # Debug recording (optional, keep raw indata/output)
            if self.debug_recording:
                if self.debug_input_enabled:
                    self.debug_input_data.append(indata.copy())
                if self.debug_output_enabled:
                    self.debug_output_data.append(processed.copy())

        except Exception as e:
            print(f"Duplex callback error: {e}")
            outdata.fill(0)  # Output silence on error


    def processing_loop(self):
        """Background thread: handles DOA and beamforming."""
        while self.running:
            try:
                # Get input audio block (already converted to float32 in callback)
                audio_block = self.input_queue.get(timeout=0.1)

                # Start timing for overrun detection
                t0 = time.perf_counter()

                # Ensure channel count
                if audio_block.shape[1] < self.channels:
                    pad = np.zeros((len(audio_block), self.channels - audio_block.shape[1]))
                    audio_block = np.hstack([audio_block, pad])
                else:
                    audio_block = audio_block[:, :self.channels]

                # For DOA, use first 4 channels (tetrahedral array)
                doa_audio = audio_block[:, :4]
                if doa_audio.shape[1] < 4:
                    pad = np.zeros((len(doa_audio), 4 - doa_audio.shape[1]))
                    doa_audio = np.hstack([doa_audio, pad])

                # Update channel levels for GUI visualization
                levels = np.sqrt(np.mean(audio_block**2, axis=0))
                self.level_update.emit(levels)

                # Update DOA every N blocks to reduce computational load
                self.doa_block_counter += 1
                if self.doa_block_counter >= self.doa_update_interval:
                    self.doa_block_counter = 0
                    if self.auto_track and self.doa_processor:
                        try:
                            # Use faster TDOA method for real-time processing
                            if self.doa_method == "srp_phat":
                                az, el, conf = self.doa_processor.srp_phat_doa(doa_audio)
                            else:  # tdoa_ls (faster)
                                tdoas = self.doa_processor.compute_tdoa_estimates(doa_audio)
                                az, el, conf = self.doa_processor.least_squares_doa(tdoas)

                            self.current_azimuth, self.current_elevation, self.current_confidence = az, el, conf
                            self.doa_update.emit(az, el, conf)
                        except Exception:
                            # Continue with previous DOA values if update fails
                            pass

                # Choose target direction
                if not self.auto_track:
                    target_az, target_el = self.manual_azimuth, self.manual_elevation
                else:
                    target_az, target_el = self.current_azimuth, self.current_elevation

                # Apply beamforming
                if self.beamforming_enabled and self.doa_processor:
                    try:
                        # Apply selected beamforming method
                        if self.beamform_mode == "delay_sum":
                            processed = self.doa_processor.delay_and_sum_beamformer(
                                doa_audio, target_az, target_el)
                        elif self.beamform_mode == "mvdr":
                            processed = self.doa_processor.mvdr_beamformer(
                                doa_audio, target_az, target_el)
                        elif self.beamform_mode == "mvdr_broadband":
                            processed = self.doa_processor.broadband_mvdr_beamformer(
                                doa_audio, target_az, target_el)
                        elif self.beamform_mode == "superdirective":
                            processed = self.doa_processor.superdirective_beamformer(
                                doa_audio, target_az, target_el)
                        else:
                            # Fallback to simple averaging
                            processed = np.mean(doa_audio, axis=1)

                        # Ensure output is float32
                        processed = processed.astype(np.float32)
                    except Exception as e:
                        # Fallback to simple averaging if beamforming fails
                        processed = np.mean(audio_block, axis=1).astype(np.float32)
                else:
                    # No beamforming - just average all channels
                    processed = np.mean(audio_block, axis=1).astype(np.float32)

                # Convert to stereo output
                stereo_output = np.column_stack([processed, processed])

                # Push to output queue (for audio callback)
                try:
                    self.output_queue.put_nowait(stereo_output)
                except queue.Full:
                    # Drop oldest if queue is full
                    try:
                        self.output_queue.get_nowait()
                        self.output_queue.put_nowait(stereo_output)
                    except queue.Empty:
                        pass

                # Also push a copy to monitor queue for GUI visualization
                try:
                    self.monitor_queue.put_nowait(stereo_output.copy())
                except queue.Full:
                    # Drop oldest for GUI - less critical than audio
                    try:
                        self.monitor_queue.get_nowait()
                        self.monitor_queue.put_nowait(stereo_output.copy())
                    except queue.Empty:
                        pass

                # Check for processing overruns
                elapsed = (time.perf_counter() - t0) * 1000  # Convert to milliseconds
                block_time_ms = (self.block_size / self.sample_rate) * 1000
                if elapsed > block_time_ms:
                    print(f"⚠️ Processing overrun: {elapsed:.1f} ms (block = {block_time_ms:.1f} ms)")

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Processing error: {e}")

    def start(self):
        """Start audio processing."""
        if self.running:
            return

        if self.input_device is None:
            print("Error: No input device selected!")
            return

        if self.output_device is None:
            print("Error: No output device selected!")
            return

        # Initialize DOA processor before starting
        input_sr = self.input_sample_rate or self.sample_rate
        if self.doa_processor is None:
            self.doa_processor = DOAProcessor()
            self.doa_processor.sample_rate = input_sr
            self.doa_processor.max_lag_samples = self.doa_processor.calculate_max_lag_samples()
            print(f"DOA processor initialized with sample rate: {input_sr}")

        self.running = True

        # Clear queues
        while not self.input_queue.empty():
            try:
                self.input_queue.get_nowait()
            except queue.Empty:
                break
        while not self.output_queue.empty():
            try:
                self.output_queue.get_nowait()
            except queue.Empty:
                break
        while not self.monitor_queue.empty():
            try:
                self.monitor_queue.get_nowait()
            except queue.Empty:
                break

        # Start worker thread for DOA and beamforming processing
        self.processing_thread = threading.Thread(target=self.processing_loop, daemon=True)
        self.processing_thread.start()
        print("Worker thread started for DOA and beamforming processing")

        # Start duplex stream for real-time audio I/O
        try:
            sample_rate = self.input_sample_rate or self.sample_rate

            print(f"Creating DUPLEX stream: sr={sample_rate}, block={self.block_size}")
            print(f"  Input: device={self.input_device}, channels={self.channels}")
            print(f"  Output: device={self.output_device}, channels=2")

            # Create duplex stream with lightweight callback (use float32 for both)
            self.duplex_stream = sd.Stream(
                device=(self.input_device, self.output_device),
                channels=(self.channels, 2),  # Input channels, output channels
                samplerate=sample_rate,
                blocksize=self.block_size,
                dtype=(np.float32, np.float32),  # Use float32 for both to avoid conversion
                callback=self.duplex_callback
            )

            self.duplex_stream.start()
            print("Audio processing started (duplex + worker mode)")

        except Exception as e:
            print(f"Error creating audio streams: {e}")
            self.running = False
            return

    def stop(self):
        """Stop audio processing."""
        if not self.running:
            return

        self.running = False

        # Stop duplex stream
        if hasattr(self, 'duplex_stream') and self.duplex_stream:
            self.duplex_stream.stop()
            self.duplex_stream.close()
            self.duplex_stream = None

        # Stop processing thread
        if self.processing_thread:
            self.processing_thread.join(timeout=2.0)

        # Stop any ongoing debug recording
        if self.debug_recording:
            self.stop_debug_recording()

        print("Audio processing stopped")


class DirectionWidget(QWidget):
    """Widget for visualizing and controlling beam direction."""

    direction_changed = pyqtSignal(float, float)  # azimuth, elevation

    def __init__(self):
        super().__init__()
        self.setMinimumSize(400, 400)
        self.setMaximumSize(400, 400)

        # Current direction
        self.azimuth = 0.0
        self.elevation = 0.0
        self.confidence = 0.0

        # Manual control
        self.manual_mode = False
        self.manual_azimuth = 0.0
        self.manual_elevation = 0.0

    def set_direction(self, azimuth, elevation, confidence=1.0):
        """Update displayed direction."""
        self.azimuth = azimuth
        self.elevation = elevation
        self.confidence = confidence
        self.update()

    def set_manual_direction(self, azimuth, elevation):
        """Set manual direction."""
        self.manual_azimuth = azimuth
        self.manual_elevation = elevation
        self.update()

    def mousePressEvent(self, event):
        """Handle mouse click for manual direction control."""
        if self.manual_mode:
            # Convert click position to angles
            center_x = self.width() / 2
            center_y = self.height() / 2

            dx = event.x() - center_x
            dy = center_y - event.y()  # Invert Y axis

            # Calculate azimuth (full 360°)
            self.manual_azimuth = np.degrees(np.arctan2(dx, dy))

            # Calculate elevation based on distance from center
            dist = np.sqrt(dx**2 + dy**2)
            max_dist = min(center_x, center_y) * 0.9
            self.manual_elevation = 90 * (1 - dist / max_dist)
            self.manual_elevation = np.clip(self.manual_elevation, -90, 90)

            self.direction_changed.emit(self.manual_azimuth, self.manual_elevation)
            self.update()

    def paintEvent(self, event):
        """Draw the direction visualization."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor(30, 30, 30))

        center_x = self.width() / 2
        center_y = self.height() / 2
        radius = min(center_x, center_y) * 0.9

        # Draw elevation circles
        painter.setPen(QPen(QColor(60, 60, 60), 1))
        for el in [30, 60, 90]:
            r = radius * (90 - el) / 90
            painter.drawEllipse(int(center_x - r), int(center_y - r), int(2*r), int(2*r))

        # Draw azimuth lines
        for az in range(0, 360, 30):
            x = center_x + radius * np.sin(np.radians(az))
            y = center_y - radius * np.cos(np.radians(az))
            painter.drawLine(int(center_x), int(center_y), int(x), int(y))

        # Draw labels
        painter.setPen(QPen(QColor(150, 150, 150), 1))
        painter.setFont(QFont("Arial", 10))
        painter.drawText(int(center_x - 10), 20, "0°")
        painter.drawText(self.width() - 30, int(center_y + 5), "90°")
        painter.drawText(int(center_x - 15), self.height() - 10, "180°")
        painter.drawText(10, int(center_y + 5), "-90°")

        # Draw current beam direction
        if not self.manual_mode:
            # Auto-tracked direction
            r = radius * (90 - abs(self.elevation)) / 90
            x = center_x + r * np.sin(np.radians(self.azimuth))
            y = center_y - r * np.cos(np.radians(self.azimuth))

            # Confidence affects size and opacity
            size = 10 + 20 * self.confidence
            opacity = int(100 + 155 * self.confidence)

            painter.setPen(QPen(QColor(0, 255, 0, opacity), 2))
            painter.setBrush(QBrush(QColor(0, 255, 0, opacity // 2)))
            painter.drawEllipse(int(x - size/2), int(y - size/2), int(size), int(size))

            # Direction line
            painter.setPen(QPen(QColor(0, 255, 0, opacity), 2))
            painter.drawLine(int(center_x), int(center_y), int(x), int(y))

        # Draw manual direction if in manual mode
        if self.manual_mode:
            r = radius * (90 - abs(self.manual_elevation)) / 90
            x = center_x + r * np.sin(np.radians(self.manual_azimuth))
            y = center_y - r * np.cos(np.radians(self.manual_azimuth))

            painter.setPen(QPen(QColor(255, 165, 0), 3))
            painter.setBrush(QBrush(QColor(255, 165, 0, 100)))
            painter.drawEllipse(int(x - 15), int(y - 15), 30, 30)

            # Direction line
            painter.setPen(QPen(QColor(255, 165, 0), 3))
            painter.drawLine(int(center_x), int(center_y), int(x), int(y))

        # Draw center
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.drawEllipse(int(center_x - 5), int(center_y - 5), 10, 10)


class BeamformerGUI(QMainWindow):
    """Main GUI window for real-time beamformer."""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Real-Time Beamformer - Teensy Ambisonic Microphone")
        self.setGeometry(100, 100, 1200, 800)

        # Audio processor
        self.audio_processor = AudioProcessor(block_size=2048)

        # Connect signals
        self.audio_processor.doa_update.connect(self.update_doa)
        self.audio_processor.level_update.connect(self.update_levels)

        # Get available devices
        self.input_devices, self.output_devices = AudioProcessor.get_audio_devices()

        # Start with processing stopped
        self.processing_active = False

        # Setup UI
        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Device selection row
        device_layout = QHBoxLayout()

        # Input device selection
        device_layout.addWidget(QLabel("Input Device:"))
        self.input_device_combo = QComboBox()
        self.input_device_combo.setMinimumWidth(250)
        for device in self.input_devices:
            display_name = f"{device['name']} ({device['channels']} ch)"
            self.input_device_combo.addItem(display_name, device['index'])

        self.input_device_combo.currentIndexChanged.connect(self.update_input_device)
        device_layout.addWidget(self.input_device_combo)

        # Channel count spinbox
        device_layout.addWidget(QLabel("Channels:"))
        self.channel_spin = QSpinBox()
        self.channel_spin.setRange(1, 32)
        self.channel_spin.setValue(4)  # Default to 4 for tetrahedral array
        self.channel_spin.valueChanged.connect(self.update_channel_count)
        device_layout.addWidget(self.channel_spin)

        # Input sample rate selection
        device_layout.addWidget(QLabel("Input SR:"))
        self.input_sample_rate_combo = QComboBox()
        common_rates = [8000, 16000, 22050, 44100, 48000, 96000, 192000]
        for rate in common_rates:
            self.input_sample_rate_combo.addItem(f"{rate} Hz", rate)
        self.input_sample_rate_combo.setCurrentText("44100 Hz")  # Default
        self.input_sample_rate_combo.currentIndexChanged.connect(self.update_input_sample_rate)
        device_layout.addWidget(self.input_sample_rate_combo)

        # Output sample rate selection
        device_layout.addWidget(QLabel("Output SR:"))
        self.output_sample_rate_combo = QComboBox()
        for rate in common_rates:
            self.output_sample_rate_combo.addItem(f"{rate} Hz", rate)
        self.output_sample_rate_combo.setCurrentText("44100 Hz")  # Default
        self.output_sample_rate_combo.currentIndexChanged.connect(self.update_output_sample_rate)
        device_layout.addWidget(self.output_sample_rate_combo)

        # Output sample format selection
        device_layout.addWidget(QLabel("Output Format:"))
        self.output_format_combo = QComboBox()
        self.output_format_combo.addItem("float32", np.float32)
        self.output_format_combo.addItem("int16", np.int16)
        self.output_format_combo.addItem("int32", np.int32)
        self.output_format_combo.setCurrentText("float32")  # Default
        self.output_format_combo.currentIndexChanged.connect(self.update_output_format)
        device_layout.addWidget(self.output_format_combo)

        # Try to find Teensy or multi-channel device and set it as default
        default_device_idx = 0
        for i, device in enumerate(self.input_devices):
            if "Teensy" in device['name']:
                default_device_idx = i
                # Set channels based on device capability
                self.channel_spin.setMaximum(device['channels'])
                self.channel_spin.setValue(min(device['channels'], 8))
                break
            elif device['channels'] >= 4:
                default_device_idx = i
                self.channel_spin.setMaximum(device['channels'])
                self.channel_spin.setValue(min(device['channels'], 8))

        self.input_device_combo.setCurrentIndex(default_device_idx)

        # Output device selection
        device_layout.addWidget(QLabel("Output Device:"))
        self.output_device_combo = QComboBox()
        self.output_device_combo.setMinimumWidth(250)
        for device in self.output_devices:
            display_name = f"{device['name']} ({device['channels']} ch)"
            self.output_device_combo.addItem(display_name, device['index'])

        # Set default output device
        try:
            default_output = sd.default.device[1]
            for i, device in enumerate(self.output_devices):
                if device['index'] == default_output:
                    self.output_device_combo.setCurrentIndex(i)
                    break
        except:
            pass

        self.output_device_combo.currentIndexChanged.connect(self.update_output_device)
        device_layout.addWidget(self.output_device_combo)

        device_layout.addStretch()
        layout.addLayout(device_layout)

        # Top controls
        top_layout = QHBoxLayout()

        # Start/Stop button
        self.start_button = QPushButton("Start Processing")
        self.start_button.clicked.connect(self.toggle_processing)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 16px;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        top_layout.addWidget(self.start_button)

        # Beamforming enable
        self.beamform_check = QCheckBox("Enable Beamforming")
        self.beamform_check.setChecked(True)
        self.beamform_check.stateChanged.connect(self.update_beamforming)
        top_layout.addWidget(self.beamform_check)

        # Beamforming method
        top_layout.addWidget(QLabel("Method:"))
        self.method_combo = QComboBox()
        self.method_combo.addItems(["Delay & Sum", "MVDR", "Broadband MVDR", "Superdirective"])
        self.method_combo.setCurrentIndex(0)  # Default to Delay & Sum for best performance
        self.method_combo.currentIndexChanged.connect(self.update_method)
        top_layout.addWidget(self.method_combo)

        # DOA method
        top_layout.addWidget(QLabel("DOA:"))
        self.doa_combo = QComboBox()
        self.doa_combo.addItems(["SRP-PHAT", "TDOA-LS"])
        self.doa_combo.setCurrentIndex(1)  # Default to TDOA-LS for best performance
        self.doa_combo.currentIndexChanged.connect(self.update_doa_method)
        top_layout.addWidget(self.doa_combo)

        # Auto-track checkbox
        self.auto_track_check = QCheckBox("Auto-track")
        self.auto_track_check.setChecked(True)
        self.auto_track_check.stateChanged.connect(self.update_auto_track)
        top_layout.addWidget(self.auto_track_check)

        # Debug recording controls
        top_layout.addWidget(QLabel("|"))  # Separator

        self.debug_record_button = QPushButton("Start Debug Recording")
        self.debug_record_button.clicked.connect(self.toggle_debug_recording)
        self.debug_record_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-size: 12px;
                padding: 8px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        top_layout.addWidget(self.debug_record_button)

        self.debug_input_check = QCheckBox("Input")
        self.debug_input_check.setChecked(True)
        self.debug_input_check.setToolTip("Record raw input from microphone")
        top_layout.addWidget(self.debug_input_check)

        self.debug_output_check = QCheckBox("Output")
        self.debug_output_check.setChecked(True)
        self.debug_output_check.setToolTip("Record processed beamformed output")
        top_layout.addWidget(self.debug_output_check)

        top_layout.addStretch()
        layout.addLayout(top_layout)

        # Main content area
        content_layout = QHBoxLayout()

        # Left panel - Direction control
        left_panel = QVBoxLayout()

        # Direction widget
        self.direction_widget = DirectionWidget()
        self.direction_widget.direction_changed.connect(self.manual_direction_changed)
        left_panel.addWidget(self.direction_widget)

        # Direction info
        info_group = QGroupBox("Direction Info")
        info_layout = QGridLayout()

        self.azimuth_label = QLabel("Azimuth: 0.0°")
        self.elevation_label = QLabel("Elevation: 0.0°")
        self.confidence_label = QLabel("Confidence: 0.000")

        info_layout.addWidget(self.azimuth_label, 0, 0)
        info_layout.addWidget(self.elevation_label, 1, 0)
        info_layout.addWidget(self.confidence_label, 2, 0)

        info_group.setLayout(info_layout)
        left_panel.addWidget(info_group)

        # Manual controls
        manual_group = QGroupBox("Manual Control")
        manual_layout = QGridLayout()

        manual_layout.addWidget(QLabel("Azimuth:"), 0, 0)
        self.azimuth_slider = QSlider(Qt.Horizontal)
        self.azimuth_slider.setRange(-180, 180)
        self.azimuth_slider.setValue(0)
        self.azimuth_slider.valueChanged.connect(self.manual_slider_changed)
        manual_layout.addWidget(self.azimuth_slider, 0, 1)
        self.azimuth_spin = QSpinBox()
        self.azimuth_spin.setRange(-180, 180)
        self.azimuth_spin.setValue(0)
        self.azimuth_spin.valueChanged.connect(self.manual_spin_changed)
        manual_layout.addWidget(self.azimuth_spin, 0, 2)

        manual_layout.addWidget(QLabel("Elevation:"), 1, 0)
        self.elevation_slider = QSlider(Qt.Horizontal)
        self.elevation_slider.setRange(-90, 90)
        self.elevation_slider.setValue(0)
        self.elevation_slider.valueChanged.connect(self.manual_slider_changed)
        manual_layout.addWidget(self.elevation_slider, 1, 1)
        self.elevation_spin = QSpinBox()
        self.elevation_spin.setRange(-90, 90)
        self.elevation_spin.setValue(0)
        self.elevation_spin.valueChanged.connect(self.manual_spin_changed)
        manual_layout.addWidget(self.elevation_spin, 1, 2)

        manual_group.setLayout(manual_layout)
        left_panel.addWidget(manual_group)

        content_layout.addLayout(left_panel)

        # Right panel - Audio visualization
        right_panel = QVBoxLayout()

        # Channel levels
        levels_group = QGroupBox("Channel Levels")
        levels_layout = QVBoxLayout()

        self.level_plot = pg.PlotWidget()
        self.level_plot.setLabel('left', 'Channel')
        self.level_plot.setLabel('bottom', 'Level')
        self.level_plot.setYRange(0, 16)  # Support up to 16 channels
        self.level_plot.setXRange(0, 1)

        self.level_bars = pg.BarGraphItem(x=np.arange(16), height=np.zeros(16), width=0.8)
        self.level_plot.addItem(self.level_bars)

        levels_layout.addWidget(self.level_plot)
        levels_group.setLayout(levels_layout)
        right_panel.addWidget(levels_group)

        # Waveform display
        wave_group = QGroupBox("Beamformed Output")
        wave_layout = QVBoxLayout()

        self.wave_plot = pg.PlotWidget()
        self.wave_plot.setLabel('left', 'Amplitude')
        self.wave_plot.setLabel('bottom', 'Time (s)')
        self.wave_plot.setYRange(-1, 1)

        self.wave_curve = self.wave_plot.plot(pen='y')

        wave_layout.addWidget(self.wave_plot)
        wave_group.setLayout(wave_layout)
        right_panel.addWidget(wave_group)

        content_layout.addLayout(right_panel)
        layout.addLayout(content_layout)

        # Status bar
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

        # Setup timers for periodic updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_displays)
        self.update_timer.start(100)  # Update at 10 Hz

        # Initialize devices after all UI components are created
        if hasattr(self, 'input_device_combo') and hasattr(self, 'output_device_combo'):
            self.update_input_sample_rate()
            self.update_output_sample_rate()
            self.update_output_format()
            self.update_input_device()
            self.update_output_device()
            # Force device settings update after all components are set
            self.update_device_settings()

    def toggle_processing(self):
        """Start or stop audio processing."""
        if not self.processing_active:
            self.audio_processor.start()
            self.processing_active = True
            self.start_button.setText("Stop Processing")
            self.start_button.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    font-size: 16px;
                    padding: 10px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #da190b;
                }
            """)
            self.status_label.setText("Processing active")
        else:
            self.audio_processor.stop()
            self.processing_active = False
            self.start_button.setText("Start Processing")
            self.start_button.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    font-size: 16px;
                    padding: 10px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            self.status_label.setText("Processing stopped")

    def update_input_device(self):
        """Update selected input device."""
        if self.input_device_combo.currentIndex() >= 0:
            device_index = self.input_device_combo.currentData()
            if self.processing_active:
                self.toggle_processing()  # Stop first
            if hasattr(self, 'audio_processor'):
                device_info = self.input_devices[self.input_device_combo.currentIndex()]
                device_name = device_info['name']
                max_channels = device_info['channels']
                device_sample_rate = device_info['sample_rate']

                # Update channel spinbox maximum based on device capabilities
                self.channel_spin.setMaximum(max_channels)
                if self.channel_spin.value() > max_channels:
                    self.channel_spin.setValue(max_channels)

                # Update audio processor device settings (only if all components exist)
                if hasattr(self, 'output_device_combo') and hasattr(self, 'input_sample_rate_combo'):
                    self.update_device_settings()

                print(f"Selected input device: {device_name} (index {device_index}, max {max_channels} ch, {device_sample_rate} Hz)")

    def update_output_device(self):
        """Update selected output device."""
        if self.output_device_combo.currentIndex() >= 0:
            device_index = self.output_device_combo.currentData()
            if self.processing_active:
                self.toggle_processing()  # Stop first
            if hasattr(self, 'audio_processor'):
                device_info = self.output_devices[self.output_device_combo.currentIndex()]
                device_name = device_info['name']
                device_sample_rate = device_info['sample_rate']

                # Update audio processor device settings (only if all components exist)
                if hasattr(self, 'input_device_combo') and hasattr(self, 'input_sample_rate_combo'):
                    self.update_device_settings()

                print(f"Selected output device: {device_name} (index {device_index}, {device_sample_rate} Hz)")

    def update_channel_count(self):
        """Update number of input channels."""
        if self.processing_active:
            self.toggle_processing()  # Stop first
        if hasattr(self, 'audio_processor'):
            self.audio_processor.channels = self.channel_spin.value()
            print(f"Set channel count to: {self.audio_processor.channels}")

    def update_input_sample_rate(self):
        """Update input sample rate."""
        if self.processing_active:
            self.toggle_processing()  # Stop first
        if hasattr(self, 'audio_processor'):
            self.audio_processor.input_sample_rate = self.input_sample_rate_combo.currentData()
            print(f"Set input sample rate to: {self.audio_processor.input_sample_rate} Hz")

    def update_output_sample_rate(self):
        """Update output sample rate."""
        if self.processing_active:
            self.toggle_processing()  # Stop first
        if hasattr(self, 'audio_processor'):
            self.audio_processor.output_sample_rate = self.output_sample_rate_combo.currentData()
            print(f"Set output sample rate to: {self.audio_processor.output_sample_rate} Hz")

    def update_output_format(self):
        """Update output format."""
        if self.processing_active:
            self.toggle_processing()  # Stop first
        if hasattr(self, 'audio_processor'):
            self.audio_processor.output_format = self.output_format_combo.currentData()
            print(f"Set output format to: {self.audio_processor.output_format.__name__}")

    def update_device_settings(self):
        """Update audio processor with current device settings."""
        if not hasattr(self, 'audio_processor'):
            return

        # Check if all required UI components exist
        required_attrs = ['input_device_combo', 'output_device_combo',
                         'input_sample_rate_combo', 'output_sample_rate_combo', 'output_format_combo']
        if not all(hasattr(self, attr) for attr in required_attrs):
            return

        input_device = self.input_device_combo.currentData() if self.input_device_combo.currentIndex() >= 0 else None
        output_device = self.output_device_combo.currentData() if self.output_device_combo.currentIndex() >= 0 else None

        if input_device is not None and output_device is not None:
            # Set devices and sample rates
            self.audio_processor.input_device = input_device
            self.audio_processor.output_device = output_device
            self.audio_processor.input_sample_rate = self.input_sample_rate_combo.currentData()
            self.audio_processor.output_sample_rate = self.output_sample_rate_combo.currentData()
            self.audio_processor.output_format = self.output_format_combo.currentData()
            self.audio_processor.channels = self.channel_spin.value()

            print(f"Updated devices - Input: {input_device} @ {self.audio_processor.input_sample_rate}Hz, "
                  f"Output: {output_device} @ {self.audio_processor.output_sample_rate}Hz ({self.audio_processor.output_format.__name__})")

    def update_beamforming(self):
        """Update beamforming enabled state."""
        self.audio_processor.beamforming_enabled = self.beamform_check.isChecked()

    def update_method(self):
        """Update beamforming method."""
        methods = ["delay_sum", "mvdr", "mvdr_broadband", "superdirective"]
        self.audio_processor.beamform_mode = methods[self.method_combo.currentIndex()]

    def update_doa_method(self):
        """Update DOA estimation method."""
        methods = ["srp_phat", "tdoa_ls"]
        self.audio_processor.doa_method = methods[self.doa_combo.currentIndex()]

    def update_auto_track(self):
        """Update auto-tracking mode."""
        auto_track = self.auto_track_check.isChecked()
        self.audio_processor.auto_track = auto_track
        self.direction_widget.manual_mode = not auto_track

        # Enable/disable manual controls
        self.azimuth_slider.setEnabled(not auto_track)
        self.azimuth_spin.setEnabled(not auto_track)
        self.elevation_slider.setEnabled(not auto_track)
        self.elevation_spin.setEnabled(not auto_track)

    def toggle_debug_recording(self):
        """Toggle debug recording on/off."""
        if not self.audio_processor.debug_recording:
            # Start recording
            record_input = self.debug_input_check.isChecked()
            record_output = self.debug_output_check.isChecked()

            if not record_input and not record_output:
                print("Please select at least one debug recording option (Input or Output)")
                return

            if not self.processing_active:
                print("Please start audio processing first")
                return

            self.audio_processor.start_debug_recording(record_input, record_output)
            self.debug_record_button.setText("Stop Debug Recording")
            self.debug_record_button.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    font-size: 12px;
                    padding: 8px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #da190b;
                }
            """)
            self.debug_input_check.setEnabled(False)
            self.debug_output_check.setEnabled(False)
            self.status_label.setText("Processing active - Debug recording")

        else:
            # Stop recording
            self.audio_processor.stop_debug_recording()
            self.debug_record_button.setText("Start Debug Recording")
            self.debug_record_button.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    font-size: 12px;
                    padding: 8px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)
            self.debug_input_check.setEnabled(True)
            self.debug_output_check.setEnabled(True)
            if self.processing_active:
                self.status_label.setText("Processing active")
            else:
                self.status_label.setText("Ready")

    def manual_direction_changed(self, azimuth, elevation):
        """Handle manual direction change from widget."""
        self.audio_processor.manual_azimuth = azimuth
        self.audio_processor.manual_elevation = elevation

        # Update sliders and spinboxes
        self.azimuth_slider.setValue(int(azimuth))
        self.azimuth_spin.setValue(int(azimuth))
        self.elevation_slider.setValue(int(elevation))
        self.elevation_spin.setValue(int(elevation))

    def manual_slider_changed(self):
        """Handle manual direction change from sliders."""
        azimuth = self.azimuth_slider.value()
        elevation = self.elevation_slider.value()

        self.audio_processor.manual_azimuth = azimuth
        self.audio_processor.manual_elevation = elevation
        self.direction_widget.set_manual_direction(azimuth, elevation)

        # Update spinboxes
        self.azimuth_spin.setValue(azimuth)
        self.elevation_spin.setValue(elevation)

    def manual_spin_changed(self):
        """Handle manual direction change from spinboxes."""
        azimuth = self.azimuth_spin.value()
        elevation = self.elevation_spin.value()

        self.audio_processor.manual_azimuth = azimuth
        self.audio_processor.manual_elevation = elevation
        self.direction_widget.set_manual_direction(azimuth, elevation)

        # Update sliders
        self.azimuth_slider.setValue(azimuth)
        self.elevation_slider.setValue(elevation)

    def update_doa(self, azimuth, elevation, confidence):
        """Update DOA display."""
        self.direction_widget.set_direction(azimuth, elevation, confidence)

        self.azimuth_label.setText(f"Azimuth: {azimuth:.1f}°")
        self.elevation_label.setText(f"Elevation: {elevation:.1f}°")
        self.confidence_label.setText(f"Confidence: {confidence:.3f}")

    def update_levels(self, levels):
        """Update channel level display."""
        # Update bar graph with actual number of channels
        num_channels = len(levels)
        bar_heights = np.zeros(16)  # Max 16 channels display
        bar_heights[:min(num_channels, 16)] = levels[:min(num_channels, 16)]
        self.level_bars.setOpts(x=np.arange(16), height=bar_heights)

        # Update Y-axis range to show active channels
        self.level_plot.setYRange(0, min(num_channels + 1, 16))

    def update_displays(self):
        """Periodic update of waveform display."""
        if self.processing_active and not self.audio_processor.monitor_queue.empty():
            try:
                # Get latest output block from monitor queue (doesn't interfere with audio)
                output_block = self.audio_processor.monitor_queue.get_nowait()

                # Convert to mono for display if stereo
                if len(output_block.shape) > 1 and output_block.shape[1] > 1:
                    mono_block = np.mean(output_block, axis=1)  # Average channels
                else:
                    mono_block = output_block.flatten() if len(output_block.shape) > 1 else output_block

                # Downsample for display
                downsample = 10
                display_data = mono_block[::downsample]

                # Create time axis
                t = np.arange(len(display_data)) / (self.audio_processor.sample_rate / downsample)

                # Update waveform
                self.wave_curve.setData(t, display_data)

            except queue.Empty:
                pass

    def closeEvent(self, event):
        """Clean up when closing."""
        if self.processing_active:
            self.audio_processor.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Set dark theme
    app.setStyle('Fusion')
    palette = app.palette()
    palette.setColor(palette.Window, QColor(53, 53, 53))
    palette.setColor(palette.WindowText, Qt.white)
    palette.setColor(palette.Base, QColor(25, 25, 25))
    palette.setColor(palette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(palette.ToolTipBase, Qt.white)
    palette.setColor(palette.ToolTipText, Qt.white)
    palette.setColor(palette.Text, Qt.white)
    palette.setColor(palette.Button, QColor(53, 53, 53))
    palette.setColor(palette.ButtonText, Qt.white)
    palette.setColor(palette.BrightText, Qt.red)
    palette.setColor(palette.Link, QColor(42, 130, 218))
    palette.setColor(palette.Highlight, QColor(42, 130, 218))
    palette.setColor(palette.HighlightedText, Qt.black)
    app.setPalette(palette)

    window = BeamformerGUI()
    window.show()

    sys.exit(app.exec_())