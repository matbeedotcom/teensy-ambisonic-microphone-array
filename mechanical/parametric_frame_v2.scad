/**
 * Parametric Spherical Microphone Array Frame V2
 * MOUNT-FIRST ARCHITECTURE - Frame grows organically from microphone mounts
 *
 * Key differences from V1:
 * - Microphone mounts are created FIRST
 * - Frame structure uses hull() between nearest neighbor mounts
 * - Creates organic, minimal frame connections
 * - No separate frame thickness - structure emerges from hulled mounts
 *
 * MICROPHONE DISTRIBUTIONS:
 * - 4 mics  → Tetrahedron (1st order ambisonics)
 * - 6 mics  → Octahedron
 * - 8 mics  → Cube (2nd order ambisonics) ← DEFAULT
 * - 12 mics → Icosahedron (3rd order capable)
 * - 20 mics → Dodecahedron (higher order)
 * - Other  → Fibonacci sphere
 *
 * HOW TO USE:
 * 1. Set mic_count to desired number of channels
 * 2. Set vertex_distance for array radius
 * 3. Adjust neighbor_connection_ratio to control frame density
 * 4. Render and export STL files
 */

// ========================================
// CONFIGURABLE PARAMETERS
// ========================================

// Number of microphones (determines geometry)
mic_count = 8;  // Try 4, 6, 8, 12, 20, or any other number

// Array radius configuration
vertex_distance = 61;  // Distance from center to each microphone (mm)
                       // Larger = better DOA, smaller = more compact

// Frame generation parameters
neighbor_connection_ratio = 1.5;  // Connect to neighbors within this ratio of minimum distance
                                   // Lower = sparser frame, higher = denser frame
                                   // Typical: 1.3-1.8

// Microphone mount parameters
mic_board_diameter = 15;    // Microphone breakout board diameter
mount_thickness = 3;        // Mounting pad thickness
mount_offset = -10.0;       // Distance from vertex to mounting pad (mm)
post_offset = 1.0;          // Distance from PCB edge to mounting posts (mm)
clearance = 0.2;            // 3D printing clearance

// Frame structure parameters
frame_arm_diameter = 2.5;   // Diameter of frame arms connecting mounts
hull_segments = 8;          // Number of segments for frame hull connections
wire_diameter = 8;          // Wire bundle diameter

// ICM20948 IMU parameters
icm_board_length = 25.4;
icm_board_width = 15.24;
icm_board_thickness = 1.6;
icm_hole_inset = 2.0;
icm_hole_diameter = 2.5;
icm_standoff_height = 3;

// ========================================
// PLATONIC SOLID VERTEX DEFINITIONS
// ========================================

// Tetrahedron (4 vertices)
function tetrahedron_vertices() = [
    [ 1,  1,  1],
    [ 1, -1, -1],
    [-1,  1, -1],
    [-1, -1,  1]
];

// Octahedron (6 vertices)
function octahedron_vertices() = [
    [ 1,  0,  0],
    [-1,  0,  0],
    [ 0,  1,  0],
    [ 0, -1,  0],
    [ 0,  0,  1],
    [ 0,  0, -1]
];

// Cube (8 vertices)
function cube_vertices() = [
    [ 1,  1,  1],
    [ 1,  1, -1],
    [ 1, -1,  1],
    [ 1, -1, -1],
    [-1,  1,  1],
    [-1,  1, -1],
    [-1, -1,  1],
    [-1, -1, -1]
];

// Icosahedron (12 vertices)
function icosahedron_vertices() =
    let(phi = (1 + sqrt(5)) / 2)
    [
        [ 0,  1,  phi],
        [ 0,  1, -phi],
        [ 0, -1,  phi],
        [ 0, -1, -phi],
        [ 1,  phi,  0],
        [ 1, -phi,  0],
        [-1,  phi,  0],
        [-1, -phi,  0],
        [ phi,  0,  1],
        [ phi,  0, -1],
        [-phi,  0,  1],
        [-phi,  0, -1]
    ];

