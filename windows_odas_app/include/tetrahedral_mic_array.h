#ifndef TETRAHEDRAL_MIC_ARRAY_H
#define TETRAHEDRAL_MIC_ARRAY_H

// Audio configuration
#define SAMPLE_RATE 44100
#define CHANNELS 4
#define FRAME_SIZE 512
#define BUFFER_SIZE 4096

// Array geometry constants (matching mechanical design)
#define ARRAY_RADIUS 0.025f  // 25mm radius

// Tetrahedral microphone positions (4 channels)
typedef struct {
    float x;
    float y;
    float z;
} mic_position_t;

// Forward declarations for ODAS types (we'll include headers in implementation)
typedef struct mics_obj mics_obj;
typedef struct samplerate_obj samplerate_obj;
typedef struct soundspeed_obj soundspeed_obj;
typedef struct spatialfilters_obj spatialfilters_obj;

typedef struct msg_hops_cfg msg_hops_cfg;
typedef struct msg_spectra_cfg msg_spectra_cfg;
typedef struct msg_pots_cfg msg_pots_cfg;
typedef struct msg_powers_cfg msg_powers_cfg;

typedef struct mod_ssl_cfg mod_ssl_cfg;
typedef struct mod_stft_cfg mod_stft_cfg;
typedef struct mod_noise_cfg mod_noise_cfg;

typedef struct msg_hops_obj msg_hops_obj;
typedef struct msg_spectra_obj msg_spectra_obj;
typedef struct msg_pots_obj msg_pots_obj;
typedef struct msg_powers_obj msg_powers_obj;

typedef struct mod_ssl_obj mod_ssl_obj;
typedef struct mod_stft_obj mod_stft_obj;
typedef struct mod_noise_obj mod_noise_obj;

typedef struct con_spectra_obj con_spectra_obj;
typedef struct con_powers_obj con_powers_obj;

// DOA processing structure
typedef struct doa_processing_t {
    // Basic configurations
    mics_obj *mics;
    samplerate_obj *samplerate;
    soundspeed_obj *soundspeed;
    spatialfilters_obj *spatialfilters;

    // Message configurations
    msg_hops_cfg *msg_hops_cfg;
    msg_spectra_cfg *msg_spectra_cfg;
    msg_pots_cfg *msg_pots_cfg;
    msg_powers_cfg *msg_powers_cfg;

    // Module configurations
    mod_ssl_cfg *mod_ssl_cfg;
    mod_stft_cfg *mod_stft_cfg;
    mod_noise_cfg *mod_noise_cfg;

    // Message objects
    msg_hops_obj *msg_hops;
    msg_spectra_obj *msg_spectra;
    msg_pots_obj *msg_pots;
    msg_powers_obj *msg_powers;

    // Modules
    mod_ssl_obj *mod_ssl;
    mod_stft_obj *mod_stft;
    mod_noise_obj *mod_noise;

    // Connectors
    con_spectra_obj *con_spectra;
    con_powers_obj *con_powers;

    // Processing state
    int initialized;
} doa_processing_t;

// Main application structure
typedef struct {
    // DOA processing
    doa_processing_t *doa_proc;

    // Audio capture
    void *audio_device;

    // Processing state
    int running;

    // Configuration
    char *config_file;
    char *wav_file;

} tetrahedral_app_t;

// Function prototypes
int tetrahedral_app_init(tetrahedral_app_t *app, const char *config_file, const char *wav_file);
int tetrahedral_app_run(tetrahedral_app_t *app);
void tetrahedral_app_cleanup(tetrahedral_app_t *app);

// Audio capture functions
int audio_capture_init(void **device, int channels, int sample_rate);
int audio_capture_init_wav(void **device, const char *wav_file, int channels, int sample_rate);
int audio_capture_read(void *device, float *buffer, int frames);
void audio_capture_cleanup(void *device);

// DOA processing functions
int doa_processing_init(doa_processing_t *proc, const char *config_file);
void doa_processing_cleanup(doa_processing_t *proc);
int doa_processing_start(doa_processing_t *proc);
int doa_processing_stop(doa_processing_t *proc);
int process_audio_frame(doa_processing_t *proc, float *audio_data, int frames);

// Array geometry functions
mic_position_t* get_tetrahedral_positions(void);

#endif // TETRAHEDRAL_MIC_ARRAY_H