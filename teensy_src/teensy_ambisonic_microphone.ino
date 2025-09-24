/* Teensy 4.1 Master - Local I2S + Remote TDM to 8-Channel USB
 *
 * This sketch receives:
 * - 4 local I2S microphone channels (SAI1 RX)
 * - 4 remote TDM channels from Teensy B slave (first 4 of 8 TDM slots)
 * - Routes all 8 channels to USB output
 *
 * Hardware connections for Teensy 4.1 Master (A):
 * Local microphones (unchanged):
 * - Pin 8 (GPIO_B1_00): SAI1_RXD0 - Local mic pair 1 (L1/R1)
 * - Pin 6 (GPIO_B0_10): SAI1_RXD1 - Local mic pair 2 (L2/R2)
 *
 * Clock generation (master):
 * - Pin 21 (GPIO_AD_B1_11): SAI1_BCLK - Bit clock (drives slave)
 * - Pin 20 (GPIO_AD_B1_10): SAI1_SYNC - Frame sync/LRCLK (drives slave)
 * - Pin 23 (GPIO_AD_B1_09): SAI1_MCLK - Master clock
 *
 * TDM data from Teensy B slave:
 * - Pin 8: SAI1_RXD0 - TDM data from slave (using slots 0-3 of 16)
 *
 * Note: Pin 8 serves dual purpose - local I2S RX and remote TDM RX
 */

 #include <Audio.h>
 #include <Wire.h>
 #include <SPI.h>
 
 // Create audio objects
 AudioInputI2SQuad    i2sQuadIn;      // 4-channel local I2S input using SAI1_RXD0 and RXD1
 AudioInputTDM        tdmIn;          // 16-channel TDM input (using channels 0-7 from slave)
 AudioOutputUSB       usbOut;         // 8-channel USB output to PC

 // Connect local I2S inputs to USB channels 0-3
 AudioConnection patchCord1(i2sQuadIn, 0, usbOut, 0);   // Local Ch0 (L1 from RXD0)
 AudioConnection patchCord2(i2sQuadIn, 1, usbOut, 1);   // Local Ch1 (R1 from RXD0)
 AudioConnection patchCord3(i2sQuadIn, 2, usbOut, 2);   // Local Ch2 (L2 from RXD1)
 AudioConnection patchCord4(i2sQuadIn, 3, usbOut, 3);   // Local Ch3 (R2 from RXD1)

 // Connect remote TDM inputs to USB channels 4-7 (first 4 of 8 TDM channels)
 AudioConnection patchCord5(tdmIn, 0, usbOut, 4);       // Remote Ch0 (440 Hz)
 AudioConnection patchCord6(tdmIn, 1, usbOut, 5);       // Remote Ch1 (523 Hz)
 AudioConnection patchCord7(tdmIn, 2, usbOut, 6);       // Remote Ch2 (659 Hz)
 AudioConnection patchCord8(tdmIn, 3, usbOut, 7);       // Remote Ch3 (784 Hz)

 // Monitor audio levels - local channels
 AudioAnalyzePeak     peakLocal[4];
 AudioConnection patchCord9(i2sQuadIn, 0, peakLocal[0], 0);
 AudioConnection patchCord10(i2sQuadIn, 1, peakLocal[1], 0);
 AudioConnection patchCord11(i2sQuadIn, 2, peakLocal[2], 0);
 AudioConnection patchCord12(i2sQuadIn, 3, peakLocal[3], 0);

 // Monitor audio levels - remote TDM channels (first 4)
 AudioAnalyzePeak     peakRemote[4];
 AudioConnection patchCord13(tdmIn, 0, peakRemote[0], 0);
 AudioConnection patchCord14(tdmIn, 1, peakRemote[1], 0);
 AudioConnection patchCord15(tdmIn, 2, peakRemote[2], 0);
 AudioConnection patchCord16(tdmIn, 3, peakRemote[3], 0);
 
 void setup() {
   Serial.begin(115200);

   // Audio initialization - increased memory for 12 channels
   AudioMemory(40);

   // Wait for serial monitor
   delay(1000);

   Serial.println("=============================================");
   Serial.println("Teensy 4.1 Master - 8-Channel USB Audio");
   Serial.println("=============================================");
   Serial.println();
   Serial.println("Local I2S microphones (4 channels):");
   Serial.println("  Pin 8:  SAI1_RXD0 (Local Pair 1 - L1/R1)");
   Serial.println("  Pin 6:  SAI1_RXD1 (Local Pair 2 - L2/R2)");
   Serial.println();
   Serial.println("Clock generation (master):");
   Serial.println("  Pin 21: SAI1_BCLK (drives slave)");
   Serial.println("  Pin 20: SAI1_SYNC/LRCLK (drives slave)");
   Serial.println("  Pin 23: SAI1_MCLK");
   Serial.println();
   Serial.println("TDM from Teensy B slave (first 4 of 8 channels):");
   Serial.println("  Pin 8:  SAI1_RXD0 (TDM data from slave)");
   Serial.println();
   Serial.println("USB Audio Channels:");
   Serial.println("  Ch 0-3: Local I2S microphones");
   Serial.println("  Ch 4-7: Remote TDM from slave");
   Serial.println("    Ch 4: 440 Hz (A4)");
   Serial.println("    Ch 5: 523 Hz (C5)");
   Serial.println("    Ch 6: 659 Hz (E5)");
   Serial.println("    Ch 7: 784 Hz (G5)");
   Serial.println();
   Serial.println("USB Audio: Should appear as 'Teensy Audio 8CH'");
   Serial.println("Starting 8-channel audio streaming...");
   Serial.println();
 }
 
 void loop() {
   // Print peak levels every 1000ms
   static elapsedMillis timeout = 0;

   if (timeout >= 1000) {
     timeout = 0;

     // Check if peak analyzers have data
     bool hasLocalData = true;
     bool hasRemoteData = true;

     for (int i = 0; i < 4; i++) {
       if (!peakLocal[i].available()) hasLocalData = false;
     }
     for (int i = 0; i < 4; i++) {
       if (!peakRemote[i].available()) hasRemoteData = false;
     }

     if (hasLocalData || hasRemoteData) {
       Serial.println("=== AUDIO LEVELS ===");

       // Local I2S channels
       if (hasLocalData) {
         Serial.print("Local I2S: ");
         for (int i = 0; i < 4; i++) {
           float level = peakLocal[i].read();
           Serial.print("Ch");
           Serial.print(i);
           Serial.print(":");
           printBarCompact(level);
           Serial.print(" ");
         }
         Serial.println();
       }

       // Remote TDM channels
       if (hasRemoteData) {
         Serial.print("Remote TDM: ");
         for (int i = 0; i < 4; i++) {
           float level = peakRemote[i].read();
           Serial.print("Ch");
           Serial.print(i + 4);  // USB channels 4-7
           Serial.print(":");
           printBarCompact(level);
           Serial.print(" ");
         }
         Serial.println();
       }
       Serial.println();
     }
   }

   // Print memory usage every 5 seconds
   static elapsedMillis statusTimeout = 0;
   if (statusTimeout >= 5000) {
     statusTimeout = 0;
     Serial.print("Audio memory: ");
     Serial.print(AudioMemoryUsage());
     Serial.print("/");
     Serial.print(AudioMemoryUsageMax());
     Serial.print("  CPU: ");
     Serial.print(AudioProcessorUsage());
     Serial.println("%");
     Serial.println();
   }
 }
 
 void printBar(float level) {
   Serial.print("[");
   int bars = level * 20;
   for (int i = 0; i < 20; i++) {
     if (i < bars) Serial.print("=");
     else Serial.print(" ");
   }
   Serial.print("]");
 }

 void printBarCompact(float level) {
   Serial.print("[");
   int bars = level * 8;  // Shorter bar for compact display
   for (int i = 0; i < 8; i++) {
     if (i < bars) Serial.print("=");
     else Serial.print(" ");
   }
   Serial.print("]");
 }