// Dodecahedron (20 vertices)
function dodecahedron_vertices() =
    let(phi = (1 + sqrt(5)) / 2)
    concat(
        cube_vertices(),
        [
            [ 0,  phi,  1/phi],
            [ 0,  phi, -1/phi],
            [ 0, -phi,  1/phi],
            [ 0, -phi, -1/phi],
            [ 1/phi,  0,  phi],
            [ 1/phi,  0, -phi],
            [-1/phi,  0,  phi],
            [-1/phi,  0, -phi],
            [ phi,  1/phi,  0],
            [ phi, -1/phi,  0],
            [-phi,  1/phi,  0],
            [-phi, -1/phi,  0]
        ]
    );

// Spherical even distribution using golden angle
function spherical_even_distribution(n) =
    n == 1 ? [[0, 0, 1]] :
    n == 2 ? [[0, 0, 1], [0, 0, -1]] :
    let(
        phi = (1 + sqrt(5)) / 2,
        indices = [0:n-1]
    )
    [
        for (i = indices)
            let(
                elevation = asin(1 - 2 * (i + 0.5) / n),
                azimuth = (i * 360 / phi) % 360,
                x = cos(elevation) * cos(azimuth),
                y = cos(elevation) * sin(azimuth),
                z = sin(elevation)
            )
            [x, y, z]
    ];

// ========================================
// VERTEX DISTRIBUTION SELECTOR
// ========================================

use_platonic_solids = true;  // Use exact platonic solids when available

function get_raw_vertices(count) =
    use_platonic_solids ? (
        count == 4  ? tetrahedron_vertices() :
        count == 6  ? octahedron_vertices() :
        count == 8  ? cube_vertices() :
        count == 12 ? icosahedron_vertices() :
        count == 20 ? dodecahedron_vertices() :
        spherical_even_distribution(count)
    ) :
    spherical_even_distribution(count);

// Normalize and scale vertices to desired radius
function normalize_vertices(verts, radius) = [
    for (v = verts)
        let(len = norm(v))
        v * (radius / len)
];

// Get final vertex positions
vertices = normalize_vertices(get_raw_vertices(mic_count), vertex_distance);

// Log calculated positions
echo(str("=== MICROPHONE POSITIONS ==="));
echo(str("Using ", use_platonic_solids ? "Platonic solid" : "Algorithmic", " distribution for ", mic_count, " microphones"));
for (i = [0:len(vertices)-1]) {
    v = vertices[i];
    r = norm(v);
    azimuth = atan2(v.y, v.x);
    elevation = asin(v.z / r);
    echo(str("Mic ", i, ": [", round(v.x*10)/10, ", ", round(v.y*10)/10, ", ", round(v.z*10)/10, "] mm",
             " (r=", round(r*10)/10, "mm, az=", round(azimuth), "°, el=", round(elevation), "°)"));
}
echo(str("=== END POSITIONS ==="));

// ========================================
// NEAREST NEIGHBOR EDGE GENERATION
// ========================================

function dist(v1, v2) = norm(v2 - v1);

// Find nearest neighbor edges (only connect to closest neighbors)
function generate_nearest_neighbor_edges(verts, ratio) =
    let(
        // Calculate all pairwise distances
        distances = [
            for (i = [0:len(verts)-1])
                for (j = [i+1:len(verts)-1])
                    dist(verts[i], verts[j])
        ],
        // Find minimum distance
        min_dist = min([for (d = distances) d]),
        // Set threshold as ratio of minimum
        threshold = min_dist * ratio,
        // Generate edges under threshold
        edges = [
            for (i = [0:len(verts)-1])
                for (j = [i+1:len(verts)-1])
                    if (dist(verts[i], verts[j]) <= threshold)
                        [i, j]
        ]
    )
    edges;

edges = generate_nearest_neighbor_edges(vertices, neighbor_connection_ratio);

