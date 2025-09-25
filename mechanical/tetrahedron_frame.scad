/**
 * Tetrahedral Microphone Array Frame
 *
 * Designed for 4x INMP441 breakout boards (15mm diameter)
 * Regular tetrahedron with 50mm center-to-vertex distance
 *
 * IMPORTANT: Microphones are oriented OUTWARD from the center!
 * Each mic faces away from the tetrahedron center to capture
 * directional audio from all around the sphere.
 *
 * This gives proper ambisonic capture with sensitivity to:
 * - All horizontal directions (360° azimuth)
 * - Elevation angles from -90° to +90°
 *
 * Includes wire management and strain relief
 */

// Design parameters
vertex_distance = 25;           // Distance from center to vertex (25mm = 50mm spacing)
mic_board_diameter = 15;        // Microphone breakout board diameter
board_thickness = 1.6;          // PCB thickness
wire_diameter = 8;              // Wire bundle diameter
frame_thickness = 2;            // Frame rod thickness
mount_thickness = 3;            // Mounting pad thickness
mount_offset = -10.0;             // Distance from vertex to mounting pad (mm)
post_offset = 1.0;               // Distance from PCB edge to mounting posts (mm)
slot_rotations = [45, 90, 90, 45]; // Optimized angles for each vertex
clearance = 0.2;                // 3D printing clearance

// Calculated tetrahedron vertices (regular tetrahedron)
a = vertex_distance;
vertices = [
    [ a,  a,  a],    // Vertex 0
    [ a, -a, -a],    // Vertex 1
    [-a,  a, -a],    // Vertex 2
    [-a, -a,  a]     // Vertex 3
];

// Main assembly
module tetrahedron_frame() {
    difference() {
        union() {
            // Frame structure
            tetrahedron_edges();

            // Microphone mounting points (positioned closer to connect with frame)
            for (i = [0:3]) {
                // Calculate outward normal vector for this vertex
                normal = vertices[i] / norm(vertices[i]);
                // Position mounting pad using constant offset
                mount_position = vertices[i] + normal * mount_offset;

                translate(mount_position) {
                    // Rotate mounting surface to face outward
                    rotate([0, atan2(sqrt(normal.x*normal.x + normal.y*normal.y), normal.z), atan2(normal.y, normal.x)]) {
                        microphone_mount(i);  // Pass vertex index
                    }
                }
            }
        }

        // Wire channels through frame
        wire_channels();

        // Mounting holes for microphones (positioned closer to match mounting pad)
        for (i = [0:3]) {
            // Calculate outward normal vector for this vertex
            normal = vertices[i] / norm(vertices[i]);
            // Position mounting holes using constant offset
            mount_position = vertices[i] + normal * mount_offset;
            translate(mount_position) {
                // Rotate mounting holes to match outward orientation
                rotate([0, atan2(sqrt(normal.x*normal.x + normal.y*normal.y), normal.z), atan2(normal.y, normal.x)]) {
                    microphone_mounting_holes();
                }
            }
        }
    }

