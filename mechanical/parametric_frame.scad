/**
 * Parametric Spherical Microphone Array Frame
 * DYNAMICALLY CONFIGURABLE - Any microphone count with optimal spherical distribution
 *
 * Designed for INMP441 breakout boards (15mm diameter)
 * Automatically generates:
 * - Optimal spherical point distribution (Platonic solids or Fibonacci sphere)
 * - Frame structure connecting nearby microphones
 * - Mounting pads at each microphone position
 * - Adaptive IMU mount that clips onto any frame geometry
 *
 * MICROPHONE DISTRIBUTIONS:
 * - 4 mics  → Tetrahedron (1st order ambisonics - 4 channels)
 * - 6 mics  → Octahedron
 * - 8 mics  → Cube (2nd order ambisonics - 9 channels with center)
 * - 12 mics → Icosahedron (3rd order capable)
 * - 20 mics → Dodecahedron (higher order)
 * - Other  → Fibonacci sphere (approximately even distribution)
 *
 * IMPORTANT: Microphones are oriented OUTWARD from the center!
 *
 * HOW TO USE:
 * 1. Set mic_count to desired number of channels (line 27)
 * 2. Set vertex_distance for DOA performance vs size tradeoff (line 30)
 * 3. Adjust max_edge_ratio for frame density (line 35)
 * 4. Render and export STL files
 *
 * The IMU mount automatically adapts to any configuration!
 */

// ========================================
// CONFIGURABLE PARAMETERS
// ========================================

// Number of microphones (determines geometry)
mic_count = 8;  // Change to 4, 6, 8, 12, 20, or any other number

// Array radius configuration
vertex_distance = 61;  // Distance from center to each microphone (mm)
                       // Larger = better DOA, smaller = more compact
                       // Recommended: 61mm for ~70mm spacing (9 samples delay @ 44.1kHz)

// Frame generation parameters
max_edge_ratio = 1.8;  // Maximum edge length as ratio of minimum edge
                       // Lower = denser frame, higher = sparser frame
                       // Typical: 1.5-2.0

// Microphone mount parameters
mic_board_diameter = 15;    // Microphone breakout board diameter
mount_thickness = 3;        // Mounting pad thickness
mount_offset = -10.0;       // Distance from vertex to mounting pad (mm)
post_offset = 1.0;          // Distance from PCB edge to mounting posts (mm)
clearance = 0.2;            // 3D printing clearance

// Frame structure parameters
frame_thickness = 2;        // Frame rod thickness
wire_diameter = 8;          // Wire bundle diameter

// ICM20948 IMU parameters
icm_board_length = 25.4;
icm_board_width = 15.24;
icm_board_thickness = 1.6;
icm_hole_inset = 2.0;
icm_hole_diameter = 2.5;
icm_standoff_height = 3;