// Calculate statistics
min_edge_length = min([for (e = edges) dist(vertices[e[0]], vertices[e[1]])]);
max_edge_length = max([for (e = edges) dist(vertices[e[0]], vertices[e[1]])]);
echo(str("Microphone count: ", mic_count));
echo(str("Vertex distance (radius): ", vertex_distance, " mm"));
echo(str("Number of edges: ", len(edges)));
echo(str("Edge length range: ", min_edge_length, " - ", max_edge_length, " mm"));
echo(str("Max time delay: ~", max_edge_length / 343 * 44100, " samples @ 44.1kHz"));

// ========================================
// SLOT ROTATIONS
// ========================================

function cross(a, b) = [
    a[1] * b[2] - a[2] * b[1],
    a[2] * b[0] - a[0] * b[2],
    a[0] * b[1] - a[1] * b[0]
];

function calculate_slot_rotation(vertex_idx, verts, edge_list) =
    let(
        vertex = verts[vertex_idx],
        normal = vertex / norm(vertex),
        connected_edges = [
            for (edge = edge_list)
                if (edge[0] == vertex_idx || edge[1] == vertex_idx)
                    edge
        ],
        edge_angles = [
            for (edge = connected_edges)
                let(
                    other_idx = edge[0] == vertex_idx ? edge[1] : edge[0],
                    other_v = verts[other_idx],
                    edge_dir = other_v - vertex,
                    global_x = [1, 0, 0],
                    local_x_temp = global_x - normal * (global_x * normal),
                    local_x = norm(local_x_temp) > 0.01 ? local_x_temp / norm(local_x_temp) : [0, 1, 0],
                    local_y = cross(normal, local_x),
                    proj_x = edge_dir * local_x,
                    proj_y = edge_dir * local_y,
                    angle = atan2(proj_y, proj_x)
                )
                angle
        ],
        result = len(edge_angles) == 0 ? 0 :
        len(edge_angles) == 1 ? (edge_angles[0] + 180) :
        let(
            safety_margin = 10,
            normalized = [for (a = edge_angles) (a + 360) % 360],
            sorted = [for (i = [0:len(normalized)-1])
                let(
                    min_val = min([for (j = [i:len(normalized)-1]) normalized[j]]),
                    min_idx = [for (j = [i:len(normalized)-1]) if (normalized[j] == min_val) j][0]
                )
                min_val
            ],
            gaps = [for (i = [0:len(sorted)-1])
                let(
                    next_idx = (i + 1) % len(sorted),
                    next_angle = next_idx == 0 ? sorted[0] + 360 : sorted[next_idx],
                    gap_size = next_angle - sorted[i],
                    gap_start = sorted[i] + safety_margin,
                    gap_end = next_angle - safety_margin,
                    effective_gap = gap_end - gap_start,
                    mid_angle = gap_start + effective_gap / 2
                )
                [effective_gap, mid_angle, gap_size]
            ],
            max_gap_size = max([for (g = gaps) g[0]]),
            max_gap = [for (g = gaps) if (g[0] == max_gap_size) g][0],
            angle = (max_gap[1] % 360)
        )
        angle
    )
    result;

function generate_slot_rotations(verts, edge_list) = [
    for (i = [0:len(verts)-1])
        calculate_slot_rotation(i, verts, edge_list)
];

slot_rotations = generate_slot_rotations(vertices, edges);

// ========================================
// MICROPHONE MOUNT (BASE BUILDING BLOCK)
// ========================================

