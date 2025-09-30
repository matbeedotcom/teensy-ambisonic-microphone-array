"""
ODAS-Py: Python bindings for ODAS (Open embeddeD Audition System)

Provides high-performance native audio processing for:
- Sound Source Localization (SSL)
- Sound Source Tracking (SST)
- Sound Source Separation (SSS)
"""

from .odaslive import OdasLive, list_audio_devices, print_audio_devices
from .version import __version__

# C extension modules
try:
    from . import _odas_core
    HAS_C_EXTENSION = True
except ImportError:
    HAS_C_EXTENSION = False

__all__ = ['OdasLive', 'list_audio_devices', 'print_audio_devices',
           '__version__', 'HAS_C_EXTENSION']