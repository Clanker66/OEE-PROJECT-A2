# 🔬 OOE VIRTUAL LABORATORY: OPTICAL & EM SYSTEMS
**Institution:** National Higher School of Advanced Technologies (ENSTA)  
**Module:** Physics / Computer Vision  
**Academic Year:** 2025–2026  
**Supervisor:** Dr. CHEGGOU Rabéa  
**Class** A2
---

> **📌 NOTE FOR STUDENTS:** This GitHub repository has been established for a **Better Collection** and professional archiving of your submitted works. It serves as the official digital library for the MI2 OOE projects.

---

## 👥 TEAM IDENTIFICATION
- **Project Leader:** AKLI Merouane
- **Group Number:** G1
- **Team Members:**
  1. EL MOKRETAR Akram
  2. AKBOUDJ Anis Mohammed Nassim
  3. NAMANE Haithem
  4. SAIBI Mohamed Abdelilah
  5. MESSIKH Mohammed Yahia
  6. BENNACER Sami Fares
---

## 📂 PROJECT THEMES

### Theme 1: Physics of Refraction & Engineering Applications
* Geometric modeling of refraction (Snell-Descartes laws).
* Apparent depth phenomena and underwater robotic guidance.
* Fiber optics: Critical angles and total internal reflection.

### Theme 2: Biophysics of Vision & Optical Correction
* Modeling the human eye (Relaxed vs. Accommodated).
* Physiological causes of Myopia and corrective lens simulations.

### Theme 3: Advanced Projection & Surveillance Systems
* Ray tracing for video projectors and image inversion.
* Wide-angle visualization through door peepholes (-10D lenses).

### Theme 4: EM Waves, Interference & Diffraction
* Wave propagation and Electromagnetic spectrum.
* Modeling Young’s double-slit interference patterns.
* Diffraction impact on resolution in Computer Vision.

---
# THEME 4's PROJECT
# (Geometric Project) Standing Wave Spy Decoder

A Python desktop simulation that combines **geometric optics**, **standing waves**, and **cryptography** to visualize how a secret message can be transmitted and decoded using wave physics.

## Table of Contents