module microphone_mount_base(vertex_index = 0) {
    difference() {
        union() {
            // Main mounting pad
            cylinder(h=mount_thickness, d=mic_board_diameter + 4, center=false, $fn=32);

            // PCB retaining ring
            translate([0, 0, mount_thickness]) {
                difference() {
                    cylinder(h=1.5, d=mic_board_diameter + 3, center=false, $fn=32);
                    translate([0, 0, -0.1]) {
                        cylinder(h=1.7, d=mic_board_diameter + clearance, center=false, $fn=32);
                    }
                }
            }

            // Mounting posts
            for (angle = [0:90:270]) {
                rotate([0, 0, angle]) {
                    translate([mic_board_diameter/2 + post_offset, 0, mount_thickness]) {
                        cylinder(h=2, d=2, center=false, $fn=12);
                    }
                }
            }
        }

        // Center hole for microphone
        translate([0, 0, -0.1]) {
            cylinder(h=mount_thickness + 2, d=10, center=false, $fn=24);
        }

        // Wire slot cutout
        rotate([0, 0, slot_rotations[vertex_index]]) {
            translate([0, (mic_board_diameter + 6)/4, mount_thickness/2]) {
                cube([6, (mic_board_diameter + 6)/2, mount_thickness + 4], center=true);
            }
        }
    }
}

// ========================================
// MOUNT-FIRST FRAME GENERATION
// ========================================

// Helper: Get mount position and orientation for a vertex
function get_mount_transform(vertex_idx, verts, offset) =
    let(
        vertex = verts[vertex_idx],
        normal = vertex / norm(vertex),
        mount_pos = vertex + normal * offset,
        // Spherical angles for orientation
        polar = atan2(sqrt(normal.x*normal.x + normal.y*normal.y), normal.z),
        azimuth = atan2(normal.y, normal.x)
    )
    [mount_pos, polar, azimuth];


// Create connection from mic mount to IMU base plate edge
module mount_to_imu_connector(idx, verts, offset, imu_size) {
    // Get mount position and orientation
    vertex = verts[idx];
    normal = vertex / norm(vertex);
    mount_pos = vertex + normal * offset;

    // Get slot rotation for this mount (where the wire gap is)
    slot_angle = slot_rotations[idx];

    // Place connection point OPPOSITE to the wire slot (180° away)
    // This ensures the frame arm doesn't interfere with wire routing
    connection_angle = slot_angle + 180;

    // Calculate connection point on mount edge in mount's local coordinate system
    // Use same coordinate system as mount orientation
    polar = atan2(sqrt(normal.x*normal.x + normal.y*normal.y), normal.z);
    azimuth = atan2(normal.y, normal.x);

    // Connection point at mount edge
    mount_radius = mic_board_diameter/2;

    // Transform from mount's local coords to world coords
    // In mount's local frame: X/Y is the mount plane, Z points outward (along normal)
    translate(mount_pos) {
        rotate([0, polar, azimuth]) {
            rotate([0, 0, connection_angle]) {
                translate([mount_radius, 0, 0]) {
                    sphere(r=frame_arm_diameter/2, $fn=12);
                }
            }
        }
    }

    // Connection point at IMU base plate edge
    imu_length = imu_size[0];
    imu_width = imu_size[1];

    // Direction from origin toward mount (in XY plane)
    mount_xy = [mount_pos.x, mount_pos.y];
    mount_norm_xy = norm(mount_xy);
    mount_dir_xy = mount_norm_xy > 0.001 ? mount_xy / mount_norm_xy : [1, 0];

    // Find where this direction intersects IMU base rectangle edge
    t_x = abs(mount_dir_xy[0]) > 0.001 ? (imu_length/2) / abs(mount_dir_xy[0]) : 999;
    t_y = abs(mount_dir_xy[1]) > 0.001 ? (imu_width/2) / abs(mount_dir_xy[1]) : 999;
    t = min(t_x, t_y);

    conn_point_imu = [mount_dir_xy[0] * t, mount_dir_xy[1] * t, 0];

    translate(conn_point_imu) {
        sphere(r=frame_arm_diameter/2, $fn=12);
    }
}

// Main frame module - builds from mounts outward
module parametric_frame_v2() {
    // 1. Create all microphone mounts
    for (i = [0:mic_count-1]) {
        t = get_mount_transform(i, vertices, mount_offset);
        pos = t[0];
        polar = t[1];
        azimuth = t[2];

        translate(pos) {
            rotate([0, polar, azimuth]) {
                microphone_mount_base(i);
            }
        }
    }

