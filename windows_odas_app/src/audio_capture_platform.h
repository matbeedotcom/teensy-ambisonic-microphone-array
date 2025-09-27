#ifndef AUDIO_CAPTURE_PLATFORM_H
#define AUDIO_CAPTURE_PLATFORM_H

#include "tetrahedral_mic_array.h"

// Platform-specific audio capture implementation
#ifdef _WIN32
    #include "audio_capture_windows.h"
#else
    #include "audio_capture_dummy.h"
#endif

#endif // AUDIO_CAPTURE_PLATFORM_H