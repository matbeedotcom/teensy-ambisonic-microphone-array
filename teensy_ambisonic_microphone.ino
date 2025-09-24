#include <Audio.h>
#include "AudioOutputTDM_Slave.h"

AudioSynthWaveformSine sine1;
AudioSynthWaveformSine sine2;
AudioSynthWaveformSine sine3;
AudioSynthWaveformSine sine4;
AudioSynthWaveformSine sine5;
AudioSynthWaveformSine sine6;
AudioSynthWaveformSine sine7;
AudioSynthWaveformSine sine8;

AudioOutputTDM_Slave tdmTX;

AudioConnection c0(sine1, 0, tdmTX, 0);
AudioConnection c1(sine2, 0, tdmTX, 1);
AudioConnection c2(sine3, 0, tdmTX, 2);
AudioConnection c3(sine4, 0, tdmTX, 3);
AudioConnection c4(sine5, 0, tdmTX, 4);
AudioConnection c5(sine6, 0, tdmTX, 5);
AudioConnection c6(sine7, 0, tdmTX, 6);
AudioConnection c7(sine8, 0, tdmTX, 7);

void setup() {
  AudioMemory(200);
  Serial.begin(115200);
  Serial.println("TDM Slave - 8 Channel Sine Wave Generator");

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

  Serial.println("Generated frequencies:");
  Serial.println("Ch0: 440 Hz (A4)");
  Serial.println("Ch1: 523 Hz (C5)");
  Serial.println("Ch2: 659 Hz (E5)");
  Serial.println("Ch3: 784 Hz (G5)");
  Serial.println("Ch4: 880 Hz (A5)");
  Serial.println("Ch5: 1047 Hz (C6)");
  Serial.println("Ch6: 1319 Hz (E6)");
  Serial.println("Ch7: 1568 Hz (G6)");
}

void loop() {
  delay(1000);
  Serial.print("CPU Usage: ");
  Serial.print(AudioProcessorUsage());
  Serial.print("%, Memory: ");
  Serial.print(AudioMemoryUsage());
  Serial.println(" blocks");
}