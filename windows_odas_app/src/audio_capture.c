#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stddef.h>
#include <math.h>
#include <windows.h>
#include <mmsystem.h>
#include <mmdeviceapi.h>
#include <audioclient.h>
#include <functiondiscoverykeys_devpkey.h>
#include <propidl.h>
#include <mmreg.h>

#include "tetrahedral_mic_array.h"

// Forward declarations
int audio_capture_read_wav(void *device, float *buffer, int frames);

// Use GUID values directly

// Windows audio capture structure
typedef struct {
    IMMDevice *device;
    IAudioClient *audio_client;
    IAudioCaptureClient *capture_client;
    WAVEFORMATEX *wave_format;
    float *audio_buffer;
    int buffer_size;
    int buffer_pos;
    int channels;
    int sample_rate;
    HANDLE event;
} audio_capture_t;

// WAV file capture structure
typedef struct {
    FILE *file;
    int channels;
    int sample_rate;
    int bits_per_sample;
    int data_size;
    int bytes_read;
    int is_wav_mode;
} wav_capture_t;

int audio_capture_init(void **device, int channels, int sample_rate) {
    if (!device || channels <= 0 || sample_rate <= 0) {
        return -1;
    }

    audio_capture_t *capture = calloc(1, sizeof(audio_capture_t));
    if (!capture) {
        return -1;
    }

    capture->channels = channels;
    capture->sample_rate = sample_rate;

    HRESULT hr;
    IMMDeviceEnumerator *enumerator = NULL;

    // Initialize COM
    hr = CoInitializeEx(NULL, COINIT_MULTITHREADED);
    if (FAILED(hr)) {
        fprintf(stderr, "Failed to initialize COM: 0x%08X\n", hr);
        free(capture);
        return -1;
    }

    // Create device enumerator
    const CLSID CLSID_MMDeviceEnumerator_val = {0xbcde0395, 0xe52f, 0x467c, {0x8e,0x3d,0xc4,0x57,0x92,0x91,0x69,0x2e}};
    const IID IID_IMMDeviceEnumerator_val = {0xa95664d2, 0x9614, 0x4f35, {0xa7,0x46,0xde,0x8d,0xb6,0x36,0x17,0xe6}};

    hr = CoCreateInstance(&CLSID_MMDeviceEnumerator_val, NULL, CLSCTX_ALL,
                         &IID_IMMDeviceEnumerator_val, (void**)&enumerator);
    if (FAILED(hr)) {
        fprintf(stderr, "Failed to create device enumerator: 0x%08X\n", hr);
        CoUninitialize();
        free(capture);
        return -1;
    }

    // Enumerate audio devices to find Teensy Audio
    IMMDeviceCollection *devices = NULL;
    hr = enumerator->lpVtbl->EnumAudioEndpoints(enumerator, eCapture, DEVICE_STATE_ACTIVE, &devices);
    if (FAILED(hr)) {
        fprintf(stderr, "Failed to enumerate audio endpoints: 0x%08X\n", hr);
        enumerator->lpVtbl->Release(enumerator);
        CoUninitialize();
        free(capture);
        return -1;
    }

    UINT device_count = 0;
    devices->lpVtbl->GetCount(devices, &device_count);
    printf("Found %d audio capture devices\n", device_count);

    IMMDevice *teensy_device = NULL;
    for (UINT i = 0; i < device_count; i++) {
        IMMDevice *device = NULL;
        hr = devices->lpVtbl->Item(devices, i, &device);
        if (SUCCEEDED(hr)) {
            IPropertyStore *props = NULL;
            hr = device->lpVtbl->OpenPropertyStore(device, STGM_READ, &props);
            if (SUCCEEDED(hr)) {
                PROPVARIANT varName;
                PropVariantInit(&varName);
                hr = props->lpVtbl->GetValue(props, &PKEY_Device_FriendlyName, &varName);
                if (SUCCEEDED(hr)) {
                    // Convert wide string to regular string for comparison
                    char device_name[256] = {0};
                    WideCharToMultiByte(CP_UTF8, 0, varName.pwszVal, -1, device_name, sizeof(device_name), NULL, NULL);
                    printf("Device %d: %s\n", i, device_name);

                    // Look for Teensy Audio device (may appear as "Teensy Audio" or "Digital Audio Interface")
                    if (strstr(device_name, "Teensy") != NULL ||
                        strstr(device_name, "Digital Audio Interface") != NULL) {
                        printf("Found Teensy Audio device: %s\n", device_name);
                        teensy_device = device;
                        device->lpVtbl->AddRef(device);  // Keep reference
                    }
                    PropVariantClear(&varName);
                }
                props->lpVtbl->Release(props);
            }
            if (teensy_device == NULL) {
                device->lpVtbl->Release(device);
            }
        }
    }

    devices->lpVtbl->Release(devices);

    if (teensy_device == NULL) {
        fprintf(stderr, "Teensy Audio device not found. Using default device.\n");
        // Fall back to default device
        hr = enumerator->lpVtbl->GetDefaultAudioEndpoint(enumerator, eCapture, eMultimedia, &capture->device);
        if (FAILED(hr)) {
            fprintf(stderr, "Failed to get default audio endpoint: 0x%08X\n", hr);
            enumerator->lpVtbl->Release(enumerator);
            CoUninitialize();
            free(capture);
            return -1;
        }
    } else {
        capture->device = teensy_device;
    }

    // Activate audio client
    hr = capture->device->lpVtbl->Activate(capture->device, &IID_IAudioClient, CLSCTX_ALL, NULL, (void**)&capture->audio_client);
    if (FAILED(hr)) {
        fprintf(stderr, "Failed to activate audio client: 0x%08X\n", hr);
        capture->device->lpVtbl->Release(capture->device);
        enumerator->lpVtbl->Release(enumerator);
        CoUninitialize();
        free(capture);
        return -1;
    }

    // Get mix format
    hr = capture->audio_client->lpVtbl->GetMixFormat(capture->audio_client, &capture->wave_format);
    if (FAILED(hr)) {
        fprintf(stderr, "Failed to get mix format: 0x%08X\n", hr);
        capture->audio_client->lpVtbl->Release(capture->audio_client);
        capture->device->lpVtbl->Release(capture->device);
        enumerator->lpVtbl->Release(enumerator);
        CoUninitialize();
        free(capture);
        return -1;
    }

    printf("Device format: %d channels, %d Hz, %d bits\n",
           capture->wave_format->nChannels,
           capture->wave_format->nSamplesPerSec,
           capture->wave_format->wBitsPerSample);

    // Try to use device's native format if it matches our requirements
    if (capture->wave_format->nChannels == channels &&
        capture->wave_format->nSamplesPerSec == sample_rate) {
        printf("Device native format matches requirements\n");
    } else {
        // Create our desired format (4 channels, 44.1kHz, 16-bit)
        WAVEFORMATEX desired_format = {
            .wFormatTag = WAVE_FORMAT_PCM,
            .nChannels = channels,
            .nSamplesPerSec = sample_rate,
            .wBitsPerSample = 16,
            .nBlockAlign = channels * 2,
            .nAvgBytesPerSec = sample_rate * channels * 2,
            .cbSize = 0
        };

        // Store original format
        WAVEFORMATEX original_format = *capture->wave_format;

        // Check if desired format is supported
        WAVEFORMATEX *closest_format = NULL;
        hr = capture->audio_client->lpVtbl->IsFormatSupported(capture->audio_client, AUDCLNT_SHAREMODE_SHARED,
                                                             &desired_format, &closest_format);

        if (hr == S_OK) {
            printf("Using desired format: %d channels, %d Hz\n", channels, sample_rate);
            CoTaskMemFree(capture->wave_format);
            capture->wave_format = (WAVEFORMATEX*)CoTaskMemAlloc(sizeof(WAVEFORMATEX));
            memcpy(capture->wave_format, &desired_format, sizeof(WAVEFORMATEX));
        } else if (hr == S_FALSE && closest_format) {
            printf("Desired format not supported, using closest match\n");
            printf("Closest format: %d channels, %d Hz, %d bits\n",
                   closest_format->nChannels, closest_format->nSamplesPerSec, closest_format->wBitsPerSample);
            CoTaskMemFree(capture->wave_format);
            capture->wave_format = closest_format;
        } else if (FAILED(hr)) {
            fprintf(stderr, "Format check failed: 0x%08X\n", hr);
            fprintf(stderr, "Device may not support %d channels at %d Hz\n", channels, sample_rate);
            fprintf(stderr, "Keeping device native format: %d channels, %d Hz\n",
                    original_format.nChannels, original_format.nSamplesPerSec);
            // Keep the original format
        }
    }

    // Use a standard buffer duration (30ms) for initialization
    REFERENCE_TIME buffer_duration = 30 * 10000; // 30ms in 100-nanosecond units
    printf("Using initial buffer duration: %lld (30ms)\n", buffer_duration);

    // Initialize audio client
    hr = capture->audio_client->lpVtbl->Initialize(capture->audio_client, AUDCLNT_SHAREMODE_SHARED,
                                                   AUDCLNT_STREAMFLAGS_EVENTCALLBACK, buffer_duration,
                                                   0, capture->wave_format, NULL);

    // If buffer size alignment failed, get the aligned size and retry
    if (hr == AUDCLNT_E_BUFFER_SIZE_NOT_ALIGNED) {
        printf("Buffer size not aligned, getting aligned buffer size...\n");

        // Get the aligned buffer size
        UINT32 buffer_frames;
        hr = capture->audio_client->lpVtbl->GetBufferSize(capture->audio_client, &buffer_frames);
        if (FAILED(hr)) {
            fprintf(stderr, "Failed to get buffer size: 0x%08X\n", hr);
            CoTaskMemFree(capture->wave_format);
            capture->audio_client->lpVtbl->Release(capture->audio_client);
            capture->device->lpVtbl->Release(capture->device);
            enumerator->lpVtbl->Release(enumerator);
            CoUninitialize();
            free(capture);
            return -1;
        }

        // Release and recreate the audio client
        capture->audio_client->lpVtbl->Release(capture->audio_client);
        hr = capture->device->lpVtbl->Activate(capture->device, &IID_IAudioClient, CLSCTX_ALL, NULL, (void**)&capture->audio_client);
        if (FAILED(hr)) {
            fprintf(stderr, "Failed to reactivate audio client: 0x%08X\n", hr);
            CoTaskMemFree(capture->wave_format);
            capture->device->lpVtbl->Release(capture->device);
            enumerator->lpVtbl->Release(enumerator);
            CoUninitialize();
            free(capture);
            return -1;
        }

        // Calculate aligned buffer duration
        buffer_duration = (REFERENCE_TIME)((10000.0 * 1000 * buffer_frames / capture->wave_format->nSamplesPerSec) + 0.5);
        printf("Retrying with aligned buffer: %d frames, duration: %lld\n", buffer_frames, buffer_duration);

        // Retry initialization with aligned buffer size
        hr = capture->audio_client->lpVtbl->Initialize(capture->audio_client, AUDCLNT_SHAREMODE_SHARED,
                                                       AUDCLNT_STREAMFLAGS_EVENTCALLBACK, buffer_duration,
                                                       0, capture->wave_format, NULL);
    }

    if (FAILED(hr)) {
        fprintf(stderr, "Failed to initialize audio client: 0x%08X\n", hr);
        CoTaskMemFree(capture->wave_format);
        capture->audio_client->lpVtbl->Release(capture->audio_client);
        capture->device->lpVtbl->Release(capture->device);
        enumerator->lpVtbl->Release(enumerator);
        CoUninitialize();
        free(capture);
        return -1;
    }

    // Get capture client
    hr = capture->audio_client->lpVtbl->GetService(capture->audio_client, &IID_IAudioCaptureClient, (void**)&capture->capture_client);
    if (FAILED(hr)) {
        fprintf(stderr, "Failed to get capture client: 0x%08X\n", hr);
        CoTaskMemFree(capture->wave_format);
        capture->audio_client->lpVtbl->Release(capture->audio_client);
        capture->device->lpVtbl->Release(capture->device);
        enumerator->lpVtbl->Release(enumerator);
        CoUninitialize();
        free(capture);
        return -1;
    }

    // Create event for notifications
    capture->event = CreateEvent(NULL, FALSE, FALSE, NULL);
    if (!capture->event) {
        fprintf(stderr, "Failed to create event\n");
        capture->capture_client->lpVtbl->Release(capture->capture_client);
        CoTaskMemFree(capture->wave_format);
        capture->audio_client->lpVtbl->Release(capture->audio_client);
        capture->device->lpVtbl->Release(capture->device);
        enumerator->lpVtbl->Release(enumerator);
        CoUninitialize();
        free(capture);
        return -1;
    }

    // Set event handle
    hr = capture->audio_client->lpVtbl->SetEventHandle(capture->audio_client, capture->event);
    if (FAILED(hr)) {
        fprintf(stderr, "Failed to set event handle: 0x%08X\n", hr);
        CloseHandle(capture->event);
        capture->capture_client->lpVtbl->Release(capture->capture_client);
        CoTaskMemFree(capture->wave_format);
        capture->audio_client->lpVtbl->Release(capture->audio_client);
        capture->device->lpVtbl->Release(capture->device);
        enumerator->lpVtbl->Release(enumerator);
        CoUninitialize();
        free(capture);
        return -1;
    }

    // Start capture
    hr = capture->audio_client->lpVtbl->Start(capture->audio_client);
    if (FAILED(hr)) {
        fprintf(stderr, "Failed to start audio capture: 0x%08X\n", hr);
        CloseHandle(capture->event);
        capture->capture_client->lpVtbl->Release(capture->capture_client);
        CoTaskMemFree(capture->wave_format);
        capture->audio_client->lpVtbl->Release(capture->audio_client);
        capture->device->lpVtbl->Release(capture->device);
        enumerator->lpVtbl->Release(enumerator);
        CoUninitialize();
        free(capture);
        return -1;
    }

    // Allocate audio buffer
    capture->buffer_size = BUFFER_SIZE * channels;
    capture->audio_buffer = calloc(capture->buffer_size, sizeof(float));
    if (!capture->audio_buffer) {
        fprintf(stderr, "Failed to allocate audio buffer\n");
        audio_capture_cleanup(capture);
        return -1;
    }

    enumerator->lpVtbl->Release(enumerator);

    *device = capture;
    printf("WASAPI audio capture initialized and started successfully\n");
    return 0;
}