- [What It Does](#what-it-does)
- [Physics & Laws Used](#physics--laws-used)
- [Requirements](#requirements)
- [Installation](#installation)
  - [Windows](#windows)
  - [Linux](#linux)
- [How to Run](#how-to-run)
- [How to Use the Simulation](#how-to-use-the-simulation)
- [Understanding the Plots](#understanding-the-plots)
- [Project Structure](#project-structure)
- [Example](#example)

---

## What It Does

The program simulates a scenario where an encrypted message is transmitted as an AM-FSK (Amplitude Modulated - Frequency Shift Keying) signal that reflects off a metal wall, creating a **standing wave**. A receiver placed at different positions along the x-axis picks up the signal — but only at specific positions (antinodes) is the signal strong enough to decode.

The message is also encrypted using a **Caesar cipher** before transmission, adding a second layer of security.

---

## Physics & Laws Used

### 1. Law of Reflection
> The angle of incidence equals the angle of reflection (θᵢ = θᵣ)

The signal wave hits a metal wall at angle θ and reflects back at the same angle. The geometry panel visualizes the incident and reflected rays with wavefronts.

### 2. Standing Waves
When the incident and reflected waves interfere, they form a **standing wave**:

```
E(x, t) = 2 · sin(k⊥ · x) · cos(ωt)
```

- **Nodes**: positions where amplitude = 0 (no signal)
- **Antinodes**: positions where amplitude = 2 (maximum signal)

The perpendicular wave number is:
```
k⊥ = (2π / λ) · cos(θ)
```

### 3. AM-FSK Signal Encoding
Each character in the message is assigned a unique frequency tone and modulated with a carrier wave:
```
signal(t) = sin(2π · f_char · t) · sin(2π · f_carrier · t)
```

### 4. Demodulation & Low-Pass Filtering
The received signal is demodulated by multiplying with the local carrier replica and passing through a Butterworth low-pass filter to recover the original tone.

### 5. Caesar Cipher
Before transmission, the plaintext is encrypted by shifting each letter by a fixed number of positions in the alphabet:
```
encrypted_char = (original_position + shift) mod 26
```

---

## Requirements

- Python **3.8 or higher**
- The following Python libraries:

| Library | Purpose |
|---|---|
| `numpy` | Numerical calculations |
| `scipy` | Signal filtering (Butterworth low-pass) |
| `matplotlib` | Plotting all simulation panels |
| `tkinter` | GUI window (included with Python) |

---

## Installation

### Windows

**Step 1 — Check if Python is installed**

Open **Command Prompt** (press `Win + R`, type `cmd`, press Enter) and run:
```
python --version
```
If you see a version number (e.g. `Python 3.11.2`), you're good. If not, download Python from [https://www.python.org/downloads/](https://www.python.org/downloads/) — make sure to check **"Add Python to PATH"** during installation.

**Step 2 — Install the required libraries**
```
pip install numpy scipy matplotlib
```

**Step 3 — Clone the project**
```
git clone https://github.com/Clanker66/OEE-PROJECT-A2
cd OEE-PROJECT-A2
```

---

### Linux

**Step 1 — Check if Python is installed**

Open a terminal and run:
```bash
python3 --version
```
If not installed:
```bash
sudo apt update
sudo apt install python3 python3-pip
```

**Step 2 — Install tkinter** (often missing on Linux)
```bash
sudo apt install python3-tk
```

**Step 3 — Install the required libraries**
```bash
pip3 install numpy scipy matplotlib
```

**Step 4 — Clone the project**
```bash
git clone https://github.com/Clanker66/OEE-PROJECT-A2
cd OEE-PROJECT-A2
```

---

## How to Run

**Windows:**
```
python THEME4.py
```

**Linux:**
```
python3 THEME4.py
```

A window (1360×920) will open with the full simulation interface.

---

## How to Use the Simulation

### Step 1 — Enter a message
Type your plaintext in the **"Plain text"** field and click **"Encode & Send"**.  
Only letters (a–z, A–Z) are accepted.

### Step 2 — Set the Caesar shift
Use the **"Caesar shift"** slider (0–25) to choose the encryption shift.  
The encrypted version of your message is shown in real time.

### Step 3 — Adjust the signal parameters

| Control | What it does |
|---|---|
| **Carrier (Hz)** | Carrier frequency for AM modulation (500–8000 Hz) |
| **Burst (ms)** | Duration of each character's signal burst (1–30 ms) |
| **Angle θ (°)** | Reflection angle from the wall normal (0–89°) |

### Step 4 — Position the receiver
- Use the **"Receiver x (m)"** slider to move the receiver along the x-axis.
- Click **"⇒ Best position"** to jump automatically to the **first antinode** (strongest signal).
- The signal is decodable only when the amplitude **A ≥ 1.9**.

### Step 5 — Read the output
At the bottom of the window:
- **Received (enc):** — the encrypted message as received over the wave
- **→ Decrypted:** — the final decrypted plaintext (visible when signal is strong enough)

If the receiver is at a node, both fields show `?` characters until you move to an antinode.

### Zoom controls
Use the **"Zoom (m)"** slider to zoom into a region of the standing wave plot around the receiver position. Click **"Reset zoom"** to return to the full 0–10 m view.

---

## Understanding the Plots

| Panel | Description |
|---|---|
| **TX** | The transmitted AM-FSK signal — each character shown in a different color |
| **Reflection** | Geometric diagram of incident/reflected rays and wavefronts |
| **Standing wave** | Envelope, nodes, antinodes, and receiver position |
| **DFT** | Frequency spectrum of the demodulated signal |
| **Received & demodulated** | Time-domain signal as received at position x |
| **Stat panel** | Caesar cipher map, signal strength bar, and decode status |

---

## Example

1. Type `hello` in the plaintext field → click **Encode & Send**
2. Set shift to `3` → encrypted message becomes `khoor`
3. Set angle θ to `30°`
4. Click **⇒ Best position** → receiver jumps to first antinode
5. Bottom bar shows: `khoor` → `hello` ✔

**Thank you for your professional contribution!**