    // Labels embedded on the outside of mounting pad cylinders
    for (i = [0:3]) {
        // Calculate outward normal vector for this vertex
        normal = vertices[i] / norm(vertices[i]);
        // Position label using constant offset
        mount_position = vertices[i] + normal * mount_offset;
        translate(mount_position) {
            // Rotate label to match outward orientation
            rotate([0, atan2(sqrt(normal.x*normal.x + normal.y*normal.y), normal.z), atan2(normal.y, normal.x)]) {
                // Position label on the outside surface of the mounting pad
                rotate([0, 0, 180]) {  // Rotate to opposite side from wire slot
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

// Tetrahedron edge structure
module tetrahedron_edges() {
    difference() {
        // Connect each vertex to every other vertex (full frame)
        union() {
            for (i = [0:3]) {
                for (j = [i+1:3]) {
                    hull() {
                        translate(vertices[i]) sphere(r=frame_thickness);
                        translate(vertices[j]) sphere(r=frame_thickness);
                    }
                }
            }
        }

        // Subtract mounting pad volumes and everything above them from frame
        for (i = [0:3]) {
            // Calculate outward normal vector for this vertex
            normal = vertices[i] / norm(vertices[i]);
            // Position where mounting pad will be
            mount_position = vertices[i] + normal * mount_offset;

            translate(mount_position) {
                // Rotate to match mounting pad orientation
                rotate([0, atan2(sqrt(normal.x*normal.x + normal.y*normal.y), normal.z), atan2(normal.y, normal.x)]) {
                    // Cut out volume for mounting pad and everything above it
                    cylinder(h=50, d=mic_board_diameter + 6, center=false, $fn=32);
                }
            }
        }
    }
}

// Microphone mounting pad - fixed to frame
module microphone_mount(vertex_index = 0) {
    difference() {
        union() {
            // Base mounting pad
            cylinder(h=mount_thickness, d=mic_board_diameter + 4, center=false, $fn=32);

            // Raised rim to hold PCB (1mm thick) with snap-fit
            translate([0, 0, mount_thickness]) {
                difference() {
                    cylinder(h=1.5, d=mic_board_diameter + 3, center=false, $fn=32);
                    translate([0, 0, -0.1]) {
                        cylinder(h=1.7, d=mic_board_diameter + clearance, center=false, $fn=32);
                    }
                }
            }

            // Press-fit posts for cap attachment (4 posts)
            for (angle = [0:90:270]) {
                rotate([0, 0, angle]) {
                    translate([mic_board_diameter/2 + post_offset, 0, mount_thickness]) {
                        // Posts that the cap will press onto
                        cylinder(h=2, d=2, center=false, $fn=12);
                    }
                }
            }
        }

        // Center hole (1cm diameter) - through entire mount
        translate([0, 0, -0.1]) {
            cylinder(h=mount_thickness + 2, d=10, center=false, $fn=24);
        }

        // Cable passthrough slot - positioned to avoid frame connections
        // Rotate the slot direction based on vertex to avoid frame edge interference
        rotate([0, 0, slot_rotations[vertex_index]]) {
            translate([0, (mic_board_diameter + 6)/4, mount_thickness/2]) {
                cube([6, (mic_board_diameter + 6)/2, mount_thickness + 4], center=true);
            }
        }
    }
}

// This module is no longer needed - holes are integrated into microphone_mount()
module microphone_mounting_holes() {
    // No additional holes needed - everything is handled in microphone_mount()
}

// Central hub for wire management
module central_hub() {
    sphere(r=8, $fn=32);
}

// Wire routing channels
module wire_channels() {
    // Channels from each vertex to center
    for (i = [0:3]) {
        hull() {
            translate(vertices[i]) {
                cylinder(h=mount_thickness + 1, d=wire_diameter + 1, center=true, $fn=16);
            }
            cylinder(h=6, d=wire_diameter + 1, center=true, $fn=16);
        }
    }

    // Central wire exit hole
    cylinder(h=20, d=8, center=true, $fn=16);
}

// Removed strain relief clips - not needed

// Assembly instructions marker
module assembly_marker(vertex_num) {
    translate([0, 0, mount_thickness + 0.1]) {
        color("red") {
            linear_extrude(0.3) {
                difference() {
                    circle(d=4, $fn=16);
                    text(str(vertex_num), size=2, halign="center", valign="center");
                }
            }
        }
    }
}

// Press-fit cap for securing PCB to mounting pad
module mounting_cap() {
    difference() {
        union() {
            // Main cap body
            cylinder(h=1, d=mic_board_diameter + 2, center=false, $fn=32);

            // Raised edge to hold PCB down
            translate([0, 0, 1]) {
                difference() {
                    cylinder(h=0.5, d=mic_board_diameter + 2, center=false, $fn=32);
                    translate([0, 0, -0.1]) {
                        cylinder(h=0.7, d=mic_board_diameter - 2, center=false, $fn=32);
                    }
                }
            }
        }

        // Center hole for microphone (1cm)
        translate([0, 0, -0.1]) {
            cylinder(h=2, d=10.5, center=false, $fn=24);
        }

        // Press-fit holes for posts (4 holes)
        for (angle = [0:90:270]) {
            rotate([0, 0, angle]) {
                translate([mic_board_diameter/2 + post_offset, 0, -0.1]) {
                    // Slightly smaller than posts for press fit
                    cylinder(h=2, d=1.8, center=false, $fn=12);
                }
            }
        }

        // Cable access slot (matches mounting pad slot orientation)
        rotate([0, 0, 45]) {  // Default orientation - adjust per cap if needed
            translate([0, 0, -0.1]) {
                cube([4, mic_board_diameter + 4, 2], center=true);
            }
        }
    }
}

// Print layout - main frame and caps
module print_layout() {
    // Main frame
    tetrahedron_frame();

    // Press-fit caps (4x)
    for (i = [0:3]) {
        translate([50 + (i % 2) * 20, (i < 2 ? 0 : 20), 0]) {
            mounting_cap();
        }
    }
}

// Removed wire management clip - not needed

// Render the frame
print_layout();