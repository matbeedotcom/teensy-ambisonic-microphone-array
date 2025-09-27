#include <stdio.h>
#include <math.h>

#include "tetrahedral_mic_array.h"

// Calculate distance between two microphones
float calculate_mic_distance(const mic_position_t *pos1, const mic_position_t *pos2) {
    float dx = pos1->x - pos2->x;
    float dy = pos1->y - pos2->y;
    float dz = pos1->z - pos2->z;
    return sqrtf(dx*dx + dy*dy + dz*dz);
}

// Calculate maximum time delay between microphones (for DOA processing)
float calculate_max_time_delay(float speed_of_sound) {
    mic_position_t *positions = get_tetrahedral_positions();
    float max_distance = 0.0f;

    // Find maximum distance between any two microphones
    for (int i = 0; i < 4; i++) {
        for (int j = i + 1; j < 4; j++) {
            float distance = calculate_mic_distance(&positions[i], &positions[j]);
            if (distance > max_distance) {
                max_distance = distance;
            }
        }
    }

    return max_distance / speed_of_sound;
}

// Calculate maximum lag in samples for given sample rate
int calculate_max_lag_samples(int sample_rate, float speed_of_sound) {
    float max_delay = calculate_max_time_delay(speed_of_sound);
    return (int)ceilf(max_delay * sample_rate);
}

// Validate array geometry (check if it's a proper tetrahedron)
int validate_tetrahedral_geometry(void) {
    mic_position_t *positions = get_tetrahedral_positions();

    // Check if all edge lengths are approximately equal
    float edge_lengths[6];
    int edge_index = 0;

    for (int i = 0; i < 4; i++) {
        for (int j = i + 1; j < 4; j++) {
            edge_lengths[edge_index++] = calculate_mic_distance(&positions[i], &positions[j]);
        }
    }

    // Calculate average edge length
    float avg_length = 0.0f;
    for (int i = 0; i < 6; i++) {
        avg_length += edge_lengths[i];
    }
    avg_length /= 6.0f;

    // Check if all edges are within 1% of average
    for (int i = 0; i < 6; i++) {
        float deviation = fabsf(edge_lengths[i] - avg_length) / avg_length;
        if (deviation > 0.01f) {
            printf("Warning: Edge length deviation %.2f%% exceeds 1%%\n", deviation * 100);
            return -1;
        }
    }

    return 0;
}

// Print detailed array information
void print_array_info(void) {
    mic_position_t *positions = get_tetrahedral_positions();

    printf("=== Detailed Array Information ===\n");

    // Print microphone positions
    for (int i = 0; i < 4; i++) {
        printf("Mic %d: [%7.3f, %7.3f, %7.3f] m",
               i, positions[i].x, positions[i].y, positions[i].z);
        printf(" (radius: %.3f m)\n",
               sqrtf(positions[i].x*positions[i].x +
                     positions[i].y*positions[i].y +
                     positions[i].z*positions[i].z));
    }

    printf("\nEdge lengths:\n");
    int edge_index = 0;
    for (int i = 0; i < 4; i++) {
        for (int j = i + 1; j < 4; j++) {
            float distance = calculate_mic_distance(&positions[i], &positions[j]);
            printf("  Mic %d - Mic %d: %.3f m\n", i, j, distance);
        }
    }

    // Calculate DOA parameters
    float speed_of_sound = 343.0f; // m/s at 20°C
    float max_delay = calculate_max_time_delay(speed_of_sound);
    int max_lag = calculate_max_lag_samples(SAMPLE_RATE, speed_of_sound);

    printf("\nDOA Processing Parameters:\n");
    printf("  Speed of sound: %.1f m/s\n", speed_of_sound);
    printf("  Maximum time delay: %.6f s\n", max_delay);
    printf("  Maximum lag (samples): %d\n", max_lag);
    printf("  Angular resolution: ~5 degrees\n");

    // Validate geometry
    printf("\nGeometry validation: ");
    if (validate_tetrahedral_geometry() == 0) {
        printf("PASSED\n");
    } else {
        printf("FAILED\n");
    }

    printf("\n");
}