// ========================================
// EXAMPLE CONFIGURATIONS
// ========================================
//
// COMPACT 1st ORDER (4 channels):
//   mic_count = 4, vertex_distance = 43mm
//   → ~50mm edge spacing, ~6 samples delay, good for portable devices
//
// STANDARD 1st ORDER (4 channels):
//   mic_count = 4, vertex_distance = 61mm
//   → ~70mm edge spacing, ~9 samples delay, excellent DOA accuracy
//
// COMPACT 2nd ORDER (8 channels):
//   mic_count = 8, vertex_distance = 43mm
//   → ~50mm edge spacing, smaller build
//
// STANDARD 2nd ORDER (8 channels):
//   mic_count = 8, vertex_distance = 61mm (DEFAULT)
//   → ~70mm edge spacing, matches tetrahedral performance
//
// HIGH-ORDER ARRAYS (12+ channels):
//   mic_count = 12, vertex_distance = 61mm
//   → Icosahedron, 3rd order ambisonic capable
//
// The frame structure automatically adapts to all configurations!

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
    let(phi = (1 + sqrt(5)) / 2)  // Golden ratio
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
        cube_vertices(),  // 8 cube vertices
        [  // 12 additional vertices on face centers
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

// Fibonacci sphere (arbitrary count)
function fibonacci_sphere(n) = [
    for (i = [0:n-1])
        let(
            y = 1 - (i / (n - 1)) * 2,  // y from 1 to -1
            radius = sqrt(1 - y * y),    // radius at y
            theta = i * 2.39996323,      // Golden angle in radians (≈137.5°)
            x = cos(theta) * radius,
            z = sin(theta) * radius
        )
        [x, y, z]
];

// ========================================
// VERTEX DISTRIBUTION SELECTOR
// ========================================

function get_raw_vertices(count) =
    count == 4  ? tetrahedron_vertices() :
    count == 6  ? octahedron_vertices() :
    count == 8  ? cube_vertices() :
    count == 12 ? icosahedron_vertices() :
    count == 20 ? dodecahedron_vertices() :
    fibonacci_sphere(count);  // Fallback for arbitrary counts

// Normalize and scale vertices to desired radius
function normalize_vertices(verts, radius) = [
    for (v = verts)
        let(len = norm(v))
        v * (radius / len)
];

// Get final vertex positions
vertices = normalize_vertices(get_raw_vertices(mic_count), vertex_distance);

// ========================================
// EDGE GENERATION (PROXIMITY-BASED)
// ========================================

// Calculate distance between two vertices
function dist(v1, v2) = norm(v2 - v1);

// Find all edges within threshold
function generate_edges(verts, max_ratio) =
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
        threshold = min_dist * max_ratio,
        // Generate edges under threshold
        edges = [
            for (i = [0:len(verts)-1])
                for (j = [i+1:len(verts)-1])
                    if (dist(verts[i], verts[j]) <= threshold)
                        [i, j]
        ]
    )
    edges;

edges = generate_edges(vertices, max_edge_ratio);

// Calculate statistics
min_edge_length = min([for (e = edges) dist(vertices[e[0]], vertices[e[1]])]);
max_edge_length = max([for (e = edges) dist(vertices[e[0]], vertices[e[1]])]);
echo(str("Microphone count: ", mic_count));
echo(str("Vertex distance (radius): ", vertex_distance, " mm"));
echo(str("Number of edges: ", len(edges)));
echo(str("Edge length range: ", min_edge_length, " - ", max_edge_length, " mm"));
echo(str("Max time delay: ~", max_edge_length / 343 * 44100, " samples @ 44.1kHz"));

// ========================================
// SLOT ROTATIONS (AVOID FRAME INTERFERENCE)
// ========================================

// Generate slot rotations based on vertex positions
function generate_slot_rotations(verts) = [
    for (v = verts)
        let(angle = atan2(v.y, v.x))
        (angle + 45) % 360  // Offset by 45° from radial direction
];

slot_rotations = generate_slot_rotations(vertices);

// ========================================
// FRAME GENERATION
// ========================================

module parametric_frame() {
    difference() {
        union() {
            // Frame edges
            frame_edges();

            // Microphone mounting points
            for (i = [0:mic_count-1]) {
                normal = vertices[i] / norm(vertices[i]);
                mount_position = vertices[i] + normal * mount_offset;

                translate(mount_position) {
                    rotate([0, atan2(sqrt(normal.x*normal.x + normal.y*normal.y), normal.z), atan2(normal.y, normal.x)]) {
                        microphone_mount(i);
                    }
                }
            }
        }

        // Wire channels
        wire_channels();

        // Mounting holes
        for (i = [0:mic_count-1]) {
            normal = vertices[i] / norm(vertices[i]);
            mount_position = vertices[i] + normal * mount_offset;
            translate(mount_position) {
                rotate([0, atan2(sqrt(normal.x*normal.x + normal.y*normal.y), normal.z), atan2(normal.y, normal.x)]) {
                    microphone_mounting_holes();
                }
            }
        }
    }

