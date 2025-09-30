#ifndef ODAS_WRAPPER_H
#define ODAS_WRAPPER_H

#include <odas/odas.h>

// Forward declarations for odaslive structures
typedef struct configs configs;
typedef struct objects objects;
typedef struct aobjects aobjects;

// Wrapper structure to hold ODAS processing state
typedef struct {
    configs *cfgs;
    aobjects *aobjs;
    int running;
    int initialized;
    char *config_file;
} odas_processor_t;

// Initialize ODAS processor from config file
odas_processor_t* odas_processor_create(const char *config_file);

// Start ODAS processing threads
int odas_processor_start(odas_processor_t *processor);

// Stop ODAS processing threads
int odas_processor_stop(odas_processor_t *processor);

// Check if processor is running
int odas_processor_is_running(odas_processor_t *processor);

// Cleanup and destroy processor
void odas_processor_destroy(odas_processor_t *processor);

// Callback registration for results
typedef void (*odas_pots_callback_t)(float *x, float *y, float *z, int count, void *user_data);
typedef void (*odas_tracks_callback_t)(int track_id, float x, float y, float z, void *user_data);

// Register callbacks for receiving results
int odas_processor_set_pots_callback(odas_processor_t *processor, odas_pots_callback_t callback, void *user_data);
int odas_processor_set_tracks_callback(odas_processor_t *processor, odas_tracks_callback_t callback, void *user_data);

#endif // ODAS_WRAPPER_H