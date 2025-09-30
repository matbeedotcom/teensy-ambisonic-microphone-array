#include "odas_wrapper.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

// Include odaslive headers
#include "configs.h"
#include "objects.h"
#include "threads.h"

odas_processor_t* odas_processor_create(const char *config_file) {
    if (!config_file) {
        fprintf(stderr, "Config file path cannot be NULL\n");
        return NULL;
    }

    odas_processor_t *processor = (odas_processor_t*)calloc(1, sizeof(odas_processor_t));
    if (!processor) {
        fprintf(stderr, "Failed to allocate processor\n");
        return NULL;
    }

    processor->config_file = strdup(config_file);
    if (!processor->config_file) {
        fprintf(stderr, "Failed to duplicate config file path\n");
        free(processor);
        return NULL;
    }

    // Load configurations
    processor->cfgs = configs_construct(config_file);
    if (!processor->cfgs) {
        fprintf(stderr, "Failed to construct configs from file: %s\n", config_file);
        free(processor->config_file);
        free(processor);
        return NULL;
    }

    // Construct async objects
    processor->aobjs = aobjects_construct(processor->cfgs);
    if (!processor->aobjs) {
        fprintf(stderr, "Failed to construct aobjects\n");
        configs_destroy(processor->cfgs);
        free(processor->config_file);
        free(processor);
        return NULL;
    }

    processor->initialized = 1;
    processor->running = 0;

    return processor;
}

int odas_processor_start(odas_processor_t *processor) {
    if (!processor || !processor->initialized) {
        fprintf(stderr, "Processor not initialized\n");
        return -1;
    }

    if (processor->running) {
        fprintf(stderr, "Processor already running\n");
        return -1;
    }

    // Start processing threads
    threads_multiple_start(processor->aobjs);
    processor->running = 1;

    return 0;
}

int odas_processor_stop(odas_processor_t *processor) {
    if (!processor || !processor->initialized) {
        fprintf(stderr, "Processor not initialized\n");
        return -1;
    }

    if (!processor->running) {
        fprintf(stderr, "Processor not running\n");
        return -1;
    }

    // Stop processing threads
    threads_multiple_stop(processor->aobjs);
    threads_multiple_join(processor->aobjs);
    processor->running = 0;

    return 0;
}

int odas_processor_is_running(odas_processor_t *processor) {
    if (!processor) {
        return 0;
    }
    return processor->running;
}

void odas_processor_destroy(odas_processor_t *processor) {
    if (!processor) {
        return;
    }

    // Stop if running
    if (processor->running) {
        odas_processor_stop(processor);
    }

    // Destroy objects
    if (processor->aobjs) {
        aobjects_destroy(processor->aobjs);
        processor->aobjs = NULL;
    }

    // Destroy configs
    if (processor->cfgs) {
        configs_destroy(processor->cfgs);
        processor->cfgs = NULL;
    }

    // Free config file path
    if (processor->config_file) {
        free(processor->config_file);
        processor->config_file = NULL;
    }

    processor->initialized = 0;
    free(processor);
}

// Note: Callback registration would require modifying the ODAS library
// to expose callback hooks. For now, these functions return not implemented.
int odas_processor_set_pots_callback(odas_processor_t *processor, odas_pots_callback_t callback, void *user_data) {
    // TODO: Implement callback registration when ODAS library is extended
    fprintf(stderr, "Callback registration not yet implemented - requires ODAS library modification\n");
    return -1;
}

int odas_processor_set_tracks_callback(odas_processor_t *processor, odas_tracks_callback_t callback, void *user_data) {
    // TODO: Implement callback registration when ODAS library is extended
    fprintf(stderr, "Callback registration not yet implemented - requires ODAS library modification\n");
    return -1;
}