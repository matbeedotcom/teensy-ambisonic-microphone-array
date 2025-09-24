/* Teensy B Slave - 8-Channel Sine Wave TDM Generator
 *
 * This sketch generates 8 sine waves at different frequencies and transmits
 * them via TDM slave mode to Teensy A master.
 *
 * Hardware connections for Teensy 4.1 Slave (B):
 * Clock inputs (from Master A):
 * - Pin 21: SAI1_RX_BCLK - Bit clock (from master)
 * - Pin 20: SAI1_RX_SYNC - Frame sync/LRCLK (from master)
 *
 * TDM output to Master A:
 * - Pin 7: SAI1_TXD0 - TDM data to master (8 channels in slots 0-7)
 *
 * Generated sine wave frequencies:
 * - Ch0: 440 Hz (A4)    - Ch4: 880 Hz (A5)
 * - Ch1: 523 Hz (C5)    - Ch5: 1047 Hz (C6)
 * - Ch2: 659 Hz (E5)    - Ch6: 1319 Hz (E6)
 * - Ch3: 784 Hz (G5)    - Ch7: 1568 Hz (G6)
 */

#include <Audio.h>
#include "AudioOutputTDM_Slave.h"

// Create 8 sine wave generators
AudioSynthWaveformSine sine1;
AudioSynthWaveformSine sine2;
AudioSynthWaveformSine sine3;
AudioSynthWaveformSine sine4;
AudioSynthWaveformSine sine5;
AudioSynthWaveformSine sine6;
AudioSynthWaveformSine sine7;
AudioSynthWaveformSine sine8;

// TDM slave output (uses external clocks from master)
AudioOutputTDM_Slave tdmTX;

// Connect sine generators to TDM output slots 0-7
AudioConnection c0(sine1, 0, tdmTX, 0);  // Ch0 -> TDM slot 0
AudioConnection c1(sine2, 0, tdmTX, 1);  // Ch1 -> TDM slot 1
AudioConnection c2(sine3, 0, tdmTX, 2);  // Ch2 -> TDM slot 2
AudioConnection c3(sine4, 0, tdmTX, 3);  // Ch3 -> TDM slot 3
AudioConnection c4(sine5, 0, tdmTX, 4);  // Ch4 -> TDM slot 4
AudioConnection c5(sine6, 0, tdmTX, 5);  // Ch5 -> TDM slot 5
AudioConnection c6(sine7, 0, tdmTX, 6);  // Ch6 -> TDM slot 6
AudioConnection c7(sine8, 0, tdmTX, 7);  // Ch7 -> TDM slot 7

void setup() {
  // Audio initialization
  AudioMemory(200);

  Serial.begin(115200);
  delay(1000);

  Serial.println("===============================================");
  Serial.println("Teensy 4.1 Slave - 8-Channel TDM Sine Generator");
  Serial.println("===============================================");
  Serial.println();
  Serial.println("Clock inputs (from Master A):");
  Serial.println("  Pin 21: SAI1_RX_BCLK (from master)");
  Serial.println("  Pin 20: SAI1_RX_SYNC (from master)");
  Serial.println();
  Serial.println("TDM output to Master A:");
  Serial.println("  Pin 7:  SAI1_TXD0 (TDM data to master)");
  Serial.println();

  // Configure sine wave generators
  sine1.frequency(440.0);   // A4
  sine1.amplitude(0.5);

  sine2.frequency(523.25);  // C5
  sine2.amplitude(0.5);

  sine3.frequency(659.25);  // E5
  sine3.amplitude(0.5);

  sine4.frequency(783.99);  // G5
  sine4.amplitude(0.5);

  sine5.frequency(880.0);   // A5
  sine5.amplitude(0.5);

  sine6.frequency(1046.5);  // C6
  sine6.amplitude(0.5);

  sine7.frequency(1318.5);  // E6
  sine7.amplitude(0.5);

  sine8.frequency(1568.0);  // G6
  sine8.amplitude(0.5);

  Serial.println("Generated TDM frequencies:");
  Serial.println("  TDM Slot 0: 440 Hz (A4)");
  Serial.println("  TDM Slot 1: 523 Hz (C5)");
  Serial.println("  TDM Slot 2: 659 Hz (E5)");
  Serial.println("  TDM Slot 3: 784 Hz (G5)");
  Serial.println("  TDM Slot 4: 880 Hz (A5)");
  Serial.println("  TDM Slot 5: 1047 Hz (C6)");
  Serial.println("  TDM Slot 6: 1319 Hz (E6)");
  Serial.println("  TDM Slot 7: 1568 Hz (G6)");
  Serial.println();
  Serial.println("TDM slave mode - waiting for master clocks...");
}

void loop() {
  // Print status every second
  delay(1000);
  Serial.print("CPU Usage: ");
  Serial.print(AudioProcessorUsage());
  Serial.print("%, Memory: ");
  Serial.print(AudioMemoryUsage());
  Serial.println(" blocks");
}