    // 2. Create frame connectors from each mount to IMU base edge using hull()
    imu_base_size = [icm_board_length + 8, icm_board_width + 8];
    for (i = [0:mic_count-1]) {
        hull() {
            mount_to_imu_connector(i, vertices, mount_offset, imu_base_size);
        }
    }

    // 3. Add labels
    for (i = [0:mic_count-1]) {
        t = get_mount_transform(i, vertices, mount_offset);
        pos = t[0];
        polar = t[1];
        azimuth = t[2];

        translate(pos) {
            rotate([0, polar, azimuth]) {
                rotate([0, 0, 180]) {
                    translate([0, (mic_board_diameter + 5)/2, mount_thickness/2]) {
                        rotate([90, 0, 0]) {
                            linear_extrude(1) {
                                text(str(i), size=2, halign="center", valign="center", font="Arial:style=Bold");
                            }
                        }
                    }
                }
            }
        }
    }
}

// Wire channels - only cut through the microphone mounts, not the frame arms
module wire_channels() {
    // Central wire bundle channel
    cylinder(h=20, d=wire_diameter + 1, center=true, $fn=16);

    // Wire channels at each microphone position only
    for (i = [0:mic_count-1]) {
        normal = vertices[i] / norm(vertices[i]);
        mount_pos = vertices[i] + normal * mount_offset;

        translate(mount_pos) {
            // Short channel through the mount only, not extending to center
            cylinder(h=mount_thickness + 2, d=wire_diameter + 1, center=true, $fn=16);
        }
    }
}

// Mounting cap (unchanged)
module mounting_cap() {
    difference() {
        union() {
            cylinder(h=1, d=mic_board_diameter + 2, center=false, $fn=32);
            translate([0, 0, 1]) {
                difference() {
                    cylinder(h=0.5, d=mic_board_diameter + 2, center=false, $fn=32);
                    translate([0, 0, -0.1]) {
                        cylinder(h=0.7, d=mic_board_diameter - 2, center=false, $fn=32);
                    }
                }
            }
        }

        translate([0, 0, -0.1]) {
            cylinder(h=2, d=10.5, center=false, $fn=24);
        }

        for (angle = [0:90:270]) {
            rotate([0, 0, angle]) {
                translate([mic_board_diameter/2 + post_offset, 0, -0.1]) {
                    cylinder(h=2, d=1.8, center=false, $fn=12);
                }
            }
        }

        rotate([0, 0, 45]) {
            translate([0, 0, -0.1]) {
                cube([4, mic_board_diameter + 4, 2], center=true);
            }
        }
    }
}

// ========================================
// ICM20948 IMU MOUNT (ADAPTIVE)
// ========================================

function base_plate_exit_point(target_point, base_length, base_width) =
    let(
        dir_xy = [target_point[0], target_point[1], 0],
        dir_norm = norm(dir_xy),
        dir_normalized = dir_norm > 0.001 ? dir_xy / dir_norm : [1, 0, 0],
        t_x = abs(dir_normalized[0]) > 0.001 ? (base_length/2) / abs(dir_normalized[0]) : 999,
        t_y = abs(dir_normalized[1]) > 0.001 ? (base_width/2) / abs(dir_normalized[1]) : 999,
        t = min(t_x, t_y),
        exit_point = dir_normalized * t
    )
    exit_point;

module c_clamp_arm_3d(start_point, end_point, thickness = 1.5, height = 2) {
    direction = end_point - start_point;
    length = norm(direction);

    if (length > 0.001) {
        hull() {
            translate(start_point) {
                cube([thickness, thickness, height], center=true);
            }
            translate(end_point) {
                cube([thickness, thickness, height], center=true);
            }
        }
    }
}