int audio_capture_read(void *device, float *buffer, int frames) {
    if (!device || !buffer || frames <= 0) {
        return -1;
    }

    // Check if this is a WAV file device by checking if the device pointer
    // points to a wav_capture_t structure with is_wav_mode set
    // We need to be careful about the casting since both structs have different layouts
    int *is_wav_mode_ptr = (int*)((char*)device + offsetof(wav_capture_t, is_wav_mode));
    if (*is_wav_mode_ptr == 1) {
        return audio_capture_read_wav(device, buffer, frames);
    }

    audio_capture_t *capture = (audio_capture_t *)device;
    int samples_read = 0;
    int samples_needed = frames * capture->channels;

    // Read from internal buffer first if we have leftover data
    if (capture->buffer_pos > 0) {
        int samples_to_copy = (samples_needed < capture->buffer_pos) ? samples_needed : capture->buffer_pos;
        memcpy(buffer, capture->audio_buffer, samples_to_copy * sizeof(float));
        samples_read = samples_to_copy;

        // Move remaining data to beginning of buffer
        if (capture->buffer_pos > samples_to_copy) {
            memmove(capture->audio_buffer,
                    capture->audio_buffer + samples_to_copy,
                    (capture->buffer_pos - samples_to_copy) * sizeof(float));
        }
        capture->buffer_pos -= samples_to_copy;
    }

    // Read more data from WASAPI if needed
    while (samples_read < samples_needed) {
        // Wait for audio data (with timeout)
        DWORD wait_result = WaitForSingleObject(capture->event, 100);
        if (wait_result != WAIT_OBJECT_0) {
            // Timeout or error - fill remaining with zeros
            for (int i = samples_read; i < samples_needed; i++) {
                buffer[i] = 0.0f;
            }
            return 0;
        }

        BYTE *data = NULL;
        UINT32 frames_available = 0;
        DWORD flags = 0;

        HRESULT hr = capture->capture_client->lpVtbl->GetBuffer(
            capture->capture_client, &data, &frames_available, &flags, NULL, NULL);

        if (FAILED(hr)) {
            if (hr == AUDCLNT_S_BUFFER_EMPTY) {
                // No data available yet
                continue;
            }
            fprintf(stderr, "Failed to get buffer: 0x%08X\n", hr);
            return -1;
        }

        if (frames_available == 0) {
            capture->capture_client->lpVtbl->ReleaseBuffer(capture->capture_client, frames_available);
            continue;
        }

        // Convert audio data based on format
        int samples_available = frames_available * capture->channels;
        int samples_to_copy = samples_available;
        if (samples_read + samples_to_copy > samples_needed) {
            samples_to_copy = samples_needed - samples_read;
        }

        // Handle different audio formats
        if (capture->wave_format->wBitsPerSample == 32) {
            if (capture->wave_format->wFormatTag == WAVE_FORMAT_IEEE_FLOAT ||
                (capture->wave_format->wFormatTag == WAVE_FORMAT_EXTENSIBLE &&
                 ((WAVEFORMATEXTENSIBLE*)capture->wave_format)->SubFormat.Data1 == WAVE_FORMAT_IEEE_FLOAT)) {
                // 32-bit float - direct copy
                memcpy(buffer + samples_read, data, samples_to_copy * sizeof(float));
            } else {
                // 32-bit integer - convert to float
                int32_t *int_data = (int32_t*)data;
                for (int i = 0; i < samples_to_copy; i++) {
                    buffer[samples_read + i] = int_data[i] / 2147483648.0f;
                }
            }
        } else if (capture->wave_format->wBitsPerSample == 16) {
            // 16-bit integer - convert to float
            int16_t *int_data = (int16_t*)data;
            for (int i = 0; i < samples_to_copy; i++) {
                buffer[samples_read + i] = int_data[i] / 32768.0f;
            }
        } else if (capture->wave_format->wBitsPerSample == 24) {
            // 24-bit integer - convert to float
            uint8_t *byte_data = (uint8_t*)data;
            for (int i = 0; i < samples_to_copy; i++) {
                int32_t sample = (byte_data[i*3] << 8) | (byte_data[i*3+1] << 16) | (byte_data[i*3+2] << 24);
                buffer[samples_read + i] = sample / 2147483648.0f;
            }
        }

        samples_read += samples_to_copy;

        // Store excess data in internal buffer if any
        if (samples_available > samples_to_copy) {
            int excess = samples_available - samples_to_copy;
            if (excess > capture->buffer_size) {
                excess = capture->buffer_size;
            }

            // Convert and store excess data
            if (capture->wave_format->wBitsPerSample == 32) {
                if (capture->wave_format->wFormatTag == WAVE_FORMAT_IEEE_FLOAT ||
                    (capture->wave_format->wFormatTag == WAVE_FORMAT_EXTENSIBLE &&
                     ((WAVEFORMATEXTENSIBLE*)capture->wave_format)->SubFormat.Data1 == WAVE_FORMAT_IEEE_FLOAT)) {
                    memcpy(capture->audio_buffer,
                           ((float*)data) + samples_to_copy,
                           excess * sizeof(float));
                } else {
                    int32_t *int_data = ((int32_t*)data) + samples_to_copy;
                    for (int i = 0; i < excess; i++) {
                        capture->audio_buffer[i] = int_data[i] / 2147483648.0f;
                    }
                }
            } else if (capture->wave_format->wBitsPerSample == 16) {
                int16_t *int_data = ((int16_t*)data) + samples_to_copy;
                for (int i = 0; i < excess; i++) {
                    capture->audio_buffer[i] = int_data[i] / 32768.0f;
                }
            }
            capture->buffer_pos = excess;
        }

        capture->capture_client->lpVtbl->ReleaseBuffer(capture->capture_client, frames_available);

        if (samples_read >= samples_needed) {
            break;
        }
    }

    return 0;
}

