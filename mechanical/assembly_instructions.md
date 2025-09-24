# Tetrahedral Microphone Array Assembly Instructions

## Overview
This guide covers assembly of the 3D printed tetrahedral frame for your 4-microphone ambisonic array.

⚠️ **CRITICAL**: Microphones must face **OUTWARD** from the center for proper directional audio capture!

## Parts Required

### 3D Printed Components
- [x] 1x Tetrahedral frame (`tetrahedron_frame.stl`)
- [x] 4x PCB adapter rings with twist-lock tabs (included in print)
- [x] 4x Strain relief clips (included in print)
- [x] 1x Wire management clip (included in print)

### Electronic Components
- [x] 4x INMP441 I2S microphone breakout boards (15mm diameter, 1mm thick)
- [x] 4x sets of I2S wires (5-wire: VDD, GND, SCK, WS, SD)
- [x] Small amount of double-sided tape or adhesive (optional)

### Tools Needed
- Wire strippers
- Soldering iron & solder
- Heat shrink tubing (optional)
- Small drill bit (2-3mm) for cable routing if needed

## Assembly Steps

### Step 1: 3D Print Preparation
1. **Print Settings**:
   - Layer Height: 0.2mm
   - Infill: 20-30%
   - No supports needed (designed support-free)
   - Print with central hub at bottom

2. **Post-Processing**:
   - Remove any support material or brim
   - Test-fit microphone boards in mounting holes
   - Clean mounting holes with small drill bit if needed

### Step 2: Microphone Orientation Check

**CRITICAL**: Each microphone must face **OUTWARD** from the tetrahedron center.

The INMP441 microphone element (small black square) should point:
- **Mic 0**: Up-Right-Forward direction
- **Mic 1**: Up-Left-Back direction
- **Mic 2**: Down-Right-Back direction
- **Mic 3**: Down-Left-Forward direction

### Step 3: Wire Preparation

For each microphone, prepare a 4-wire cable (~20cm length):
- **Red**: VDD (3.3V)
- **Black**: GND
- **Blue**: SCK (Serial Clock)
- **Green**: WS (Word Select/LRCLK)
- **Yellow**: SD (Serial Data)

1. Strip wire ends (~3mm)
2. Pre-tin wire ends with solder
3. Add strain relief clips to wire bundles

### Step 4: Microphone Mounting

For each of the 4 vertex positions:

1. **Orient the microphone correctly**:
   - Place breakout board on mounting pad
   - Ensure microphone element faces OUTWARD from center
   - The mic should point away from the central hub

2. **Solder connections**:
   - Solder 5-wire bundle to breakout board
   - Use heat shrink or tape for strain relief

3. **Secure with screws**:
   - Insert M2 screws through mounting holes
   - Tighten gently (don't over-torque plastic)

4. **Route wires**:
   - Thread wire bundle through vertex channel toward center
   - Leave enough slack for movement

### Step 5: Wire Management

1. **Route all wires to central hub**
2. **Group by function**:
   - All VDD wires → single power connection
   - All GND wires → single ground connection
   - Each SCK/WS/SD → separate I2S connections

3. **Use wire management clip** to organize cable bundle
4. **Add strain relief** at central hub exit

### Step 6: Testing & Calibration

1. **Visual inspection**:
   - All 4 microphones face outward ✓
   - No loose connections ✓
   - Wires properly managed ✓

2. **Electrical test**:
   - Check continuity of all connections
   - Verify no shorts between power rails

3. **Functional test**:
   - Connect to Teensy and run audio capture
   - Clap near each microphone to verify channel mapping
   - Use DOA visualizer to check directional response

## Microphone Channel Mapping

Based on your array geometry configuration:

| Position | Vertex | Direction Vector | I2S Connection |
|----------|--------|------------------|----------------|
| Mic 0    | (+,+,+)| Up-Right-Forward | SAI1_RXD0 Left |
| Mic 1    | (+,-,-)| Up-Left-Back     | SAI1_RXD0 Right|
| Mic 2    | (-,+,-)| Down-Right-Back  | SAI1_RXD1 Left |
| Mic 3    | (-,-,+)| Down-Left-Forward| SAI1_RXD1 Right|

## Troubleshooting

### Poor Directional Response
- **Check**: Are all mics facing outward?
- **Fix**: Remount any inward-facing microphones

### Noisy Audio
- **Check**: Wire shielding and grounding
- **Fix**: Add twisted pair wiring, star ground connection

### Inconsistent Channel Levels
- **Check**: Loose connections, damaged microphones
- **Fix**: Resolder connections, replace faulty mics

### Mechanical Issues
- **Check**: 3D print quality, screw tightness
- **Fix**: Reprint damaged parts, adjust mounting

## Mounting the Complete Array

The assembled array can be mounted using:
1. **Tripod mount**: Add 1/4"-20 threaded insert to central hub
2. **Ceiling mount**: Suspend from central point with wire/chain
3. **Desktop stand**: Create weighted base with central mount point

## Final Notes

- Keep the array away from reflective surfaces during testing
- The frame is designed to minimize acoustic shadowing
- Label each microphone channel for easy identification
- Store in protective case when not in use

Good luck with your ambisonic array build! 🎤🔊