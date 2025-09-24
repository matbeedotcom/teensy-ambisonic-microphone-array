#!/usr/bin/env python3
"""
Generate STL files from OpenSCAD model
Requires OpenSCAD to be installed and in PATH
"""

import subprocess
import os
import sys

def check_openscad():
    """Check if OpenSCAD is available."""
    try:
        result = subprocess.run(['openscad', '--version'],
                              capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def generate_stl(scad_file, output_file, params=None):
    """Generate STL file from SCAD file."""
    cmd = ['openscad', '-o', output_file]

    if params:
        for param, value in params.items():
            cmd.extend(['-D', f'{param}={value}'])

    cmd.append(scad_file)

    print(f"Generating {output_file}...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"✓ Generated {output_file}")
        return True
    else:
        print(f"✗ Error generating {output_file}:")
        print(result.stderr)
        return False

def main():
    """Main function to generate all STL files."""
    if not check_openscad():
        print("Error: OpenSCAD not found in PATH")
        print("Please install OpenSCAD from https://openscad.org/")
        sys.exit(1)

    scad_file = "tetrahedron_frame.scad"

    if not os.path.exists(scad_file):
        print(f"Error: {scad_file} not found")
        sys.exit(1)

    # Create output directory
    os.makedirs("stl", exist_ok=True)

    # Generate main frame STL
    success = generate_stl(scad_file, "stl/tetrahedron_frame.stl")

    if success:
        print("\n3D Printing Settings Recommendations:")
        print("- Layer Height: 0.2mm")
        print("- Infill: 20-30%")
        print("- Support: None needed (designed for support-free printing)")
        print("- Orientation: Print with central hub at bottom")
        print("- Material: PLA, PETG, or ABS")
        print("- Print Speed: Normal (50-60mm/s)")

        print(f"\nSTL files generated in 'stl/' directory")
        print("Ready for 3D printing!")

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())