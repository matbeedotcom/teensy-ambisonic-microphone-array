#include <stdio.h>
#include <windows.h>
#include <mmsystem.h>

int main() {
    printf("Audio header test program\n");

    // Test basic audio types
    WAVEFORMATEX wave_format = {
        .wFormatTag = WAVE_FORMAT_PCM,
        .nChannels = 2,
        .nSamplesPerSec = 44100,
        .wBitsPerSample = 16,
        .nBlockAlign = 4,
        .nAvgBytesPerSec = 44100 * 4,
        .cbSize = 0
    };

    printf("Wave format: %d channels, %d Hz, %d bits\n",
           wave_format.nChannels,
           wave_format.nSamplesPerSec,
           wave_format.wBitsPerSample);

    printf("Audio test completed successfully!\n");
    return 0;
}