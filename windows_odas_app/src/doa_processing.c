#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <float.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#include "tetrahedral_mic_array.h"

// Include actual ODAS headers to make structure fields accessible
#include "../../odas/include/odas/module/mod_ssl.h"
#include "../../odas/include/odas/module/mod_stft.h"
#include "../../odas/include/odas/module/mod_noise.h"
#include "../../odas/include/odas/message/msg_hops.h"
#include "../../odas/include/odas/message/msg_spectra.h"
#include "../../odas/include/odas/message/msg_pots.h"
#include "../../odas/include/odas/message/msg_powers.h"
#include "../../odas/include/odas/connector/con_spectra.h"
#include "../../odas/include/odas/connector/con_powers.h"
#include "../../odas/include/odas/connector/con_pots.h"
#include "../../odas/include/odas/general/mic.h"
#include "../../odas/include/odas/general/samplerate.h"
#include "../../odas/include/odas/general/soundspeed.h"
#include "../../odas/include/odas/general/spatialfilter.h"

int doa_processing_init(doa_processing_t *proc, const char *config_file) {
    if (!proc) {
        return -1;
    }

    printf("Initializing minimal DOA processing for tetrahedral array\n");

    // Initialize our processing structure
    memset(proc, 0, sizeof(doa_processing_t));
    printf("Structure initialized\n");

    // Create microphone configuration for tetrahedral array
    printf("Creating microphone configuration...\n");
    proc->mics = mics_construct_zero(4);  // 4 channels for tetrahedral array
    if (!proc->mics) {
        fprintf(stderr, "Failed to create microphone configuration\n");
        return -1;
    }

    // Set number of pairs for 4 microphones: C(4,2) = 6 pairs
    // Pairs: (0,1), (0,2), (0,3), (1,2), (1,3), (2,3)
    proc->mics->nPairs = 6;
    printf("Microphone configuration created with %d pairs\n", proc->mics->nPairs);

    // Set up tetrahedral microphone positions directly in the mu array
    printf("Setting microphone positions...\n");
    mic_position_t *positions = get_tetrahedral_positions();
    for (int i = 0; i < 4; i++) {
        proc->mics->mu[i * 3 + 0] = positions[i].x;  // x
        proc->mics->mu[i * 3 + 1] = positions[i].y;  // y
        proc->mics->mu[i * 3 + 2] = positions[i].z;  // z
    }
    printf("Microphone positions set\n");

    // Create samplerate configuration
    printf("Creating samplerate configuration...\n");
    proc->samplerate = samplerate_construct_zero();
    if (!proc->samplerate) {
        fprintf(stderr, "Failed to create samplerate configuration\n");
        mics_destroy(proc->mics);
        return -1;
    }
    proc->samplerate->mu = SAMPLE_RATE;  // Set sample rate after construction
    printf("Samplerate configuration created\n");

    // Create soundspeed configuration (speed of sound at room temperature)
    printf("Creating soundspeed configuration...\n");
    proc->soundspeed = soundspeed_construct_zero();
    if (!proc->soundspeed) {
        fprintf(stderr, "Failed to create soundspeed configuration\n");
        samplerate_destroy(proc->samplerate);
        mics_destroy(proc->mics);
        return -1;
    }
    proc->soundspeed->mu = 343.0f;  // Set speed of sound after construction
    printf("Soundspeed configuration created\n");

    // Create spatial filters configuration (1 filter for tetrahedral array)
    printf("Creating spatial filters configuration...\n");
    proc->spatialfilters = spatialfilters_construct_zero(1);
    if (!proc->spatialfilters) {
        fprintf(stderr, "Failed to create spatial filters configuration\n");
        soundspeed_destroy(proc->soundspeed);
        samplerate_destroy(proc->samplerate);
        mics_destroy(proc->mics);
        return -1;
    }
    printf("Spatial filters configuration created\n");

    // Create message configurations
    printf("Creating message configurations...\n");
    proc->msg_hops_cfg = msg_hops_cfg_construct();
    proc->msg_spectra_cfg = msg_spectra_cfg_construct();
    proc->msg_pots_cfg = msg_pots_cfg_construct();
    proc->msg_powers_cfg = msg_powers_cfg_construct();

    if (!proc->msg_hops_cfg || !proc->msg_spectra_cfg || !proc->msg_pots_cfg || !proc->msg_powers_cfg) {
        fprintf(stderr, "Failed to create message configurations\n");
        doa_processing_cleanup(proc);
        return -1;
    }

    // Configure message parameters
    proc->msg_hops_cfg->hopSize = FRAME_SIZE;
    proc->msg_hops_cfg->nChannels = CHANNELS;
    proc->msg_hops_cfg->fS = SAMPLE_RATE;

    // For STFT, halfFrameSize should be FRAME_SIZE/2 + 1 (typical FFT size)
    proc->msg_spectra_cfg->halfFrameSize = FRAME_SIZE / 2 + 1;
    proc->msg_spectra_cfg->nChannels = CHANNELS;
    proc->msg_spectra_cfg->fS = SAMPLE_RATE;

    // Configure pots (sound source detections)
    proc->msg_pots_cfg->nPots = 10;  // Maximum number of sound sources to detect
    proc->msg_pots_cfg->fS = SAMPLE_RATE;

    // Configure powers (noise estimation output)
    proc->msg_powers_cfg->halfFrameSize = FRAME_SIZE / 2 + 1;
    proc->msg_powers_cfg->nChannels = CHANNELS;
    proc->msg_powers_cfg->fS = SAMPLE_RATE;

    printf("Message configurations created and configured\n");

    // Create SSL configuration
    printf("Creating SSL configuration...\n");
    proc->mod_ssl_cfg = mod_ssl_cfg_construct();
    if (!proc->mod_ssl_cfg) {
        fprintf(stderr, "Failed to create SSL configuration\n");
        doa_processing_cleanup(proc);
        return -1;
    }

    // Configure SSL module for tetrahedral array
    printf("Configuring SSL module for tetrahedral array...\n");
    proc->mod_ssl_cfg->mics = proc->mics;
    proc->mod_ssl_cfg->samplerate = proc->samplerate;
    proc->mod_ssl_cfg->soundspeed = proc->soundspeed;
    proc->mod_ssl_cfg->spatialfilters = proc->spatialfilters;
    proc->mod_ssl_cfg->interpRate = 1;  // Minimal interpolation for debugging
    proc->mod_ssl_cfg->epsilon = 1e-6f; // Less aggressive regularization

    // Use minimal SSL configuration for debugging
    proc->mod_ssl_cfg->nLevels = 1;     // Single level for simplest processing

    // Allocate and set levels array - use minimal level
    proc->mod_ssl_cfg->levels = (unsigned int *)malloc(proc->mod_ssl_cfg->nLevels * sizeof(unsigned int));
    proc->mod_ssl_cfg->levels[0] = 1;   // Level 1 - minimal subdivision

    // Allocate and set deltas array - use fixed small deltas for speed
    proc->mod_ssl_cfg->deltas = (signed int *)malloc(proc->mod_ssl_cfg->nLevels * sizeof(signed int));
    proc->mod_ssl_cfg->deltas[0] = 0;   // Zero delta for maximum speed

    // Use ULTRA aggressive parameters to force detection
    proc->mod_ssl_cfg->nMatches = 1;        // Minimal matches required
    proc->mod_ssl_cfg->probMin = 0.001f;    // Almost no probability requirement
    proc->mod_ssl_cfg->nRefinedLevels = 1;  // One refinement level
    proc->mod_ssl_cfg->nThetas = 181;       // Number of theta angles
    proc->mod_ssl_cfg->gainMin = 0.001f;    // Almost no gain requirement

    printf("SSL configuration created and configured\n");

    // Create noise configuration
    printf("Creating noise estimation configuration...\n");
    proc->mod_noise_cfg = mod_noise_cfg_construct();
    if (!proc->mod_noise_cfg) {
        fprintf(stderr, "Failed to create noise configuration\n");
        doa_processing_cleanup(proc);
        return -1;
    }

    // Configure noise estimation with ReSpeaker values
    proc->mod_noise_cfg->bSize = 3;         // ReSpeaker value
    proc->mod_noise_cfg->alphaS = 0.1f;     // ReSpeaker value
    proc->mod_noise_cfg->L = 150;           // ReSpeaker value
    proc->mod_noise_cfg->delta = 3.0f;      // ReSpeaker value
    proc->mod_noise_cfg->alphaD = 0.1f;     // ReSpeaker value

    printf("Noise configuration created and configured\n");

    // Create STFT configuration
    printf("Creating STFT configuration...\n");
    proc->mod_stft_cfg = mod_stft_cfg_construct();
    if (!proc->mod_stft_cfg) {
        fprintf(stderr, "Failed to create STFT configuration\n");
        doa_processing_cleanup(proc);
        return -1;
    }
    printf("STFT configuration created\n");

    // Create message objects
    printf("Creating message objects...\n");
    proc->msg_hops = msg_hops_construct(proc->msg_hops_cfg);
    proc->msg_spectra = msg_spectra_construct(proc->msg_spectra_cfg);
    proc->msg_pots = msg_pots_construct(proc->msg_pots_cfg);
    proc->msg_powers = msg_powers_construct(proc->msg_powers_cfg);

    if (!proc->msg_hops || !proc->msg_spectra || !proc->msg_pots || !proc->msg_powers) {
        fprintf(stderr, "Failed to create message objects\n");
        doa_processing_cleanup(proc);
        return -1;
    }

    // Initialize hops buffer with zeros
    if (proc->msg_hops && proc->msg_hops->hops && proc->msg_hops->hops->array) {
        for (int ch = 0; ch < CHANNELS; ch++) {
            for (int s = 0; s < FRAME_SIZE; s++) {
                proc->msg_hops->hops->array[ch][s] = 0.0f;
            }
        }
        printf("Initialized hops buffer\n");
    }

    printf("Message objects created\n");

    // Create the modules
    printf("Creating STFT module...\n");
    proc->mod_stft = mod_stft_construct(
        proc->mod_stft_cfg,
        proc->msg_hops_cfg,
        proc->msg_spectra_cfg
    );

    if (!proc->mod_stft) {
        fprintf(stderr, "Failed to create STFT module\n");
        doa_processing_cleanup(proc);
        return -1;
    }

    // CRITICAL: Enable the STFT module (it's disabled by default!)
    mod_stft_enable(proc->mod_stft);
    printf("STFT module created and enabled successfully\n");

    // Create noise module
    printf("Creating noise estimation module...\n");
    proc->mod_noise = mod_noise_construct(
        proc->mod_noise_cfg,
        proc->msg_spectra_cfg,
        proc->msg_powers_cfg
    );

    if (!proc->mod_noise) {
        fprintf(stderr, "Failed to create noise module\n");
        doa_processing_cleanup(proc);
        return -1;
    }
    printf("Noise module created successfully\n");

    printf("Creating SSL module...\n");
    proc->mod_ssl = mod_ssl_construct(
        proc->mod_ssl_cfg,
        proc->msg_spectra_cfg,
        proc->msg_pots_cfg
    );

    if (!proc->mod_ssl) {
        fprintf(stderr, "Failed to create SSL module\n");
        doa_processing_cleanup(proc);
        return -1;
    }
    printf("SSL module created successfully\n");
    printf("ODAS modules created\n");

    // Create connectors for proper ODAS data flow
    printf("Creating connectors...\n");

    // Spectra connector: routes STFT output to noise and SSL modules
    proc->con_spectra = con_spectra_construct(2, proc->msg_spectra_cfg);
    if (!proc->con_spectra) {
        fprintf(stderr, "Failed to create spectra connector\n");
        doa_processing_cleanup(proc);
        return -1;
    }

    // Powers connector: routes noise output (currently just 1 output needed)
    proc->con_powers = con_powers_construct(1, proc->msg_powers_cfg);
    if (!proc->con_powers) {
        fprintf(stderr, "Failed to create powers connector\n");
        doa_processing_cleanup(proc);
        return -1;
    }

    // Pots connector: routes SSL output
    proc->con_pots = con_pots_construct(1, proc->msg_pots_cfg);
    if (!proc->con_pots) {
        fprintf(stderr, "Failed to create pots connector\n");
        doa_processing_cleanup(proc);
        return -1;
    }
    printf("Connectors created\n");

    // Connect the modules using proper ODAS connector pattern
    printf("Connecting modules...\n");

    // STFT connects to spectra connector input
    mod_stft_connect(proc->mod_stft, proc->msg_hops, proc->con_spectra->in);

    // Noise module connects to spectra connector output[0] and powers connector input
    mod_noise_connect(proc->mod_noise, proc->con_spectra->outs[0], proc->con_powers->in);

    // Enable the noise module
    mod_noise_enable(proc->mod_noise);
    printf("Noise module enabled\n");

    // SSL module connects to spectra connector output[1] and pots connector input (like ODAS demo)
    mod_ssl_connect(proc->mod_ssl, proc->con_spectra->outs[1], proc->con_pots->in);

    // CRITICAL: Enable the SSL module (it's disabled by default!)
    mod_ssl_enable(proc->mod_ssl);
    printf("SSL module enabled\n");

    // Connect pots connector output to message object
    proc->con_pots->outs[0] = proc->msg_pots;
    printf("Pots connector output connected to message object\n");

    printf("Modules connected with proper connector pattern\n");

    printf("Minimal DOA processing pipeline initialized successfully\n");
    printf("Using tetrahedral array with %d microphones\n", CHANNELS);
    printf("Sample rate: %d Hz, Frame size: %d samples\n", SAMPLE_RATE, FRAME_SIZE);

    proc->initialized = 1;
    printf("DOA processing initialization complete\n");
    return 0;
}

