#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <math.h>
#include <windows.h>

#include "tetrahedral_mic_array.h"

// Global application instance for signal handling
static tetrahedral_app_t *g_app = NULL;

// Signal handler for graceful shutdown
static void signal_handler(int signum) {
    if (g_app) {
        printf("\nReceived signal %d, shutting down...\n", signum);
        g_app->running = 0;
    }
}

// Print usage information
static void print_usage(const char *program_name) {
    printf("Tetrahedral Microphone Array DOA Processing\n");
    printf("Usage: %s [--wav input.wav] [config_file]\n", program_name);
    printf("\n");
    printf("Arguments:\n");
    printf("  --wav file   Use WAV file input instead of live microphone\n");
    printf("  config_file  Path to ODAS configuration file (default: config/tetrahedral_4ch.cfg)\n");
    printf("\n");
    printf("Features:\n");
    printf("  - Real-time 4-channel audio capture from Teensy microphone array\n");
    printf("  - WAV file processing for testing and analysis\n");
    printf("  - Direction of Arrival (DOA) estimation using tetrahedral geometry\n");
    printf("  - Sound source localization in 3D space\n");
    printf("\n");
}

int main(int argc, char *argv[]) {
    tetrahedral_app_t app = {0};
    const char *config_file = "config/tetrahedral_4ch.cfg";
    const char *wav_file = NULL;

    // Parse command line arguments
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--wav") == 0) {
            if (i + 1 >= argc) {
                printf("Error: --wav requires a filename argument\n");
                print_usage(argv[0]);
                return 1;
            }
            wav_file = argv[i + 1];
            i++; // Skip the filename argument
        } else if (strcmp(argv[i], "--help") == 0 || strcmp(argv[i], "-h") == 0) {
            print_usage(argv[0]);
            return 0;
        } else {
            // Assume it's the config file
            config_file = argv[i];
        }
    }

    printf("=== Tetrahedral Microphone Array DOA Processing ===\n");
    printf("Configuration file: %s\n", config_file);
    if (wav_file) {
        printf("Input mode: WAV file (%s)\n", wav_file);
    } else {
        printf("Input mode: Live microphone (WASAPI)\n");
    }
    printf("Sample rate: %d Hz\n", SAMPLE_RATE);
    printf("Channels: %d\n", CHANNELS);
    printf("Frame size: %d samples\n", FRAME_SIZE);
    printf("\n");

    // Set up signal handling
    g_app = &app;
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);

    // Initialize application
    if (tetrahedral_app_init(&app, config_file, wav_file) != 0) {
        fprintf(stderr, "Failed to initialize application\n");
        return 1;
    }

    printf("Application initialized successfully\n");
    printf("Press Ctrl+C to stop processing\n");
    printf("\n");

    // Main processing loop
    app.running = 1;
    int frame_count = 0;

    while (app.running) {
        // Run one processing frame
        if (tetrahedral_app_run(&app) != 0) {
            fprintf(stderr, "Error in processing frame %d\n", frame_count);
            break;
        }

        frame_count++;

        // Print status every 100 frames
        if (frame_count % 100 == 0) {
            printf("Processed %d frames\n", frame_count);
        }

        // Small delay to prevent CPU hogging
        Sleep(10);
    }

    printf("\nShutting down...\n");

    // Cleanup
    tetrahedral_app_cleanup(&app);

    printf("Application terminated successfully\n");
    return 0;
}

