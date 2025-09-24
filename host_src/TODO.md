Awesome—here’s a tight, technical blueprint to get **Stage A (4-mic GCC-PHAT DOA)** working end-to-end with your Teensy and Windows host.

---

# 1) Hardware & wiring (4 mics)

Use **two I²S stereo pairs** on **SAI1**:

* Shared to all 4 mics: **BCLK = pin 21**, **LRCLK/WS = pin 20**, **3V3**, **GND** (0.1 µF at each mic).
* **Pair A** → **SAI1\_RXD0 (pin 8)**

  * Mic A-L: L/R → **GND** (Left slot), SD tied to RXD0
  * Mic A-R: L/R → **3V3** (Right slot), SD tied to RXD0
* **Pair B** → **SAI1\_RXD1 (pin 6)**

  * Mic B-L: L/R → **GND** (Left slot), SD tied to RXD1
  * Mic B-R: L/R → **3V3** (Right slot), SD tied to RXD1

Keep BCLK/LRCLK short & clean; series 22–33 Ω at the Teensy end are nice to have if wires are long.

---

# 2) Teensy firmware (capture 4 channels → USB)

* **USB Type:** Audio (16-bit, 44.1 kHz default)
* **Input:** `AudioInputI2SQuad` (uses SAI1\_RXD0 + RXD1 → 4 channels)
* **Output:** `AudioOutputUSB` (exposes 4 inputs to host)
* **Descriptor:** you already patched 4-in; if not, use the 4-ch descriptor we made.

Minimal sketch:

```cpp
#include <Audio.h>
#include <Arduino.h>

AudioInputI2SQuad i2sQuadIn;  // 4-ch on SAI1 RXD0/RXD1
AudioOutputUSB    usb_out;

// Route 4 ADC lanes -> USB in ch0..3
AudioConnection c0(i2sQuadIn, 0, usb_out, 0); // A-L
AudioConnection c1(i2sQuadIn, 1, usb_out, 1); // A-R
AudioConnection c2(i2sQuadIn, 2, usb_out, 2); // B-L
AudioConnection c3(i2sQuadIn, 3, usb_out, 3); // B-R

void setup() { AudioMemory(120); }
void loop() {}
```

**Channel order sanity:** clap near each mic and watch which host channel spikes (label them now).

---

# 3) Array geometry (choose one)

* **Tetrahedron (recommended for 3D DOA):** vertices of a regular tetra scaled to your shell. Example (meters, centered at origin):

  ```
  p0 = (  a,  a,  a)
  p1 = (  a, -a, -a)
  p2 = (-a,  a, -a)
  p3 = (-a, -a,  a)
  a = 0.025  // ~50 mm spacing tip-to-origin
  ```
* **Planar square (good for 2D azimuth):** 4 corners in one plane; you’ll estimate azimuth only (elevation ambiguous).

Store `P = [p0..p3]` in a JSON the host loads.

---

# 4) Host pipeline (GCC-PHAT → DOA)

We’ll run **block-wise**, e.g. **N=1024** samples (@44.1 kHz → ≈23 ms latency). Steps:

### (a) Read multichannel block

Get 4-ch interleaved **int16** from the Teensy USB device.

### (b) Preprocess

* Convert to float, apply Hann window.
* Optional 1st-order HPF (30–50 Hz) to remove DC/rumble.

### (c) GCC-PHAT (pairwise cross-correlation)

For each pair (i,j), compute time delay of arrival (TDOA) $\hat{\tau}_{ij}$:

1. FFT: $X_i = \mathrm{FFT}(x_i)$, $X_j = \mathrm{FFT}(x_j)$
2. Cross-spectrum: $C_{ij} = X_i \cdot \overline{X_j}$
3. PHAT weight: $C_{ij} \leftarrow C_{ij} / (|C_{ij}|+\epsilon)$
4. IFFT: $r_{ij} = \mathrm{IFFT}(C_{ij})$
5. **Peak** at allowed lags: $\hat{\tau}_{ij} = \arg\max_{|\tau| \le \tau_\text{max}} r_{ij}(\tau)$

Lag bound: $\tau_\text{max} = \frac{d_\text{max}}{c}$, $c \approx 343\,\mathrm{m/s}$, $d_\text{max}$ = max mic spacing (e.g., 0.07 m → ≈0.2 ms → ±9 samples @44.1 k).

### (d) DOA solve

#### 2D (square, azimuth only)

* Assume source on the array plane (z=0); unit direction $\mathbf{s}=[\cos\theta, \sin\theta, 0]$.
* For each pair, model $\tau_{ij} = \frac{1}{c}\,\mathbf{s}\cdot(\mathbf{p}_i - \mathbf{p}_j)$.
* **Grid search** θ ∈ \[−180°,180°], pick θ maximizing consistency with $\hat{\tau}_{ij}$ (least-squares or correlation).

#### 3D (tetra, full DOA)

Two robust approaches:

* **Least-squares on sphere:** find unit $\mathbf{s}$ minimizing
  $\sum_{i<j} \left(\hat{\tau}_{ij} - \frac{1}{c}\,\mathbf{s}\cdot(\mathbf{p}_i-\mathbf{p}_j)\right)^2$ with $\|\mathbf{s}\|=1$. Solve by coarse **spherical grid** (e.g., 5°) then local refine (Gauss-Newton) with unit-norm constraint.

* **SRP-PHAT (steered response):** create a direction grid on the sphere (3–5°). For each direction $\mathbf{s}$, convert to expected **sample delays** $d_{ij} = \mathrm{round}\big((f_s/c)\,\mathbf{s}\cdot(\mathbf{p}_i-\mathbf{p}_j)\big)$. **Sum** the cross-correlations at those delays over all pairs; pick the max.

For 4 mics, both are fast and accurate. SRP-PHAT is very robust in reverb; LS is lighter.

---

# 5) Reference host code (Python, minimal SRP-PHAT)

Below is a compact script outline (uses `sounddevice`, `numpy`). It:

* captures 4-ch blocks from Teensy,
* computes **PHAT-weighted cross-correlations**,
* evaluates a **3D grid**,
* prints azimuth/elevation.

```python
import numpy as np, sounddevice as sd
from numpy.fft import rfft, irfft
from math import pi

# -------- Config --------
fs = 44100
N  = 1024                      # block size
eps = 1e-12
c   = 343.0

# Mic positions (meters): regular tetra around origin
a = 0.025
P = np.array([[ a,  a,  a],
              [ a, -a, -a],
              [-a,  a, -a],
              [-a, -a,  a]], dtype=np.float64)
pairs = [(i,j) for i in range(4) for j in range(i+1,4)]

# Precompute a spherical grid (5°)
def sphere_grid(step_deg=5):
    dirs=[]
    for el in np.radians(np.arange(-85, 86, step_deg)):   # avoid exact poles in coarse grid
        for az in np.radians(np.arange(-180, 180, step_deg)):
            ce, se = np.cos(el), np.sin(el)
            ca, sa = np.cos(az), np.sin(az)
            dirs.append([ce*ca, ce*sa, se])
    return np.array(dirs, dtype=np.float64)
G = sphere_grid(5)             # (Ng,3)
Ng = G.shape[0]
# Expected sample delays per pair and grid dir
D = {}
scale = fs / c
for (i,j) in pairs:
    v = (P[i]-P[j]) @ G.T      # (Ng,)
    D[(i,j)] = np.rint(scale * v).astype(int)

# Choose Teensy device
dev = None
for i,d in enumerate(sd.query_devices()):
    if 'teensy' in d['name'].lower() and d['max_input_channels']>=4:
        dev=i; break
assert dev is not None, "Teensy 4-ch device not found"

# -------- Streaming loop --------
with sd.InputStream(device=dev, channels=4, samplerate=fs, blocksize=N, dtype='int16') as st:
    win = np.hanning(N).astype(np.float64)
    while True:
        x, _ = st.read(N)                 # shape (N,4), int16
        X = (x.astype(np.float64) * win[:,None])  # window & float
        # FFT along time
        XF = rfft(X, axis=0)              # (Nf, 4)

        # Pairwise PHAT cross-corr via IFFT
        score = np.zeros(Ng, dtype=np.float64)
        for (i,j) in pairs:
            Cij = XF[:,i] * np.conj(XF[:,j])
            Cij /= (np.abs(Cij) + eps)
            rij = irfft(Cij)              # circular corr, length N
            # Use a small lag window around 0 (based on array span)
            # Here: +/- 10 samples
            # Accumulate SRP by sampling rij at expected delays for each direction
            di = D[(i,j)]
            # wrap indices to [0,N)
            idx = (di % N)
            score += rij[idx]

        k = int(np.argmax(score))
        s = G[k]                           # unit DOA vector
        az = np.degrees(np.arctan2(s[1], s[0]))
        el = np.degrees(np.arcsin(s[2]))
        print(f"DOA ~ az {az:6.1f}°, el {el:5.1f}° (conf {score[k]:.2f})")
```

**Notes:**

* For a small array (≤10 cm), **±10–15 samples** is a safe lag bound—tighten for speed/robustness.
* You can refine DOA by doing a **local fine search** (1–2° step) around the coarse max.

---

# 6) Calibration & checks

* **Channel map:** do a single-mic tap test (or a beeper) near each sensor to confirm labels.
* **Geometry scale:** if DOA biases, your mic spacing may be off—measure and update `P`.
* **Speed of sound:** set `c` from ambient temp (e.g., $c \approx 331 + 0.6T_{°C}$).

---

# 7) Performance tips

* If the GCC peaks look broad/noisy, bump to **N=2048** (≈46 ms).
* **16-bit** is fine for DOA—phase dominates.
* For reverberant rooms, SRP-PHAT (as coded) outperforms simple TDOA triangulation.

---

## Milestone checklist (Stage A)

1. Teensy enumerates as **4-in**; Audacity/ffmpeg sees 4 channels.
2. Python script prints **sensible az/el** while you move a clap/snap around.
3. Save a few WAVs for offline analysis & parameter tuning.

When Stage A feels solid, we’ll bump to **8** and **12** with the same host code—just update `P` and the device’s channel count.