void doa_processing_cleanup(doa_processing_t *proc) {
    if (!proc || !proc->initialized) return;

    // Cleanup modules
    if (proc->mod_ssl) {
        mod_ssl_destroy(proc->mod_ssl);
        proc->mod_ssl = NULL;
    }

    if (proc->mod_stft) {
        mod_stft_destroy(proc->mod_stft);
        proc->mod_stft = NULL;
    }

    if (proc->mod_noise) {
        mod_noise_destroy(proc->mod_noise);
        proc->mod_noise = NULL;
    }

    // Cleanup connectors
    if (proc->con_spectra) {
        con_spectra_destroy(proc->con_spectra);
        proc->con_spectra = NULL;
    }

    if (proc->con_powers) {
        con_powers_destroy(proc->con_powers);
        proc->con_powers = NULL;
    }

    if (proc->con_pots) {
        con_pots_destroy(proc->con_pots);
        proc->con_pots = NULL;
    }

    // Cleanup message objects
    if (proc->msg_pots) {
        msg_pots_destroy(proc->msg_pots);
        proc->msg_pots = NULL;
    }

    if (proc->msg_spectra) {
        msg_spectra_destroy(proc->msg_spectra);
        proc->msg_spectra = NULL;
    }

    if (proc->msg_hops) {
        msg_hops_destroy(proc->msg_hops);
        proc->msg_hops = NULL;
    }

    if (proc->msg_powers) {
        msg_powers_destroy(proc->msg_powers);
        proc->msg_powers = NULL;
    }

    // Cleanup configurations
    if (proc->mod_ssl_cfg) {
        // Free allocated arrays before destroying the config
        if (proc->mod_ssl_cfg->levels) {
            free(proc->mod_ssl_cfg->levels);
        }
        if (proc->mod_ssl_cfg->deltas) {
            free(proc->mod_ssl_cfg->deltas);
        }
        mod_ssl_cfg_destroy(proc->mod_ssl_cfg);
        proc->mod_ssl_cfg = NULL;
    }

    if (proc->mod_stft_cfg) {
        mod_stft_cfg_destroy(proc->mod_stft_cfg);
        proc->mod_stft_cfg = NULL;
    }

    if (proc->mod_noise_cfg) {
        mod_noise_cfg_destroy(proc->mod_noise_cfg);
        proc->mod_noise_cfg = NULL;
    }

    if (proc->msg_pots_cfg) {
        msg_pots_cfg_destroy(proc->msg_pots_cfg);
        proc->msg_pots_cfg = NULL;
    }

    if (proc->msg_spectra_cfg) {
        msg_spectra_cfg_destroy(proc->msg_spectra_cfg);
        proc->msg_spectra_cfg = NULL;
    }

    if (proc->msg_hops_cfg) {
        msg_hops_cfg_destroy(proc->msg_hops_cfg);
        proc->msg_hops_cfg = NULL;
    }

    if (proc->msg_powers_cfg) {
        msg_powers_cfg_destroy(proc->msg_powers_cfg);
        proc->msg_powers_cfg = NULL;
    }

    // Cleanup basic configurations
    if (proc->spatialfilters) {
        spatialfilters_destroy(proc->spatialfilters);
        proc->spatialfilters = NULL;
    }

    if (proc->soundspeed) {
        soundspeed_destroy(proc->soundspeed);
        proc->soundspeed = NULL;
    }

    if (proc->samplerate) {
        samplerate_destroy(proc->samplerate);
        proc->samplerate = NULL;
    }

    if (proc->mics) {
        mics_destroy(proc->mics);
        proc->mics = NULL;
    }

    proc->initialized = 0;
    printf("DOA processing cleaned up\n");
}

