/**
 * Desktop Mount for Parametric Spherical Microphone Array
 *
 * Mounts the ambisonic microphone array to a desktop surface via the IMU base plate.
 * Features:
 * - Stable circular base with weight for stability
 * - Vertical post with mounting plate
 * - Attaches to IMU mount holes (matching icm20948_mount dimensions)
 * - Cable routing channel through post
 * - Optional tilt adjustment
 */

// ========================================
// CONFIGURABLE PARAMETERS
// ========================================

// Base parameters
base_diameter = 100;        // Desktop base diameter (mm)
base_thickness = 8;         // Base thickness for stability (mm)
base_chamfer = 2;           // Edge chamfer for aesthetics (mm)

// Post parameters
post_height = 80;           // Height of vertical post (mm)
post_diameter = 20;         // Diameter of support post (mm)
cable_channel_diameter = 10; // Internal cable routing channel (mm)

// Mounting plate parameters (must match IMU mount from parametric_frame_v2.scad)
icm_board_length = 25.4;
icm_board_width = 15.24;
icm_hole_inset = 2.0;
icm_hole_diameter = 2.5;    // Mounting hole diameter
mount_screw_diameter = 2.2; // Clearance for M2 screws
mount_plate_width = icm_board_length + 8;  // Match IMU base plate
mount_plate_length = icm_board_width + 8;  // Match IMU base plate
mount_plate_thickness = 3;

// Standoff parameters
standoff_height = 5;        // Height above mounting plate for array clearance
standoff_diameter = 5;      // Diameter of mounting standoffs

// Cable management
cable_exit_width = 12;      // Width of cable exit notch in base
cable_exit_depth = 4;       // Depth of cable exit notch

// Non-slip pads (recesses for rubber feet)
pad_diameter = 10;
pad_depth = 2;
pad_count = 4;

// ========================================
// MODULES
// ========================================

module desktop_base() {
    difference() {
        // Main base cylinder with chamfer
        hull() {
            cylinder(h=base_thickness, d=base_diameter, center=false, $fn=64);
            translate([0, 0, base_chamfer]) {
                cylinder(h=base_thickness - base_chamfer, d=base_diameter - 2*base_chamfer, center=false, $fn=64);
            }
        }

        // Cable channel through base (continues from post)
        translate([0, 0, -0.1]) {
            cylinder(h=base_thickness + 0.2, d=cable_channel_diameter, center=false, $fn=32);
        }

        // Cable exit notch - extends from edge to center cable channel
        translate([0, -base_diameter/4, base_thickness - cable_exit_depth]) {
            cube([cable_exit_width, base_diameter/2 + 1, cable_exit_depth + 1], center=true);
        }

        // Non-slip pad recesses (bottom)
        for (angle = [45:90:315]) {
            rotate([0, 0, angle]) {
                translate([base_diameter/2 - pad_diameter, 0, -0.1]) {
                    cylinder(h=pad_depth + 0.1, d=pad_diameter, center=false, $fn=32);
                }
            }
        }

        // Weight reduction pockets (optional - can be filled with washers for extra weight)
        for (angle = [0:45:315]) {
            rotate([0, 0, angle]) {
                translate([base_diameter/3, 0, -0.1]) {
                    cylinder(h=base_thickness - 3, d=8, center=false, $fn=32);
                }
            }
        }
    }
}

module support_post() {
    difference() {
        union() {
            // Main post
            translate([0, 0, base_thickness]) {
                cylinder(h=post_height, d=post_diameter, center=false, $fn=48);
            }

            // Chamfered transition to mounting plate using hull
            hull() {
                // Top of post
                translate([0, 0, base_thickness + post_height - 0.1]) {
                    cylinder(h=0.1, d=post_diameter, center=false, $fn=48);
                }

                // Bottom of mounting plate
                translate([0, 0, base_thickness + post_height]) {
                    translate([-mount_plate_width/2, -mount_plate_length/2, 0]) {
                        cube([mount_plate_width, mount_plate_length, 0.1]);
                    }
                }
            }
        }

        // Cable channel through post
        translate([0, 0, base_thickness - 0.1]) {
            cylinder(h=post_height + 0.2, d=cable_channel_diameter, center=false, $fn=32);
        }
    }
}

module mounting_plate() {
    // Calculate hole positions (matching IMU mount)
    hole_x = icm_board_length/2 - icm_hole_inset;
    hole_y = icm_board_width/2 - icm_hole_inset;

    translate([0, 0, base_thickness + post_height]) {
        difference() {
            union() {
                // Main mounting plate
                translate([-mount_plate_width/2, -mount_plate_length/2, 0]) {
                    cube([mount_plate_width, mount_plate_length, mount_plate_thickness]);
                }

                // Mounting standoffs (match IMU hole positions)
                translate([-hole_x, -hole_y, mount_plate_thickness]) {
                    cylinder(h=standoff_height, d=standoff_diameter, center=false, $fn=24);
                }
                translate([hole_x, -hole_y, mount_plate_thickness]) {
                    cylinder(h=standoff_height, d=standoff_diameter, center=false, $fn=24);
                }
            }

            // Mounting holes through standoffs (for M2 screws)
            translate([-hole_x, -hole_y, -0.1]) {
                cylinder(h=mount_plate_thickness + standoff_height + 0.2, d=mount_screw_diameter, center=false, $fn=16);
            }
            translate([hole_x, -hole_y, -0.1]) {
                cylinder(h=mount_plate_thickness + standoff_height + 0.2, d=mount_screw_diameter, center=false, $fn=16);
            }

            // Cable routing hole through mounting plate
            translate([0, 0, -0.1]) {
                cylinder(h=mount_plate_thickness + 0.2, d=cable_channel_diameter, center=false, $fn=32);
            }

            // Orientation marker
            translate([0, mount_plate_length/2 - 2, mount_plate_thickness - 0.3]) {
                linear_extrude(0.4) {
                    text("FRONT", size=2, halign="center", valign="center", font="Arial:style=Bold");
                }
            }
        }
    }
}

// ========================================
// ASSEMBLY
// ========================================

module desktop_mount_assembly() {
    color("SteelBlue") desktop_base();
    color("SteelBlue") support_post();
    color("SteelBlue") mounting_plate();
}

// ========================================
// RENDERING
// ========================================

// Main render
desktop_mount_assembly();

// Print instructions
echo("====================================");
echo("DESKTOP MOUNT FOR AMBISONIC ARRAY");
echo("====================================");
echo(str("Base diameter: ", base_diameter, "mm"));
echo(str("Post height: ", post_height, "mm"));
echo(str("Total height: ", base_thickness + post_height + mount_plate_thickness + standoff_height, "mm"));
echo(str("Cable channel: ", cable_channel_diameter, "mm"));
echo("");
echo("ASSEMBLY INSTRUCTIONS:");
echo("1. Print desktop mount in PETG or ABS for strength");
echo("2. Optional: Add rubber feet in pad recesses for grip");
echo("3. Optional: Add washers in weight reduction pockets");
echo("4. Attach microphone array using 2× M2×10mm screws");
echo("5. Route USB cable through center channel");
echo("6. Ensure 'FRONT' marking aligns with array orientation");
echo("====================================");