void audio_capture_cleanup(void *device) {
    if (!device) return;

    // Check if this is a WAV file device
    wav_capture_t *wav_capture = (wav_capture_t *)device;
    if (wav_capture->is_wav_mode) {
        if (wav_capture->file) {
            fclose(wav_capture->file);
        }
        free(wav_capture);
        return;
    }

    audio_capture_t *capture = (audio_capture_t *)device;

    if (capture->audio_client) {
        capture->audio_client->lpVtbl->Stop(capture->audio_client);
    }

    if (capture->event) {
        CloseHandle(capture->event);
    }

    if (capture->capture_client) {
        capture->capture_client->lpVtbl->Release(capture->capture_client);
    }

    if (capture->wave_format) {
        CoTaskMemFree(capture->wave_format);
    }

    if (capture->audio_client) {
        capture->audio_client->lpVtbl->Release(capture->audio_client);
    }

    if (capture->device) {
        capture->device->lpVtbl->Release(capture->device);
    }

    if (capture->audio_buffer) {
        free(capture->audio_buffer);
    }

    CoUninitialize();
    free(capture);
}

// WAV file functions
int audio_capture_init_wav(void **device, const char *wav_file, int channels, int sample_rate) {
    if (!device || !wav_file || channels <= 0 || sample_rate <= 0) {
        return -1;
    }

    wav_capture_t *capture = calloc(1, sizeof(wav_capture_t));
    if (!capture) {
        return -1;
    }

    // Open WAV file
    capture->file = fopen(wav_file, "rb");
    if (!capture->file) {
        printf("Error: Cannot open WAV file: %s\n", wav_file);
        free(capture);
        return -1;
    }

    // Read WAV header
    char chunk_id[4];
    uint32_t chunk_size;
    char format[4];

    // RIFF header
    if (fread(chunk_id, 1, 4, capture->file) != 4 || memcmp(chunk_id, "RIFF", 4) != 0) {
        printf("Error: Not a valid RIFF file\n");
        fclose(capture->file);
        free(capture);
        return -1;
    }

    fread(&chunk_size, 4, 1, capture->file);

    if (fread(format, 1, 4, capture->file) != 4 || memcmp(format, "WAVE", 4) != 0) {
        printf("Error: Not a valid WAVE file\n");
        fclose(capture->file);
        free(capture);
        return -1;
    }

    // Find fmt chunk
    while (1) {
        if (fread(chunk_id, 1, 4, capture->file) != 4) {
            printf("Error: fmt chunk not found\n");
            fclose(capture->file);
            free(capture);
            return -1;
        }

        fread(&chunk_size, 4, 1, capture->file);

        if (memcmp(chunk_id, "fmt ", 4) == 0) {
            // Read format data
            uint16_t audio_format, num_channels, bits_per_sample;
            uint32_t sample_rate_file, byte_rate;
            uint16_t block_align;

            fread(&audio_format, 2, 1, capture->file);
            fread(&num_channels, 2, 1, capture->file);
            fread(&sample_rate_file, 4, 1, capture->file);
            fread(&byte_rate, 4, 1, capture->file);
            fread(&block_align, 2, 1, capture->file);
            fread(&bits_per_sample, 2, 1, capture->file);

            // Skip any extra format bytes
            if (chunk_size > 16) {
                fseek(capture->file, chunk_size - 16, SEEK_CUR);
            }

            printf("WAV file format: %d channels, %d Hz, %d bits\n",
                   num_channels, sample_rate_file, bits_per_sample);

            // Verify format matches expectations
            if (num_channels != channels) {
                printf("Error: WAV file has %d channels, expected %d\n", num_channels, channels);
                fclose(capture->file);
                free(capture);
                return -1;
            }

            if (sample_rate_file != sample_rate) {
                printf("Warning: WAV file has %d Hz, expected %d Hz\n", sample_rate_file, sample_rate);
            }

            capture->channels = num_channels;
            capture->sample_rate = sample_rate_file;
            capture->bits_per_sample = bits_per_sample;
            capture->is_wav_mode = 1;
            break;
        } else {
            // Skip this chunk
            fseek(capture->file, chunk_size, SEEK_CUR);
        }
    }

    // Find data chunk
    while (1) {
        if (fread(chunk_id, 1, 4, capture->file) != 4) {
            printf("Error: data chunk not found\n");
            fclose(capture->file);
            free(capture);
            return -1;
        }

        fread(&chunk_size, 4, 1, capture->file);

        if (memcmp(chunk_id, "data", 4) == 0) {
            capture->data_size = chunk_size;
            capture->bytes_read = 0;
            printf("WAV data chunk size: %d bytes\n", chunk_size);
            break;
        } else {
            // Skip this chunk
            fseek(capture->file, chunk_size, SEEK_CUR);
        }
    }

    *device = capture;
    return 0;
}

