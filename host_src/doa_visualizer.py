"""
Real-time DOA visualization using PyQt5 and matplotlib.
Displays sound source directions on 2D and 3D plots.
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patches as patches
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                            QWidget, QPushButton, QLabel, QSpinBox, QCheckBox,
                            QGroupBox, QGridLayout)
from PyQt5.QtCore import QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QFont
from mpl_toolkits.mplot3d import Axes3D
import time
from collections import deque

from audio_capture import TeensyAudioCapture
from doa_processing import DOAProcessor


class DOAVisualizer(QMainWindow):
    """Main window for real-time DOA visualization."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ambisonic Microphone - Direction of Arrival")
        self.setGeometry(100, 100, 1400, 800)

        # Initialize components
        self.audio_capture = TeensyAudioCapture()
        self.doa_processor = DOAProcessor()

        # Data storage for history
        self.history_length = 100
        self.azimuth_history = deque(maxlen=self.history_length)
        self.elevation_history = deque(maxlen=self.history_length)
        self.confidence_history = deque(maxlen=self.history_length)
        self.time_history = deque(maxlen=self.history_length)

        # Processing settings
        self.block_size = 1024
        self.use_srp_phat = True
        self.show_confidence = True
        self.min_confidence = 0.1

        # Current DOA results
        self.current_azimuth = 0.0
        self.current_elevation = 0.0
        self.current_confidence = 0.0

        self.setup_ui()
        self.setup_audio()

    def setup_ui(self):
        """Setup the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        # Left panel: Plots
        plots_widget = QWidget()
        plots_layout = QVBoxLayout(plots_widget)

        # 2D Azimuth/Elevation plot
        self.fig_2d = Figure(figsize=(8, 6))
        self.canvas_2d = FigureCanvas(self.fig_2d)
        self.ax_2d = self.fig_2d.add_subplot(111, projection='polar')
        self.ax_2d.set_title("Sound Source Direction (Top View)")
        self.ax_2d.set_theta_zero_location('N')
        self.ax_2d.set_theta_direction(-1)
        plots_layout.addWidget(self.canvas_2d)

        # 3D Sphere plot
        self.fig_3d = Figure(figsize=(8, 6))
        self.canvas_3d = FigureCanvas(self.fig_3d)
        self.ax_3d = self.fig_3d.add_subplot(111, projection='3d')
        self.ax_3d.set_title("3D Direction Visualization")
        plots_layout.addWidget(self.canvas_3d)

        main_layout.addWidget(plots_widget, 2)

        # Right panel: Controls and info
        control_widget = QWidget()
        control_widget.setMaximumWidth(300)
        control_layout = QVBoxLayout(control_widget)

        # Status group
        status_group = QGroupBox("Status")
        status_layout = QGridLayout(status_group)

        self.status_label = QLabel("Stopped")
        self.status_label.setFont(QFont("Arial", 10, QFont.Bold))
        status_layout.addWidget(QLabel("Status:"), 0, 0)
        status_layout.addWidget(self.status_label, 0, 1)

        self.device_label = QLabel("No device")
        status_layout.addWidget(QLabel("Device:"), 1, 0)
        status_layout.addWidget(self.device_label, 1, 1)

        control_layout.addWidget(status_group)

        # Current readings group
        readings_group = QGroupBox("Current DOA")
        readings_layout = QGridLayout(readings_group)

        self.azimuth_label = QLabel("0.0°")
        self.azimuth_label.setFont(QFont("Arial", 12, QFont.Bold))
        readings_layout.addWidget(QLabel("Azimuth:"), 0, 0)
        readings_layout.addWidget(self.azimuth_label, 0, 1)

        self.elevation_label = QLabel("0.0°")
        self.elevation_label.setFont(QFont("Arial", 12, QFont.Bold))
        readings_layout.addWidget(QLabel("Elevation:"), 1, 0)
        readings_layout.addWidget(self.elevation_label, 1, 1)

        self.confidence_label = QLabel("0.000")
        readings_layout.addWidget(QLabel("Confidence:"), 2, 0)
        readings_layout.addWidget(self.confidence_label, 2, 1)

        control_layout.addWidget(readings_group)

        # Settings group
        settings_group = QGroupBox("Settings")
        settings_layout = QGridLayout(settings_group)

        # Block size
        settings_layout.addWidget(QLabel("Block Size:"), 0, 0)
        self.block_size_spin = QSpinBox()
        self.block_size_spin.setRange(256, 4096)
        self.block_size_spin.setValue(self.block_size)
        self.block_size_spin.setSingleStep(256)
        self.block_size_spin.valueChanged.connect(self.on_block_size_changed)
        settings_layout.addWidget(self.block_size_spin, 0, 1)

        # Algorithm selection
        self.srp_phat_checkbox = QCheckBox("Use SRP-PHAT")
        self.srp_phat_checkbox.setChecked(self.use_srp_phat)
        self.srp_phat_checkbox.stateChanged.connect(self.on_algorithm_changed)
        settings_layout.addWidget(self.srp_phat_checkbox, 1, 0, 1, 2)

        # Confidence filtering
        self.confidence_checkbox = QCheckBox("Filter by confidence")
        self.confidence_checkbox.setChecked(self.show_confidence)
        settings_layout.addWidget(self.confidence_checkbox, 2, 0, 1, 2)

        control_layout.addWidget(settings_group)

        # Control buttons
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_processing)
        control_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_processing)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.stop_button)

        self.clear_button = QPushButton("Clear History")
        self.clear_button.clicked.connect(self.clear_history)
        control_layout.addWidget(self.clear_button)

        control_layout.addStretch()

        main_layout.addWidget(control_widget, 1)

        # Setup update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_plots)

    def setup_audio(self):
        """Setup audio processing."""
        self.audio_capture.set_audio_callback(self.process_audio_block)

        # Try to get device info
        device_info = self.audio_capture.get_device_info()
        if device_info:
            device_name = device_info.get('name', 'Unknown')
            self.device_label.setText(device_name[:30])

    def process_audio_block(self, audio_data: np.ndarray, timestamp: float):
        """Process incoming audio block and compute DOA."""
        try:
            if self.use_srp_phat:
                azimuth, elevation, confidence = self.doa_processor.srp_phat_doa(audio_data)
            else:
                tdoa_estimates = self.doa_processor.compute_tdoa_estimates(audio_data)
                azimuth, elevation, confidence = self.doa_processor.least_squares_doa(tdoa_estimates)

            # Apply confidence filtering
            if self.show_confidence and confidence < self.min_confidence:
                return

            # Update current values
            self.current_azimuth = azimuth
            self.current_elevation = elevation
            self.current_confidence = confidence

            # Add to history
            current_time = time.time()
            self.azimuth_history.append(azimuth)
            self.elevation_history.append(elevation)
            self.confidence_history.append(confidence)
            self.time_history.append(current_time)

        except Exception as e:
            print(f"Error processing audio: {e}")

    def update_plots(self):
        """Update visualization plots."""
        # Update text displays
        self.azimuth_label.setText(f"{self.current_azimuth:.1f}°")
        self.elevation_label.setText(f"{self.current_elevation:.1f}°")
        self.confidence_label.setText(f"{self.current_confidence:.3f}")

        if len(self.azimuth_history) > 0:
            self.update_2d_plot()
            self.update_3d_plot()

    def update_2d_plot(self):
        """Update 2D polar plot."""
        self.ax_2d.clear()
        self.ax_2d.set_title("Sound Source Direction (Top View)")
        self.ax_2d.set_theta_zero_location('N')
        self.ax_2d.set_theta_direction(-1)

        if len(self.azimuth_history) > 0:
            # Convert azimuth to polar coordinates
            azimuths = np.array(self.azimuth_history)
            elevations = np.array(self.elevation_history)
            confidences = np.array(self.confidence_history)

            # Plot recent history as trail
            if len(azimuths) > 1:
                theta = np.radians(azimuths)
                # Use elevation to determine radius (90° = center, 0° = edge)
                r = (90 - np.abs(elevations)) / 90

                # Color by confidence
                colors = plt.cm.viridis(confidences / (max(confidences) if max(confidences) > 0 else 1))

                self.ax_2d.scatter(theta, r, c=colors, s=20, alpha=0.6)

            # Highlight current position
            current_theta = np.radians(self.current_azimuth)
            current_r = (90 - abs(self.current_elevation)) / 90
            self.ax_2d.scatter(current_theta, current_r, c='red', s=100, marker='o', edgecolor='black', linewidth=2)

            # Set radial limits and labels
            self.ax_2d.set_ylim(0, 1)
            self.ax_2d.set_rticks([0.25, 0.5, 0.75, 1.0])
            self.ax_2d.set_rgrids([0.25, 0.5, 0.75, 1.0], ['75°', '45°', '22.5°', '0°'])

        self.canvas_2d.draw()

    def update_3d_plot(self):
        """Update 3D sphere plot."""
        self.ax_3d.clear()

        if len(self.azimuth_history) > 0:
            # Convert spherical to Cartesian coordinates
            azimuths = np.array(self.azimuth_history)
            elevations = np.array(self.elevation_history)
            confidences = np.array(self.confidence_history)

            az_rad = np.radians(azimuths)
            el_rad = np.radians(elevations)

            x = np.cos(el_rad) * np.cos(az_rad)
            y = np.cos(el_rad) * np.sin(az_rad)
            z = np.sin(el_rad)

            # Plot trail
            colors = plt.cm.viridis(confidences / (max(confidences) if max(confidences) > 0 else 1))
            self.ax_3d.scatter(x, y, z, c=colors, s=20, alpha=0.6)

            # Current position
            current_az = np.radians(self.current_azimuth)
            current_el = np.radians(self.current_elevation)
            current_x = np.cos(current_el) * np.cos(current_az)
            current_y = np.cos(current_el) * np.sin(current_az)
            current_z = np.sin(current_el)

            self.ax_3d.scatter(current_x, current_y, current_z, c='red', s=100, marker='o',
                              edgecolor='black', linewidth=2)

            # Draw coordinate sphere wireframe
            u = np.linspace(0, 2 * np.pi, 20)
            v = np.linspace(0, np.pi, 20)
            sphere_x = np.outer(np.cos(u), np.sin(v))
            sphere_y = np.outer(np.sin(u), np.sin(v))
            sphere_z = np.outer(np.ones(np.size(u)), np.cos(v))

            self.ax_3d.plot_wireframe(sphere_x, sphere_y, sphere_z, alpha=0.1, color='gray')

        self.ax_3d.set_xlabel('X (East)')
        self.ax_3d.set_ylabel('Y (North)')
        self.ax_3d.set_zlabel('Z (Up)')
        self.ax_3d.set_title('3D Sound Source Direction')

        # Set equal aspect ratio
        self.ax_3d.set_xlim([-1, 1])
        self.ax_3d.set_ylim([-1, 1])
        self.ax_3d.set_zlim([-1, 1])

        self.canvas_3d.draw()

    def start_processing(self):
        """Start audio processing and visualization."""
        if self.audio_capture.start_capture(block_size=self.block_size):
            self.status_label.setText("Running")
            self.status_label.setStyleSheet("color: green")
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.update_timer.start(50)  # Update at 20 FPS

    def stop_processing(self):
        """Stop audio processing."""
        self.audio_capture.stop_capture()
        self.update_timer.stop()
        self.status_label.setText("Stopped")
        self.status_label.setStyleSheet("color: red")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def clear_history(self):
        """Clear DOA history."""
        self.azimuth_history.clear()
        self.elevation_history.clear()
        self.confidence_history.clear()
        self.time_history.clear()
        self.update_plots()

    def on_block_size_changed(self, value):
        """Handle block size change."""
        self.block_size = value
        if self.audio_capture.is_running:
            self.stop_processing()

    def on_algorithm_changed(self, state):
        """Handle algorithm selection change."""
        self.use_srp_phat = (state == 2)  # Checked state

    def closeEvent(self, event):
        """Handle window close event."""
        self.stop_processing()
        event.accept()


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)

    # Set application properties
    app.setApplicationName("Ambisonic DOA Visualizer")
    app.setOrganizationName("Teensy Audio Lab")

    try:
        # Create and show main window
        window = DOAVisualizer()
        window.show()

        # Run application
        sys.exit(app.exec_())

    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()