// Process audio frame with ODAS
int process_audio_frame(doa_processing_t *proc, float *audio_data, int frames) {
    static int frame_debug_count = 0;
    frame_debug_count++;
    if (frame_debug_count % 100 == 0) {
        printf("FRAME_DEBUG[%d]: process_audio_frame called\n", frame_debug_count);
    }

    if (!proc || !proc->initialized || !audio_data || frames <= 0) {
        fprintf(stderr, "Invalid parameters: proc=%p, initialized=%d, audio_data=%p, frames=%d\n",
                proc, proc ? proc->initialized : 0, audio_data, frames);
        return -1;
    }

    static int frame_count = 0;
    frame_count++;

    // Monitor audio levels every second
    static float running_max = 0.0f;
    static int frames_since_display = 0;

    for (int i = 0; i < frames * CHANNELS; i++) {
        float abs_val = fabsf(audio_data[i]);
        if (abs_val > running_max) running_max = abs_val;
    }

    frames_since_display++;
    if (frames_since_display >= 86) { // ~1 second at 44.1kHz/512 frames
        printf("Audio Level: %.3f\r", running_max);
        fflush(stdout);
        running_max = 0.0f;
        frames_since_display = 0;
    }

    // Verify msg_hops buffer
    if (!proc->msg_hops || !proc->msg_hops->hops || !proc->msg_hops->hops->array) {
        fprintf(stderr, "msg_hops buffer not properly initialized\n");
        return -1;
    }

    // Update timestamp to indicate new data
    proc->msg_hops->timeStamp = frame_count;
    proc->msg_hops->fS = SAMPLE_RATE;

    // Copy audio data to the msg_hops buffer
    // The audio_data should be interleaved: [ch0_sample0, ch1_sample0, ch2_sample0, ch3_sample0, ch0_sample1, ...]
    for (int sample = 0; sample < frames; sample++) {
        for (int channel = 0; channel < CHANNELS; channel++) {
            int audio_index = sample * CHANNELS + channel;
            int hop_index = channel * FRAME_SIZE + sample;

            // Copy to the hops buffer (transposed format: channels x samples)
            proc->msg_hops->hops->array[channel][sample] = audio_data[audio_index];
        }
    }

    // Debug: Check input data to STFT
    if (frame_debug_count % 100 == 0) {
        printf("STFT_INPUT_DEBUG[%d]: First 4 samples from each channel:\n", frame_debug_count);
        for (int ch = 0; ch < CHANNELS; ch++) {
            printf("  Ch%d: [%.6f, %.6f, %.6f, %.6f]\n", ch,
                   proc->msg_hops->hops->array[ch][0],
                   proc->msg_hops->hops->array[ch][1],
                   proc->msg_hops->hops->array[ch][2],
                   proc->msg_hops->hops->array[ch][3]);
        }
    }

    // Process through STFT module
    int stft_result = mod_stft_process(proc->mod_stft);
    if (stft_result != 0) {
        fprintf(stderr, "STFT processing failed with result: %d\n", stft_result);
        return -1;
    }

    // Debug: Check STFT output
    if (frame_debug_count % 100 == 0) {
        printf("STFT_OUTPUT_DEBUG[%d]: Checking spectra connector input...\n", frame_debug_count);
        if (proc->con_spectra && proc->con_spectra->in && proc->con_spectra->in->freqs) {
            printf("  STFT output nSignals=%d, halfFrameSize=%d\n",
                   proc->con_spectra->in->freqs->nSignals,
                   proc->con_spectra->in->freqs->halfFrameSize);
            printf("  First freq values: [%.6f, %.6f, %.6f, %.6f]\n",
                   proc->con_spectra->in->freqs->array[0][1],  // Ch0, bin 1
                   proc->con_spectra->in->freqs->array[1][1],  // Ch1, bin 1
                   proc->con_spectra->in->freqs->array[2][1],  // Ch2, bin 1
                   proc->con_spectra->in->freqs->array[3][1]); // Ch3, bin 1
        } else {
            printf("  ERROR: STFT output is NULL or invalid\n");
        }
    }

    // Process spectra connector - routes STFT output to noise and SSL inputs
    int spectra_result = con_spectra_process(proc->con_spectra);
    if (spectra_result != 0) {
        fprintf(stderr, "Spectra connector processing failed\n");
        return -1;
    }

    // Process through noise estimation module (uses con_spectra->outs[0])
    int noise_result = mod_noise_process(proc->mod_noise);
    if (noise_result != 0) {
        fprintf(stderr, "Noise processing failed with result: %d\n", noise_result);
        return -1;
    }

    // Process powers connector - routes noise output
    int powers_result = con_powers_process(proc->con_powers);
    if (powers_result != 0) {
        fprintf(stderr, "Powers connector processing failed\n");
        return -1;
    }

    // Process through SSL module (uses con_spectra->outs[1] and has access to noise data)
    static int ssl_call_count = 0;
    ssl_call_count++;
    if (ssl_call_count % 100 == 0) {
        printf("APP_DEBUG[%d]: About to call mod_ssl_process, proc->mod_ssl=%p\n", ssl_call_count, proc->mod_ssl);
    }

    int ssl_result = mod_ssl_process(proc->mod_ssl);
    if (ssl_result != 0) {
        fprintf(stderr, "SSL processing failed\n");
        return -1;
    }

    if (ssl_call_count % 100 == 0) {
        printf("APP_DEBUG[%d]: mod_ssl_process returned %d\n", ssl_call_count, ssl_result);
    }

    // Process pots connector - routes SSL output to message object
    int pots_result = con_pots_process(proc->con_pots);
    if (pots_result != 0) {
        fprintf(stderr, "Pots connector processing failed\n");
        return -1;
    }

    // Check SSL output and let ODAS set nPots automatically
    if (proc->msg_pots && proc->msg_pots->pots) {
        float max_energy = 0.0f;
        static int debug_counter = 0;
        debug_counter++;

        // Check what ODAS actually detected (it should set nPots automatically)
        unsigned int actual_pots = proc->msg_pots->pots->nPots;

        // Debug: Show the actual SSL output structure
        if (debug_counter % 430 == 0) { // Every ~5 seconds
            printf("SSL detected %d pots. Raw output:\\n", actual_pots);
            for (int i = 0; i < 10 && i < 40; i++) { // Show first 10 pot entries
                float x = proc->msg_pots->pots->array[i * 4 + 0];
                float y = proc->msg_pots->pots->array[i * 4 + 1];
                float z = proc->msg_pots->pots->array[i * 4 + 2];
                float energy = proc->msg_pots->pots->array[i * 4 + 3];
                printf("  Pot[%d]: x=%.6f, y=%.6f, z=%.6f, E=%.6f\\n", i, x, y, z, energy);

                if (fabsf(energy) > max_energy) max_energy = fabsf(energy);
            }
        }

        // Debug max energy found
        if (debug_counter % 86 == 0) {
            printf("ODAS detected %d sources, Max energy: %.6f\\n", actual_pots, max_energy);
        }
    }

    // Display DOA results and diagnostics
    static int display_counter = 0;
    display_counter++;

    if (display_counter >= 86) { // Every ~1 second
        if (proc->msg_pots && proc->msg_pots->pots) {
            printf("SSL Status: nPots=%d, timeStamp=%llu\n",
                   proc->msg_pots->pots->nPots, proc->msg_pots->timeStamp);

            if (proc->msg_pots->pots->nPots > 0) {
                printf("Detected %d potential sources:\n", proc->msg_pots->pots->nPots);

                // Show first few values from the pots array
                for (unsigned int i = 0; i < proc->msg_pots->pots->nPots && i < 5; i++) {
                    printf("  Pot %d: %.6f\n", i, proc->msg_pots->pots->array[i]);
                }
            } else {
                // Check if we have any non-zero values even if nPots is 0
                // SSL might be producing output but below threshold
                printf("No sources detected. SSL output buffer status unknown.\n");
            }
        } else {
            printf("msg_pots or pots buffer is NULL\n");
        }
        display_counter = 0;
    }

    // Extract direction of arrival results
    if (proc->msg_pots->pots && proc->msg_pots->pots->nPots > 0) {
        // Find the pot with maximum value (most likely sound source)
        float max_energy = 0.0f;
        int max_pot_index = -1;

        // Correctly check the energy values (4th component of each pot)
        for (int i = 0; i < proc->msg_pots->pots->nPots; i++) {
            float energy = proc->msg_pots->pots->array[i * 4 + 3]; // Energy is 4th component
            if (energy > max_energy) {
                max_energy = energy;
                max_pot_index = i;
            }
        }

        if (max_pot_index >= 0 && max_energy > 0.001f) {  // Very low threshold for any detection
            if (frame_count % 50 == 0) {  // Print every 50 frames to avoid spam
                printf("Frame %d: Detected sound source at pot %d with energy %.6f\n",
                       frame_count, max_pot_index, max_energy);
            }
        } else {
            if (frame_count % 50 == 0) {
                printf("Frame %d: No energy detected (max=%.6f)\n", frame_count, max_energy);
            }
        }
    }

    return 0;
}