// WAV file read function
int audio_capture_read_wav(void *device, float *buffer, int frames) {
    wav_capture_t *capture = (wav_capture_t *)device;
    if (!capture || !capture->file) {
        return -1;
    }

    int samples_needed = frames * capture->channels;
    int bytes_per_sample = capture->bits_per_sample / 8;
    int bytes_to_read = samples_needed * bytes_per_sample;

    // Check if we have enough data left
    if (capture->bytes_read + bytes_to_read > capture->data_size) {
        bytes_to_read = capture->data_size - capture->bytes_read;
        if (bytes_to_read <= 0) {
            // End of file - fill with zeros
            memset(buffer, 0, samples_needed * sizeof(float));
            return 0;
        }
    }

    // Read raw data from file
    void *raw_buffer = malloc(bytes_to_read);
    if (!raw_buffer) {
        return -1;
    }

    size_t bytes_read = fread(raw_buffer, 1, bytes_to_read, capture->file);
    if (bytes_read == 0) {
        free(raw_buffer);
        // End of file - fill with zeros
        memset(buffer, 0, samples_needed * sizeof(float));
        return 0;
    }

    capture->bytes_read += bytes_read;
    int samples_read = bytes_read / bytes_per_sample;

    // Convert to float based on bit depth
    if (capture->bits_per_sample == 16) {
        int16_t *int16_data = (int16_t *)raw_buffer;
        for (int i = 0; i < samples_read; i++) {
            buffer[i] = int16_data[i] / 32768.0f;
        }
    } else if (capture->bits_per_sample == 32) {
        int32_t *int32_data = (int32_t *)raw_buffer;
        for (int i = 0; i < samples_read; i++) {
            buffer[i] = int32_data[i] / 2147483648.0f;
        }
    } else {
        printf("Error: Unsupported bit depth: %d\n", capture->bits_per_sample);
        free(raw_buffer);
        return -1;
    }

    // Fill remaining with zeros if we didn't read enough
    if (samples_read < samples_needed) {
        memset(&buffer[samples_read], 0, (samples_needed - samples_read) * sizeof(float));
    }

    free(raw_buffer);
    return 0;
}