    // Labels
    for (i = [0:mic_count-1]) {
        normal = vertices[i] / norm(vertices[i]);
        mount_position = vertices[i] + normal * mount_offset;
        translate(mount_position) {
            rotate([0, atan2(sqrt(normal.x*normal.x + normal.y*normal.y), normal.z), atan2(normal.y, normal.x)]) {
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

// Frame edge structure
module frame_edges() {
    difference() {
        union() {
            for (edge = edges) {
                i = edge[0];
                j = edge[1];
                hull() {
                    translate(vertices[i]) sphere(r=frame_thickness, $fn=16);
                    translate(vertices[j]) sphere(r=frame_thickness, $fn=16);
                }
            }
        }

        // Subtract mounting pad volumes
        for (i = [0:mic_count-1]) {
            normal = vertices[i] / norm(vertices[i]);
            mount_position = vertices[i] + normal * mount_offset;

            translate(mount_position) {
                rotate([0, atan2(sqrt(normal.x*normal.x + normal.y*normal.y), normal.z), atan2(normal.y, normal.x)]) {
                    cylinder(h=50, d=mic_board_diameter + 6, center=false, $fn=32);
                }
            }
        }
    }
}

// Microphone mount (same as previous designs)
module microphone_mount(vertex_index = 0) {
    difference() {
        union() {
            cylinder(h=mount_thickness, d=mic_board_diameter + 4, center=false, $fn=32);

            translate([0, 0, mount_thickness]) {
                difference() {
                    cylinder(h=1.5, d=mic_board_diameter + 3, center=false, $fn=32);
                    translate([0, 0, -0.1]) {
                        cylinder(h=1.7, d=mic_board_diameter + clearance, center=false, $fn=32);
                    }
                }
            }

            for (angle = [0:90:270]) {
                rotate([0, 0, angle]) {
                    translate([mic_board_diameter/2 + post_offset, 0, mount_thickness]) {
                        cylinder(h=2, d=2, center=false, $fn=12);
                    }
                }
            }
        }

        translate([0, 0, -0.1]) {
            cylinder(h=mount_thickness + 2, d=10, center=false, $fn=24);
        }

        rotate([0, 0, slot_rotations[vertex_index]]) {
            translate([0, (mic_board_diameter + 6)/4, mount_thickness/2]) {
                cube([6, (mic_board_diameter + 6)/2, mount_thickness + 4], center=true);
            }
        }
    }
}

module microphone_mounting_holes() {
    // Integrated into mount
}

// Wire channels
module wire_channels() {
    for (i = [0:mic_count-1]) {
        hull() {
            translate(vertices[i]) {
                cylinder(h=mount_thickness + 1, d=wire_diameter + 1, center=true, $fn=16);
            }
            cylinder(h=6, d=wire_diameter + 1, center=true, $fn=16);
        }
    }
    cylinder(h=20, d=8, center=true, $fn=16);
}

// Mounting cap (same as previous)
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
//
// The IMU mount automatically adapts to any frame geometry:
// 1. Selects 4 well-distributed outer edges from the frame
// 2. Creates C-clamp arms that extend from the base plate to each edge
// 3. Grippers (spheres) intersect with enlarged edge volumes
// 4. Actual frame edges are subtracted to create clip-on channels
//
// This allows the IMU mount to snap onto the center of ANY parametric frame
// without manual adjustment. Just change mic_count and vertex_distance!

module c_clamp_arm(arm_length = 5, arm_height = 2) {
    clamp_thickness = 1.5;
    translate([-clamp_thickness/2, 0, -arm_height/2]) {
        cube([clamp_thickness, arm_length, arm_height]);
    }
}

module c_clamp_sphere(arm_length = 5) {
    gripper_sphere_radius = 4;
    translate([0, arm_length, 0]) {
        sphere(r=gripper_sphere_radius, $fn=32);
    }
}

module position_clamp_arm(edge_start, edge_end, base_length, base_width, base_thickness) {
    midpoint = (edge_start + edge_end) / 2;
    edge_distance = norm(midpoint);
    radial_dir = midpoint / edge_distance;
    radial_azimuth = atan2(radial_dir.y, radial_dir.x) - 90;

    dx = abs(radial_dir.x);
    dy = abs(radial_dir.y);
    t_x = dx > 0.001 ? (base_length/2) / dx : 999;
    t_y = dy > 0.001 ? (base_width/2) / dy : 999;
    base_edge_distance = min(t_x, t_y);
    arm_length = edge_distance - base_edge_distance;

    rotate([0, 0, radial_azimuth]) {
        translate([0, base_edge_distance, 0]) {
            c_clamp_arm(arm_length = arm_length, arm_height = base_thickness);
        }
    }
}

module position_clamp_sphere(edge_start, edge_end, base_length, base_width) {
    midpoint = (edge_start + edge_end) / 2;
    edge_distance = norm(midpoint);
    radial_dir = midpoint / edge_distance;
    radial_azimuth = atan2(radial_dir.y, radial_dir.x) - 90;

    dx = abs(radial_dir.x);
    dy = abs(radial_dir.y);
    t_x = dx > 0.001 ? (base_length/2) / dx : 999;
    t_y = dy > 0.001 ? (base_width/2) / dy : 999;
    base_edge_distance = min(t_x, t_y);
    arm_length = edge_distance - base_edge_distance;
    sphere_offset = -2.5;

    rotate([0, 0, radial_azimuth]) {
        translate([0, base_edge_distance, 0]) {
            c_clamp_sphere(arm_length = arm_length + sphere_offset);
        }
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

// Select well-distributed edges for IMU clamps
// Algorithm: Select edges distributed in azimuth quadrants with good distance from origin
// Prefers more horizontal edges (lower elevation angle)
function select_imu_clamp_edges(edge_list, verts, target_count=4) =
    let(
        count = min(target_count, len(edge_list)),
        // Calculate edge data: [edge, midpoint, distance, azimuth, elevation]
        edge_data = [
            for (edge = edge_list)
                let(
                    midpoint = (verts[edge[0]] + verts[edge[1]]) / 2,
                    dist = norm(midpoint),
                    azimuth = atan2(midpoint.y, midpoint.x),
                    // Elevation: angle from XY plane (prefer low values, close to horizontal)
                    elevation = abs(atan2(midpoint.z, sqrt(midpoint.x*midpoint.x + midpoint.y*midpoint.y)))
                )
                [edge, midpoint, dist, azimuth, elevation]
        ],
        // Find max distance for filtering
        max_dist = max([for (d = edge_data) d[2]]),
        threshold = max_dist * 0.6,  // Accept edges at 60% of max distance (tighter)

        // Filter for outer edges with reasonable elevation (prefer horizontal)
        median_elevation = 45,  // Prefer edges below 45° elevation
        outer_edges = [
            for (d = edge_data)
                if (d[2] >= threshold && d[4] <= median_elevation)
                    d
        ],

        // Fallback: if too few edges, relax elevation constraint
        outer_edges_final = len(outer_edges) >= count ?  outer_edges :
            [for (d = edge_data) if (d[2] >= threshold) d],

        // Divide into quadrants centered at 0°, 90°, 180°, -90°
        quadrant_edges = [
            // Quadrant 0: -45° to 45° (front, +X direction)
            [for (d = outer_edges_final) if (d[3] >= -45 && d[3] < 45) d],
            // Quadrant 1: 45° to 135° (left, +Y direction)
            [for (d = outer_edges_final) if (d[3] >= 45 && d[3] < 135) d],
            // Quadrant 2: 135° to -135° (back, -X direction, wraps at ±180°)
            [for (d = outer_edges_final) if (d[3] >= 135 || d[3] < -135) d],
            // Quadrant 3: -135° to -45° (right, -Y direction)
            [for (d = outer_edges_final) if (d[3] >= -135 && d[3] < -45) d]
        ],

        // Select one edge from each quadrant (prefer farthest AND lowest elevation)
        selected = [
            for (q = quadrant_edges)
                if (len(q) > 0)
                    // Find edge with lowest elevation (most horizontal) in this quadrant
                    let(
                        min_elevation = min([for (d = q) d[4]]),
                        candidates = [for (d = q) if (d[4] == min_elevation) d],
                        // Among candidates with min elevation, take the farthest
                        max_dist_in_candidates = max([for (d = candidates) d[2]]),
                        best = [for (d = candidates) if (d[2] == max_dist_in_candidates) d][0]
                    )
                    best[0]  // Return just the edge
        ],

        // Fallback: if we don't have enough, just take first N outer edges
        final = len(selected) >= count ?
            [for (i = [0:count-1]) selected[i]] :
            [for (i = [0:min(count-1, len(outer_edges_final)-1)]) outer_edges_final[i][0]]
    )
    final;

// Adaptive IMU mount - automatically clamps onto frame
module icm20948_mount() {
    // Base plate sized for ICM20948 board
    base_width = icm_board_width + 8;
    base_length = icm_board_length + 8;
    base_thickness = 2;

    // Automatically select 4 well-distributed outer edges to clamp onto
    clamp_edges = select_imu_clamp_edges(edges, vertices, 4);

    // Debug output - show selected edges
    echo(str("IMU mount: selecting ", len(clamp_edges), " clamp edges from ", len(edges), " total edges"));
    for (i = [0:len(clamp_edges)-1]) {
        e = clamp_edges[i];
        midpoint = (vertices[e[0]] + vertices[e[1]]) / 2;
        elevation = abs(atan2(midpoint.z, sqrt(midpoint.x*midpoint.x + midpoint.y*midpoint.y)));
        echo(str("  Clamp ", i, ": vertices [", e[0], ",", e[1], "], azimuth=", round(atan2(midpoint.y, midpoint.x)), "°, elevation=", round(elevation), "°, dist=", round(norm(midpoint)*10)/10, "mm"));
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

            for (edge = clamp_edges) {
                position_clamp_arm(vertices[edge[0]], vertices[edge[1]], base_length, base_width, base_thickness);
            }

            intersection() {
                union() {
                    for (edge = clamp_edges) {
                        position_clamp_sphere(vertices[edge[0]], vertices[edge[1]], base_length, base_width);
                    }
                }
                enlarged_edges(edge_radius = 3);
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

        frame_edges();

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

// Print layout
module print_layout() {
    parametric_frame();

    for (i = [0:mic_count-1]) {
        cols = ceil(sqrt(mic_count));
        translate([50 + (i % cols) * 20, floor(i / cols) * 20, 0]) {
            mounting_cap();
        }
    }
}

// ========================================
// DEBUG: Visualize selected clamp edges
// ========================================
module visualize_clamp_edges() {
    clamp_edges = select_imu_clamp_edges(edges, vertices, 4);

    // Draw selected edges in red
    color("red", 0.5) {
        for (edge = clamp_edges) {
            hull() {
                translate(vertices[edge[0]]) sphere(r=3, $fn=16);
                translate(vertices[edge[1]]) sphere(r=3, $fn=16);
            }
        }
    }

    // Draw edge midpoints as spheres
    color("blue", 0.8) {
        for (edge = clamp_edges) {
            midpoint = (vertices[edge[0]] + vertices[edge[1]]) / 2;
            translate(midpoint) sphere(r=2, $fn=16);
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
parametric_frame();
icm20948_mount();

// Option 4: Debug - visualize selected clamp edges
//visualize_clamp_edges();