// Start DOA processing
int doa_processing_start(doa_processing_t *proc) {
    if (!proc || !proc->initialized) {
        return -1;
    }

    printf("Starting DOA processing pipeline...\n");
    return 0;
}

// Stop DOA processing
int doa_processing_stop(doa_processing_t *proc) {
    if (!proc || !proc->initialized) {
        return -1;
    }

    printf("Stopping DOA processing pipeline...\n");
    return 0;
}

// Function to get tetrahedral microphone positions
mic_position_t* get_tetrahedral_positions(void) {
    static mic_position_t positions[4];

    // Tetrahedral geometry with 25mm radius (matching mechanical design)
    // These positions match the vertices of a regular tetrahedron

    // Position 0: [0.025, 0.025, 0.025]
    positions[0].x = ARRAY_RADIUS;
    positions[0].y = ARRAY_RADIUS;
    positions[0].z = ARRAY_RADIUS;

    // Position 1: [0.025, -0.025, -0.025]
    positions[1].x = ARRAY_RADIUS;
    positions[1].y = -ARRAY_RADIUS;
    positions[1].z = -ARRAY_RADIUS;

    // Position 2: [-0.025, 0.025, -0.025]
    positions[2].x = -ARRAY_RADIUS;
    positions[2].y = ARRAY_RADIUS;
    positions[2].z = -ARRAY_RADIUS;

    // Position 3: [-0.025, -0.025, 0.025]
    positions[3].x = -ARRAY_RADIUS;
    positions[3].y = -ARRAY_RADIUS;
    positions[3].z = ARRAY_RADIUS;

    return positions;
}

// Function to print array geometry
void print_array_geometry(void) {
    mic_position_t *positions = get_tetrahedral_positions();

    printf("=== Tetrahedral Microphone Array Geometry ===\n");
    printf("Array radius: %.3f m (%.1f mm)\n", ARRAY_RADIUS, ARRAY_RADIUS * 1000);
    printf("\n");
    printf("Microphone positions:\n");

    for (int i = 0; i < 4; i++) {
        printf("  Mic %d: [%7.3f, %7.3f, %7.3f] m\n",
               i, positions[i].x, positions[i].y, positions[i].z);
    }

    printf("\n");
    printf("Edge length: %.3f m (%.1f mm)\n",
           ARRAY_RADIUS * 1.63299, ARRAY_RADIUS * 1.63299 * 1000);
    printf("\n");
}