int tetrahedral_app_init(tetrahedral_app_t *app, const char *config_file, const char *wav_file) {
    if (!app || !config_file) {
        return -1;
    }

    // Store configuration file path
    app->config_file = strdup(config_file);
    if (!app->config_file) {
        return -1;
    }

    // Store WAV file path if provided
    if (wav_file) {
        app->wav_file = strdup(wav_file);
        if (!app->wav_file) {
            free(app->config_file);
            return -1;
        }
    } else {
        app->wav_file = NULL;
    }

    // Allocate DOA processing structure
    app->doa_proc = (doa_processing_t *)malloc(sizeof(doa_processing_t));
    if (!app->doa_proc) {
        fprintf(stderr, "Failed to allocate DOA processing structure\n");
        return -1;
    }

    // Initialize DOA processing
    if (doa_processing_init(app->doa_proc, config_file) != 0) {
        fprintf(stderr, "Failed to initialize DOA processing\n");
        free(app->doa_proc);
        return -1;
    }

    // Initialize audio capture (WAV file or live microphone)
    if (wav_file) {
        if (audio_capture_init_wav(&app->audio_device, wav_file, CHANNELS, SAMPLE_RATE) != 0) {
            fprintf(stderr, "Failed to initialize WAV file input\n");
            doa_processing_cleanup(app->doa_proc);
            free(app->doa_proc);
            return -1;
        }
        printf("WAV file input initialized: %s (%d channels at %d Hz)\n", wav_file, CHANNELS, SAMPLE_RATE);
    } else {
        if (audio_capture_init(&app->audio_device, CHANNELS, SAMPLE_RATE) != 0) {
            fprintf(stderr, "Failed to initialize audio capture\n");
            doa_processing_cleanup(app->doa_proc);
            free(app->doa_proc);
            return -1;
        }
        printf("Audio capture initialized for %d channels at %d Hz\n", CHANNELS, SAMPLE_RATE);
    }

    return 0;
}

int tetrahedral_app_run(tetrahedral_app_t *app) {
    if (!app || !app->doa_proc || !app->audio_device) {
        return -1;
    }

    // Read audio data
    float audio_buffer[CHANNELS * FRAME_SIZE];

    if (audio_capture_read(app->audio_device, audio_buffer, FRAME_SIZE) != 0) {
        return -1;
    }

    // Amplify quiet audio by 10x for better detection
    for (int i = 0; i < CHANNELS * FRAME_SIZE; i++) {
        audio_buffer[i] *= 10.0f;
    }

    // Debug: Check audio levels going into ODAS
    static int debug_frame_count = 0;
    debug_frame_count++;

    if (debug_frame_count % 500 == 0) {
        float max_level = 0.0f;
        float rms_level = 0.0f;

        for (int i = 0; i < CHANNELS * FRAME_SIZE; i++) {
            float abs_val = fabsf(audio_buffer[i]);
            if (abs_val > max_level) max_level = abs_val;
            rms_level += audio_buffer[i] * audio_buffer[i];
        }
        rms_level = sqrtf(rms_level / (CHANNELS * FRAME_SIZE));

        printf("Audio Input Debug - Frame %d: Max=%.6f, RMS=%.6f, First 4 samples: [%.6f, %.6f, %.6f, %.6f]\n",
               debug_frame_count, max_level, rms_level,
               audio_buffer[0], audio_buffer[1], audio_buffer[2], audio_buffer[3]);

        // Check channel correlation - are all channels the same?
        float ch0_avg = 0, ch1_avg = 0, ch2_avg = 0, ch3_avg = 0;
        for (int i = 0; i < FRAME_SIZE; i++) {
            ch0_avg += audio_buffer[i*4 + 0];
            ch1_avg += audio_buffer[i*4 + 1];
            ch2_avg += audio_buffer[i*4 + 2];
            ch3_avg += audio_buffer[i*4 + 3];
        }
        ch0_avg /= FRAME_SIZE; ch1_avg /= FRAME_SIZE; ch2_avg /= FRAME_SIZE; ch3_avg /= FRAME_SIZE;
        printf("Channel averages: [%.6f, %.6f, %.6f, %.6f]\n", ch0_avg, ch1_avg, ch2_avg, ch3_avg);
    }

    // Process audio with ODAS
    if (process_audio_frame(app->doa_proc, audio_buffer, FRAME_SIZE) != 0) {
        fprintf(stderr, "Error processing audio frame\n");
        return -1;
    }

    return 0;
}

void tetrahedral_app_cleanup(tetrahedral_app_t *app) {
    if (!app) return;

    // Cleanup audio capture
    if (app->audio_device) {
        audio_capture_cleanup(app->audio_device);
        app->audio_device = NULL;
    }

    // Cleanup DOA processing
    if (app->doa_proc) {
        doa_processing_cleanup(app->doa_proc);
        free(app->doa_proc);
        app->doa_proc = NULL;
    }

    // Free configuration file path
    if (app->config_file) {
        free(app->config_file);
        app->config_file = NULL;
    }

    // Free WAV file path
    if (app->wav_file) {
        free(app->wav_file);
        app->wav_file = NULL;
    }
}