module position_clamp_arm(edge_start, edge_end, base_length, base_width, base_thickness) {
    midpoint = (edge_start + edge_end) / 2;
    direction_to_origin = -midpoint / norm(midpoint);
    sphere_offset = 2.5;
    gripper_position = midpoint + direction_to_origin * sphere_offset;
    start_point_xy = base_plate_exit_point(midpoint, base_length, base_width);
    start_point = [start_point_xy[0], start_point_xy[1], 0];
    extend_past = 3;
    direction = gripper_position - start_point;
    extended_end = gripper_position + (direction / norm(direction)) * extend_past;

    c_clamp_arm_3d(start_point, extended_end, thickness = 1.5, height = base_thickness);
}

module position_clamp_sphere(edge_start, edge_end, base_length, base_width) {
    midpoint = (edge_start + edge_end) / 2;
    direction_to_origin = -midpoint / norm(midpoint);
    // Account for sphere radius (4mm) so sphere surface reaches the edge, not the center
    sphere_radius = 4;
    sphere_offset = 2.5 + sphere_radius;  // Move sphere center further out
    sphere_position = midpoint + direction_to_origin * sphere_offset;

    translate(sphere_position) {
        sphere(r=sphere_radius, $fn=32);
    }
}

module enlarged_edges(edge_radius = 3) {
    for (edge = edges) {
        i = edge[0];
        j = edge[1];
        hull() {
            translate(vertices[i]) sphere(r=edge_radius, $fn=32);
            translate(vertices[j]) sphere(r=edge_radius, $fn=32);
        }
    }
}

function select_imu_clamp_edges(edge_list, verts, target_count=4) =
    let(
        count = min(target_count, len(edge_list)),
        edge_data = [
            for (edge = edge_list)
                let(
                    midpoint = (verts[edge[0]] + verts[edge[1]]) / 2,
                    dist = norm(midpoint),
                    azimuth = atan2(midpoint.y, midpoint.x),
                    elevation = abs(atan2(midpoint.z, sqrt(midpoint.x*midpoint.x + midpoint.y*midpoint.y)))
                )
                [edge, midpoint, dist, azimuth, elevation]
        ],
        max_dist = max([for (d = edge_data) d[2]]),
        threshold = max_dist * 0.6,
        median_elevation = 45,
        outer_edges = [
            for (d = edge_data)
                if (d[2] >= threshold && d[4] <= median_elevation)
                    d
        ],
        outer_edges_final = len(outer_edges) >= count ?  outer_edges :
            [for (d = edge_data) if (d[2] >= threshold) d],
        quadrant_edges = [
            [for (d = outer_edges_final) if (d[3] >= -45 && d[3] < 45) d],
            [for (d = outer_edges_final) if (d[3] >= 45 && d[3] < 135) d],
            [for (d = outer_edges_final) if (d[3] >= 135 || d[3] < -135) d],
            [for (d = outer_edges_final) if (d[3] >= -135 && d[3] < -45) d]
        ],
        selected = [
            for (q = quadrant_edges)
                if (len(q) > 0)
                    let(
                        min_elevation = min([for (d = q) d[4]]),
                        candidates = [for (d = q) if (d[4] == min_elevation) d],
                        max_dist_in_candidates = max([for (d = candidates) d[2]]),
                        best = [for (d = candidates) if (d[2] == max_dist_in_candidates) d][0]
                    )
                    best[0]
        ],
        final = len(selected) >= count ?
            [for (i = [0:count-1]) selected[i]] :
            [for (i = [0:min(count-1, len(outer_edges_final)-1)]) outer_edges_final[i][0]]
    )
    final;

function get_debug_color(index) =
    index == 0 ? [1, 0, 0] :
    index == 1 ? [0, 1, 0] :
    index == 2 ? [0, 0, 1] :
    index == 3 ? [1, 1, 0] :
    [1, 0, 1];

module icm20948_mount() {
    base_width = icm_board_width + 8;
    base_length = icm_board_length + 8;
    base_thickness = 2;

    clamp_edges = select_imu_clamp_edges(edges, vertices, 4);

