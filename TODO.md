Here’s the practical, nuts-and-bolts way to make **Teensy B** a **clock-slave** that **packs \~8 input channels into a single TDM stream** and sends that to **Teensy A**.

---

# 1) Wiring (one clock domain from A)

**A (master)** → **B (slave)**

* **BCLK**: A pin **21** → B pin **21**
* **LRCLK/FS**: A pin **20** → B pin **20**
* **GND**: common ground
* **TDM data B→A**: B pin **7** (`SAI1_TXD0`) → A pin **8** (`SAI1_RXD0`)

**B’s microphones** (unchanged):

* All INMP441 mics on B still use **BCLK=21** and **LRCLK=20** (now driven by A), and their **SD** lines go to B’s **RXDx** pins (e.g., SAI1\_RXD0/1/2/3 & SAI2\_RXD0/1).

---

# 2) What the firmware needs to do on Teensy B

### Inputs (mic capture) — run as **slave**

* Use the **slave** variants for I²S where available:

  * `AudioInputI2Sslave` (for a stereo pair on SAI2, etc.)
* For `AudioInputI2SQuad` (SAI1 RXD0+RXD1) there isn’t an official slave object; you either:

  * use two `AudioInputI2Sslave` objects on the lanes you’re using, **or**
  * drop in a tiny **Quad-Slave** class (I can supply this if you want to keep quad).

Either way, the key is: **B never drives clocks**; it just samples on A’s BCLK/LRCLK.

### Output (TDM transmit) — run TDM **TX as slave**

* Stock `AudioOutputTDM` configures SAI **as master**.
* For your topology, you want a **TDM TX “slave”**: SAI1 TX uses **external BCLK/LRCLK** from A and only drives **TXD0** (pin 7).

This is a very small init tweak to the TDM TX config:

* **Bit-clock direction** = **external** (SAI uses incoming BCLK)
* **Frame-sync direction** = **external** (uses incoming LRCLK/FS)
* **Frame size** = **16 slots** (we’ll use 8 of them and zero the rest)
* **Slot width** = **32 bits** (common & simple; matches Teensy’s TDM class)
* **DMA** fills the 16 slots each audio block; your 8 channels map to **slots 0–7**

---

# 3) Channel plan (8-out TDM16)

* Map your 8 captured mic channels to **TDM slots 0..7**
* Write **zeros** into slots **8..15**
* On Teensy A, use `AudioInputTDM` and read channels 0..7 (ignore 8..15)

---

# 4) Minimal code shape on Teensy B

Below is the **shape** (not the whole Teensy Audio class), so you see what changes. If you like, I can drop a ready-to-compile `AudioOutputTDM_Slave.cpp/.h` next.

```cpp
// Teensy B (slave): capture 8 mics, pack into TDM16 TX (slave), send to A

#include <Audio.h>
#include <Arduino.h>

// ---- inputs (examples) ----
// SAI1 lanes (quad) -> if you have a Quad-Slave class, use it; otherwise 2x I2Sslave
AudioInputI2Sslave i2s1_lane0; // e.g., RXD0 (Left/Right)
AudioInputI2Sslave i2s1_lane1; // e.g., RXD1 (Left/Right)

// SAI2 lane (extra stereo), optional
AudioInputI2Sslave i2s2_lane0;

// ---- TDM slave TX (custom object; uses external BCLK/LRCLK on pins 21/20) ----
AudioOutputTDM_Slave tdmTX;  // drives SAI1_TXD0 (pin 7), 16 slots/frame

// Connect 8 channels into TDM slots 0..7
// (Each AudioOutputTDM* exposes 16 inputs, like the stock TDM object.)
AudioConnection c0(i2s1_lane0, 0, tdmTX, 0);  // ch0 -> slot0
AudioConnection c1(i2s1_lane0, 1, tdmTX, 1);  // ch1 -> slot1
AudioConnection c2(i2s1_lane1, 0, tdmTX, 2);  // ch2 -> slot2
AudioConnection c3(i2s1_lane1, 1, tdmTX, 3);  // ch3 -> slot3
AudioConnection c4(i2s2_lane0, 0, tdmTX, 4);  // ch4 -> slot4
AudioConnection c5(i2s2_lane0, 1, tdmTX, 5);  // ch5 -> slot5
// Add two more inputs as needed:
AudioConnection c6(/* your next input */, 0, tdmTX, 6);
AudioConnection c7(/* your next input */, 0, tdmTX, 7);

void setup() {
  AudioMemory(200);

  // IMPORTANT: ensure B is not generating clocks
  // Using *slave* input objects does this for RX.
  // For TDM TX, our AudioOutputTDM_Slave init will configure SAI1 TX to use external BCLK/LRCLK.
}

void loop() {
  // Nothing; Audio library + DMA do the work
}
```

---

# 5) What the **TDM TX “slave” init** actually does (under the hood)

(For the i.MX RT1062 SAI, simplified; exact bit names vary slightly by header)

* **Select TDM mode / slot format**

  * `TCR4.FRSZ = 16-1`   // 16 slots per frame
  * `TCR4.SYWD = 32-1`   // 32-bit slot width
  * `TCR4.FSE = 1`       // frame sync early (aligns with standard TDM)
* **Use external clocks**

  * `TCR2.BCD = 0`       // Bit Clock Direction = external (slave)
  * `TCR4.FSD = 0`       // Frame Sync Direction = external (slave)
  * `TCR2.MSEL = 0`      // Bit-clock source = bus clock (ignored as slave)
* **Enable the transmitter on channel 0**

  * `TCR3.TCE = (1<<0)`  // Enable TX channel 0 (TXD0)
* **DMA**

  * Configure DMA to feed the TX FIFO every audio block; buffer layout = 16 interleaved slots × 32-bit words

That’s exactly what a small `AudioOutputTDM_Slave` class would set in its `begin()` before enabling `TCSR.TE`.

---

# 6) On Teensy A (the receiver)

* Keep A as **master** for clocks (default in Teensy Audio lib).
* Add `AudioInputTDM tdmIn;` and wire your 12 local + 8 remote channels as needed.
* A’s pin **8** is `SAI1_RXD0` → that’s the TDM data from B.
* USB on A advertises **(local + remote)** input channel count.

---

# 7) Signal-integrity tips

* Put **22–33 Ω** series resistors at **A’s** BCLK/LRCLK outputs (one per branch) if you have multiple long branches.
* Keep **B TXD0 → A RXD0** short and paired with **GND** (twisted pair / FFC with adjacent ground).
* Only **one** device (A) should ever drive BCLK/LRCLK.