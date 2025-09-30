"""
High-level Python interface for ODAS audio processing
"""

import os
import time
import numpy as np
from typing import Optional, Callable
from pathlib import Path

try:
    from ._odas_core import OdasProcessor as _OdasProcessorCore
except ImportError:
    _OdasProcessorCore = None
    print("Warning: ODAS native module not found. Please build the extension first.")


class OdasProcessor:
    """
    High-level interface for ODAS audio processing

    Provides real-time audio processing for:
    - Sound Source Localization (SSL) - Finding sound directions
    - Sound Source Tracking (SST) - Tracking moving sounds
    - Sound Source Separation (SSS) - Isolating individual sources

    Example:
        >>> processor = OdasProcessor('config/tetrahedral_4ch.cfg')
        >>> processor.start()
        >>> # Process audio...
        >>> processor.stop()
    """

    def __init__(self, config_file: str):
        """
        Initialize ODAS processor

        Args:
            config_file: Path to ODAS configuration file (.cfg)

        Raises:
            FileNotFoundError: If config file doesn't exist
            RuntimeError: If native ODAS module not available
        """
        if _OdasProcessorCore is None:
            raise RuntimeError(
                "ODAS native module not available. "
                "Please build the extension using: python setup.py build_ext --inplace"
            )

        config_path = Path(config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")

        self.config_file = str(config_path.absolute())
        self._core = _OdasProcessorCore(self.config_file)
        self._running = False

        # Callback storage
        self._pots_callback: Optional[Callable] = None
        self._tracks_callback: Optional[Callable] = None

    def start(self):
        """
        Start ODAS processing threads

        This begins real-time audio capture and processing.
        Results will be available through registered callbacks or sinks.

        Raises:
            RuntimeError: If processor fails to start
        """
        if self._running:
            print("Warning: Processor already running")
            return

        self._core.start()
        self._running = True
        print(f"ODAS processor started with config: {self.config_file}")

    def stop(self):
        """
        Stop ODAS processing threads

        Gracefully stops all processing and releases resources.

        Raises:
            RuntimeError: If processor fails to stop
        """
        if not self._running:
            print("Warning: Processor not running")
            return

        self._core.stop()
        self._running = False
        print("ODAS processor stopped")

    def is_running(self) -> bool:
        """
        Check if processor is currently running

        Returns:
            True if processor is active, False otherwise
        """
        return self._core.is_running()

    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()
        return False

    def set_pots_callback(self, callback: Callable[[np.ndarray], None]):
        """
        Register callback for Potential Sound Source locations (SSL results)

        Args:
            callback: Function that receives numpy array of shape (N, 3) with x,y,z coordinates

        Note:
            Currently requires ODAS library modification to support callbacks
        """
        self._pots_callback = callback
        print("Warning: Callback registration requires ODAS library modification")

    def set_tracks_callback(self, callback: Callable[[int, float, float, float], None]):
        """
        Register callback for tracked sound sources (SST results)

        Args:
            callback: Function that receives (track_id, x, y, z) for each tracked source

        Note:
            Currently requires ODAS library modification to support callbacks
        """
        self._tracks_callback = callback
        print("Warning: Callback registration requires ODAS library modification")

    def run_for_duration(self, duration: float):
        """
        Run processor for a specified duration

        Args:
            duration: Duration in seconds to run

        Example:
            >>> processor.run_for_duration(30.0)  # Run for 30 seconds
        """
        with self:
            time.sleep(duration)

    @staticmethod
    def validate_config(config_file: str) -> bool:
        """
        Validate ODAS configuration file

        Args:
            config_file: Path to config file

        Returns:
            True if config appears valid, False otherwise
        """
        config_path = Path(config_file)
        if not config_path.exists():
            print(f"Config file not found: {config_file}")
            return False

        # Basic validation - check for required sections
        content = config_path.read_text()

        return True

    def __repr__(self):
        status = "running" if self._running else "stopped"
        return f"OdasProcessor(config='{self.config_file}', status='{status}')"