    echo(str("IMU mount: selecting ", len(clamp_edges), " clamp edges from ", len(edges), " total edges"));
    for (i = [0:len(clamp_edges)-1]) {
        e = clamp_edges[i];
        midpoint = (vertices[e[0]] + vertices[e[1]]) / 2;
        elevation = abs(atan2(midpoint.z, sqrt(midpoint.x*midpoint.x + midpoint.y*midpoint.y)));
        color_name = i == 0 ? "RED" : i == 1 ? "GREEN" : i == 2 ? "BLUE" : "YELLOW";
        echo(str("  Clamp ", i, " (", color_name, "): vertices [", e[0], ",", e[1], "], azimuth=", round(atan2(midpoint.y, midpoint.x)), "°, elevation=", round(elevation), "°, dist=", round(norm(midpoint)*10)/10, "mm"));
    }

    difference() {
        union() {
            translate([-base_length/2, -base_width/2, -base_thickness/2]) {
                cube([base_length, base_width, base_thickness]);
            }

            hole_x = icm_board_length/2 - icm_hole_inset;
            hole_y = icm_board_width/2 - icm_hole_inset;

            translate([-hole_x, -hole_y, base_thickness/2]) {
                cylinder(h=icm_standoff_height, d=4, $fn=16);
            }
            translate([hole_x, -hole_y, base_thickness/2]) {
                cylinder(h=icm_standoff_height, d=4, $fn=16);
            }

        }

        hole_x = icm_board_length/2 - icm_hole_inset;
        hole_y = icm_board_width/2 - icm_hole_inset;

        translate([-hole_x, -hole_y, -base_thickness/2 - 0.1]) {
            cylinder(h=base_thickness + icm_standoff_height + 0.2, d=icm_hole_diameter, $fn=16);
        }
        translate([hole_x, -hole_y, -base_thickness/2 - 0.1]) {
            cylinder(h=base_thickness + icm_standoff_height + 0.2, d=icm_hole_diameter, $fn=16);
        }

        // Subtract radial frame arms for clearance
        // (Arms now connect mics to center, not to each other)
        for (i = [0:mic_count-1]) {
            vertex = vertices[i];
            normal = vertex / norm(vertex);
            mount_pos = vertex + normal * mount_offset;

            // Create clearance channel from center to mount
            hull() {
                sphere(r=frame_arm_diameter/2 + 0.5, $fn=16);  // Center point with clearance
                translate(mount_pos) sphere(r=frame_arm_diameter/2 + 0.5, $fn=16);
            }
        }

        translate([0, 0, base_thickness/2 - 0.3]) {
            linear_extrude(0.4) {
                translate([8, 0, 0]) {
                    polygon([[-2,1], [0,0], [-2,-1]]);
                }
                translate([-10, -2, 0]) {
                    text("FRONT", size=2, halign="left", valign="center", font="Arial:style=Bold");
                }
            }
        }

        translate([0, 0, -base_thickness/2 + 0.3]) {
            mirror([0, 0, 1]) {
                linear_extrude(0.4) {
                    translate([-6, -2, 0]) {
                        text("TOP", size=2, halign="center", valign="center", font="Arial:style=Bold");
                    }
                    translate([-6, 2, 0]) {
                        polygon([[-1,0], [0,2], [1,0]]);
                    }
                }
            }
        }
    }
}

// ========================================
// PRINT LAYOUT
// ========================================

module print_layout() {
    parametric_frame_v2();

    for (i = [0:mic_count-1]) {
        cols = ceil(sqrt(mic_count));
        translate([50 + (i % cols) * 20, floor(i / cols) * 20, 0]) {
            mounting_cap();
        }
    }
}

// ========================================
// RENDERING
// ========================================

// Option 1: Print layout
//print_layout();

// Option 2: IMU mount only
//icm20948_mount();

// Option 3: Preview assembly (default)
parametric_frame_v2();
icm20948_mount();
