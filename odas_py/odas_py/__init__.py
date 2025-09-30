"""
ODAS-Py: Python bindings for ODAS (Open embeddeD Audition System)

Provides high-performance native audio processing for:
- Sound Source Localization (SSL)
- Sound Source Tracking (SST)
- Sound Source Separation (SSS)
"""

import sys
import os

# On Windows, add the package directory to DLL search path
# This allows the C extension to find its dependency DLLs
if sys.platform == 'win32':
    package_dir = os.path.dirname(os.path.abspath(__file__))
    if hasattr(os, 'add_dll_directory'):
        os.add_dll_directory(package_dir)
    else:
        # Fallback for older Python versions
        os.environ['PATH'] = package_dir + os.pathsep + os.environ.get('PATH', '')

# C extension modules - import first before other modules
HAS_C_EXTENSION = False
try:
    from . import _odas_core
    HAS_C_EXTENSION = True
except ImportError:
    pass  # Will use simulation mode

from .odaslive import OdasLive, list_audio_devices, print_audio_devices
from .odas_processor import OdasProcessor
from .version import __version__

__all__ = ['OdasLive', 'OdasProcessor', 'list_audio_devices', 'print_audio_devices',
           '__version__', 'HAS_C_EXTENSION']