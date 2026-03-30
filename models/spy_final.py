"""
Standing Wave Spy Decoder — v3
==============================
Fixes
-----
• Demodulated-signal bug: lowpass cutoff was fc×0.6, which is BELOW the FSK
  tone frequencies when fc is low (e.g. fc=2000 Hz → cutoff=1200 Hz, but 'e'
  tone = 1000 Hz is fine while 'z' = 5200 Hz gets cut).  Fix: cutoff is now
  max(tone_max × 1.5, 800) regardless of fc, and the demodulator removes the
  2fc image via a fixed cutoff of  min(max_tone × 1.5, FS/2 × 0.9).
• Independent per-character normalisation hid amplitude changes in RX plot.
  Now all characters share a common scale derived from the actual amplitude.
• Geometry panel: correct law-of-reflection diagram (angle of incidence =
  angle of reflection, both measured from the wall normal; wavefronts drawn).

New features
------------
• Precise numeric entry field next to every slider (click → type → Enter).
• Caesar cipher: shift slider + cipher map table + encrypted/decrypted display.
• Geometry panel redrawn with proper normal, equal angles, wavefronts.
"""

import tkinter as tk
from tkinter import ttk
import numpy as np
import math
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from scipy.signal import butter, filtfilt

# ── constants ──────────────────────────────────────────────────────────────────
FS          = 44100
MAX_X       = 10.0
THRESHOLD   = 1.9
LAMBDA_SCALE = 1.0          # effective λ = 1 m so antinodes are visible

LETTERS = "abcdefghijklmnopqrstuvwxyz"

COLORS = ["#7F77DD","#D85A30","#1D9E75","#378ADD","#D4537E",
          "#639922","#BA7517","#185FA5","#993C1D","#3B6D11"]

# ── frequency map: every letter gets a unique tone ────────────────────────────
def _make_alpha():
    d = {}
    for i, c in enumerate(LETTERS):
        d[c] = 300 + i * 100          # a=300 … z=2800 Hz  (well below FS/2)
    for i, c in enumerate(LETTERS.upper()):
        d[c] = 300 + i * 100 + 50     # upper-case offset +50 Hz
    return d

ALPHA = _make_alpha()

def fof(c):
    return ALPHA.get(c, 400)

MAX_TONE = max(ALPHA.values())        # 2850 Hz
LPF_CUT  = min(MAX_TONE * 1.6, FS / 2 * 0.9)   # lowpass after demod


# ── Caesar cipher ─────────────────────────────────────────────────────────────
def caesar_encrypt(text, shift):
    out = []
    for c in text:
        if c in LETTERS:
            out.append(LETTERS[(LETTERS.index(c) + shift) % 26])
        elif c in LETTERS.upper():
            lo = c.lower()
            out.append(LETTERS[(LETTERS.index(lo) + shift) % 26].upper())
        else:
            out.append(c)
    return "".join(out)

def caesar_decrypt(text, shift):
    return caesar_encrypt(text, -shift)


# ── DSP helpers ────────────────────────────────────────────────────────────────
def lowpass(sig, cut, order=4):
    nyq = FS / 2
    cut = max(10.0, min(cut, nyq * 0.98))
    b, a = butter(order, cut / nyq, btype="low")
    return filtfilt(b, a, sig)

def k_perp(theta_deg):
    k0 = 2 * math.pi / LAMBDA_SCALE
    return k0 * math.cos(math.radians(theta_deg))

def sw_amp(x, theta_deg):
    kp = k_perp(theta_deg)
    return abs(2.0 * math.sin(kp * x))

def sw_envelope(x_arr, theta_deg):
    kp = k_perp(theta_deg)
    return 2.0 * np.abs(np.sin(kp * x_arr))

def antinodes_list(theta_deg, x_min=0.0, x_max=MAX_X):
    kp = k_perp(theta_deg)
    if kp <= 0:
        return []
    pos, n = [], 0
    while True:
        x = (2 * n + 1) * math.pi / (2 * kp)
        if x > x_max:
            break
        if x >= x_min:
            pos.append(x)
        n += 1
    return pos

def first_antinode(theta_deg):
    nodes = antinodes_list(theta_deg)
    return nodes[0] if nodes else 0.0

def make_burst(char, fc, dur_ms):
    """AM-FSK burst: tone × carrier, dur_ms milliseconds."""
    n  = max(8, int(FS * dur_ms / 1000))
    t  = np.arange(n) / FS
    return np.sin(2 * math.pi * fof(char) * t) * np.sin(2 * math.pi * fc * t)

def demodulate(burst, amp, fc):
    """
    Multiply received signal by local carrier replica, then lowpass.
    burst × amp × sin(2πfc t)  →  lowpass  →  ½·amp·tone(t)
    Cutoff is fixed at LPF_CUT (covers all FSK tones) regardless of fc.
    """
    t     = np.arange(len(burst)) / FS
    mixed = burst * amp * np.sin(2 * math.pi * fc * t)
    return lowpass(mixed, LPF_CUT)


# ── slider + entry helper ──────────────────────────────────────────────────────
def make_slider_entry(parent, label, var, from_, to, length,
                      on_change, fmt="{:.1f}", bg="#f2f2f2", fg="#222",
                      entry_width=7):
    """
    Packs:  Label | Scale | Entry
    The entry is kept in sync with the slider; pressing Enter commits the value.
    Returns the Scale and Entry widgets.
    """
    tk.Label(parent, text=label, bg=bg, font=("Helvetica", 10)).pack(side=tk.LEFT)

    scale = ttk.Scale(parent, from_=from_, to=to, variable=var,
                      orient=tk.HORIZONTAL, length=length,
                      command=lambda v: _scale_cb(v, var, entry_sv, fmt, on_change))
    scale.pack(side=tk.LEFT, padx=2)

    entry_sv = tk.StringVar(value=fmt.format(var.get()))
    entry = tk.Entry(parent, textvariable=entry_sv,
                     font=("Helvetica", 9), width=entry_width,
                     bg="#fff", relief=tk.SUNKEN)
    entry.pack(side=tk.LEFT, padx=(0, 6))

    def commit(event=None):
        try:
            v = float(entry_sv.get())
            v = max(from_, min(to, v))
            var.set(v)
            entry_sv.set(fmt.format(v))
            on_change(str(v))
        except ValueError:
            entry_sv.set(fmt.format(var.get()))

    entry.bind("<Return>", commit)
    entry.bind("<FocusOut>", commit)
    return scale, entry

def _scale_cb(val, var, entry_sv, fmt, on_change):
    try:
        entry_sv.set(fmt.format(float(val)))
    except Exception:
        pass
    on_change(val)


# ══════════════════════════════════════════════════════════════════════════════
class App:
    def __init__(self, root):
        self.root    = root
        self.root.title("Standing Wave Spy Decoder  v3")
        self.root.configure(bg="#f2f2f2")

        self.plaintext  = "signal"      # what the user types
        self.shift      = 3            # Caesar shift
        self.encrypted  = caesar_encrypt(self.plaintext, self.shift)
        # The ENCRYPTED text is what gets transmitted over the air
        self.message    = self.encrypted

        self.theta      = 0.0
        self.ix         = 0.0
        self.fc         = 6000.0
        self.dur_ms     = 10.0
        self.zoom_x0    = 0.0
        self.zoom_x1    = MAX_X
        self._after     = None

        self._build_ui()
        self._redraw()

    # ══════════════════════════════════════════════════════════════════════════
    # UI
    # ══════════════════════════════════════════════════════════════════════════
    def _build_ui(self):
        BG = "#f2f2f2"

        # ── ROW 1: message / cipher ───────────────────────────────────────────
        r1 = tk.Frame(self.root, bg=BG, pady=3)
        r1.pack(fill=tk.X, padx=10)

        tk.Label(r1, text="Plain text:", bg=BG,
                 font=("Helvetica", 11)).pack(side=tk.LEFT)
        self.msg_var = tk.StringVar(value=self.plaintext)
        tk.Entry(r1, textvariable=self.msg_var,
                 font=("Helvetica", 11), width=14).pack(side=tk.LEFT, padx=3)
        tk.Button(r1, text="Encode & Send", command=self._on_encode,
                  font=("Helvetica", 10), relief=tk.FLAT,
                  bg="#7F77DD", fg="white", padx=8).pack(side=tk.LEFT, padx=4)

        # Caesar shift
        tk.Label(r1, text="  Caesar shift:", bg=BG,
                 font=("Helvetica", 10)).pack(side=tk.LEFT)
        self.shift_var = tk.IntVar(value=self.shift)
        self.shift_scale = ttk.Scale(r1, from_=0, to=25,
                                     variable=self.shift_var,
                                     orient=tk.HORIZONTAL, length=110,
                                     command=self._on_shift)
        self.shift_scale.pack(side=tk.LEFT, padx=2)
        self.shift_entry_sv = tk.StringVar(value=str(self.shift))
        shift_entry = tk.Entry(r1, textvariable=self.shift_entry_sv,
                               font=("Helvetica", 9), width=4,
                               bg="#fff", relief=tk.SUNKEN)
        shift_entry.pack(side=tk.LEFT, padx=(0, 4))
        shift_entry.bind("<Return>",   self._commit_shift)
        shift_entry.bind("<FocusOut>", self._commit_shift)

        # encrypted / decrypted labels
        self.enc_var = tk.StringVar(value=f"Encrypted: {self.encrypted}")
        tk.Label(r1, textvariable=self.enc_var, bg=BG,
                 font=("Courier", 10, "bold"), fg="#D85A30").pack(side=tk.LEFT, padx=8)

        # ── ROW 2: carrier + burst + angle ───────────────────────────────────
        r2 = tk.Frame(self.root, bg=BG, pady=2)
        r2.pack(fill=tk.X, padx=10)

        self.fc_var  = tk.DoubleVar(value=self.fc)
        self.dur_var = tk.DoubleVar(value=self.dur_ms)
        self.th_var  = tk.DoubleVar(value=self.theta)

        make_slider_entry(r2, "Carrier (Hz):", self.fc_var,
                          500, 8000, 120, self._on_fc, "{:.0f}")
        make_slider_entry(r2, "Burst (ms):", self.dur_var,
                          1, 30, 90, self._on_dur, "{:.0f}")
        make_slider_entry(r2, "Angle θ (°):", self.th_var,
                          0, 89, 110, self._on_theta, "{:.1f}")

        self.legend = tk.Label(r2, text="", bg=BG,
                               font=("Helvetica", 8), fg="#555")
        self.legend.pack(side=tk.LEFT, padx=4)

        # ── ROW 3: receiver + zoom ────────────────────────────────────────────
        r3 = tk.Frame(self.root, bg=BG, pady=2)
        r3.pack(fill=tk.X, padx=10)

        self.x_var    = tk.DoubleVar(value=0.0)
        self.zoom_var = tk.DoubleVar(value=MAX_X)

        make_slider_entry(r3, "Receiver x (m):", self.x_var,
                          0, MAX_X, 300, self._on_x, "{:.4f}", entry_width=8)

        tk.Button(r3, text="⇒ Best position",
                  command=self._best, font=("Helvetica", 10),
                  relief=tk.FLAT, bg="#1D9E75",
                  fg="white", padx=8).pack(side=tk.LEFT, padx=4)

        make_slider_entry(r3, "  Zoom (m):", self.zoom_var,
                          0.01, MAX_X, 130, self._on_zoom, "{:.3f}")

        tk.Button(r3, text="Reset zoom",
                  command=self._reset_zoom, font=("Helvetica", 10),
                  relief=tk.FLAT, bg="#888", fg="white",
                  padx=6).pack(side=tk.LEFT, padx=4)

        # hint bar
        self.hint = tk.StringVar(value="")
        tk.Label(self.root, textvariable=self.hint, bg=BG,
                 font=("Helvetica", 8), fg="#666",
                 anchor="w").pack(fill=tk.X, padx=12)

        # ── matplotlib 3×3 figure ─────────────────────────────────────────────
        self.fig = Figure(figsize=(15, 7.2), dpi=88, facecolor="#f8f8f8")
        self.fig.subplots_adjust(left=0.05, right=0.99, top=0.93,
                                 bottom=0.08, hspace=0.62, wspace=0.28)

        self.ax_tx    = self.fig.add_subplot(3, 3, (1, 2))
        self.ax_geom  = self.fig.add_subplot(3, 3, 3)
        self.ax_sw    = self.fig.add_subplot(3, 3, (4, 5))
        self.ax_dft   = self.fig.add_subplot(3, 3, 6)
        self.ax_rx    = self.fig.add_subplot(3, 3, (7, 8))
        self.ax_stat  = self.fig.add_subplot(3, 3, 9)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=6, pady=2)

        # ── decoded / cipher bottom bar ───────────────────────────────────────
        bot = tk.Frame(self.root, bg="#EEEDFE", pady=4)
        bot.pack(fill=tk.X, padx=10, pady=3)

        tk.Label(bot, text="Received (enc):", bg="#EEEDFE",
                 font=("Helvetica", 11), fg="#3C3489").pack(side=tk.LEFT, padx=6)
        self.dec_var = tk.StringVar(value="")
        self.dec_lbl = tk.Label(bot, textvariable=self.dec_var,
                                bg="#EEEDFE", font=("Courier", 13, "bold"),
                                fg="#D85A30")
        self.dec_lbl.pack(side=tk.LEFT)

        tk.Label(bot, text="  →  Decrypted:", bg="#EEEDFE",
                 font=("Helvetica", 11), fg="#3C3489").pack(side=tk.LEFT, padx=6)
        self.plain_var = tk.StringVar(value="")
        self.plain_lbl = tk.Label(bot, textvariable=self.plain_var,
                                  bg="#EEEDFE", font=("Courier", 13, "bold"),
                                  fg="#085041")
        self.plain_lbl.pack(side=tk.LEFT)

        self.res_var = tk.StringVar(value="")
        tk.Label(bot, textvariable=self.res_var, bg="#EEEDFE",
                 font=("Helvetica", 10), fg="#555").pack(side=tk.LEFT, padx=14)

    # ══════════════════════════════════════════════════════════════════════════
    # Event handlers
    # ══════════════════════════════════════════════════════════════════════════
    def _on_encode(self):
        raw = self.msg_var.get().strip()
        self.plaintext = "".join(c for c in raw if c.lower() in LETTERS) or "hello"
        self.msg_var.set(self.plaintext)
        self._refresh_cipher()
        self.x_var.set(0); self.ix = 0.0
        self._redraw()

    def _on_shift(self, val):
        self.shift = int(round(float(val)))
        self.shift_var.set(self.shift)
        self.shift_entry_sv.set(str(self.shift))
        self._refresh_cipher()
        self._schedule()

    def _commit_shift(self, event=None):
        try:
            v = int(round(float(self.shift_entry_sv.get())))
            v = max(0, min(25, v))
            self.shift = v
            self.shift_var.set(v)
            self.shift_entry_sv.set(str(v))
            self._refresh_cipher()
            self._schedule()
        except ValueError:
            self.shift_entry_sv.set(str(self.shift))

    def _refresh_cipher(self):
        self.encrypted = caesar_encrypt(self.plaintext, self.shift)
        self.message   = self.encrypted
        self.enc_var.set(f"Encrypted: {self.encrypted}  (shift={self.shift})")

    def _on_fc(self, val):
        self.fc = float(val)
        self._schedule()

    def _on_dur(self, val):
        self.dur_ms = float(val)
        self._schedule()

    def _on_theta(self, val):
        self.theta = float(val)
        self._schedule()

    def _on_x(self, val):
        self.ix = float(val)
        self._schedule()

    def _on_zoom(self, val):
        w    = max(float(val), 1e-4)
        half = w / 2
        self.zoom_x0 = max(0.0, self.ix - half)
        self.zoom_x1 = min(MAX_X, self.ix + half)
        if self.zoom_x1 - self.zoom_x0 < w * 0.9:
            self.zoom_x0 = 0.0 if self.zoom_x0 == 0.0 else max(0.0, MAX_X - w)
            self.zoom_x1 = min(MAX_X, self.zoom_x0 + w)
        self._schedule()

    def _reset_zoom(self):
        self.zoom_x0 = 0.0
        self.zoom_x1 = MAX_X
        self.zoom_var.set(MAX_X)
        self._schedule()

    def _best(self):
        bx = first_antinode(self.theta)
        self.x_var.set(bx)
        self.ix = bx
        kp  = k_perp(self.theta)
        lam = 2 * math.pi / kp if kp > 0 else float("inf")
        w   = max(lam * 3, 0.1)
        self.zoom_var.set(w)
        self._on_zoom(w)
        self._redraw()

    def _schedule(self):
        if self._after:
            self.root.after_cancel(self._after)
        self._after = self.root.after(30, self._redraw)

    # ══════════════════════════════════════════════════════════════════════════
    # Drawing
    # ══════════════════════════════════════════════════════════════════════════
    def _redraw(self):
        self._after = None
        unique = list(dict.fromkeys(self.message))
        cmap   = {c: COLORS[i % len(COLORS)] for i, c in enumerate(unique)}
        self._draw_tx(unique, cmap)
        self._draw_geom()
        self._draw_sw()
        self._draw_dft(unique, cmap)
        self._draw_rx(unique, cmap)
        self._draw_stat(unique, cmap)
        self._update_bot()
        self._draw_cipher_legend()
        self.canvas.draw_idle()

    # ── TX ────────────────────────────────────────────────────────────────────
    def _draw_tx(self, unique, cmap):
        ax = self.ax_tx; ax.cla()
        offset = 0.0
        for c in self.message:
            burst = make_burst(c, self.fc, self.dur_ms)
            n     = len(burst)
            t     = np.arange(n) / FS
            ax.plot((t + offset) * 1000, burst,
                    color=cmap[c], lw=0.7, alpha=0.85)
            mid = (offset + n / FS / 2) * 1000
            ax.text(mid, 1.18, f"'{c}'", ha="center", fontsize=6, color=cmap[c])
            offset += n / FS
        ax.axhline(0, color="#ccc", lw=0.4)
        ax.set_ylim(-1.45, 1.45)
        ax.set_title(
            f"TX  — encrypted message '{self.message}'  |  "
            f"fc={self.fc:.0f} Hz  burst={self.dur_ms:.0f} ms/char",
            fontsize=8)
        ax.set_xlabel("Time (ms)", fontsize=7)
        ax.set_ylabel("AM-FSK", fontsize=7)
        ax.tick_params(labelsize=6)

    # ── geometry ──────────────────────────────────────────────────────────────
    def _draw_geom(self):
        """
        Correct law-of-reflection diagram.
        Wall is vertical at x=0.  Normal is horizontal (→).
        Angle θ is measured from the normal on both sides.
        Incident ray comes from bottom-left; reflected ray goes to top-left.
        Wavefronts (perpendicular to ray directions) are drawn as short lines.
        """
        ax = self.ax_geom; ax.cla()
        ax.set_xlim(-3.0, 0.8)
        ax.set_ylim(-0.5, 3.2)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(f"Reflection  θ={self.theta:.1f}°", fontsize=9)

        # metal wall
        ax.fill_betweenx([0, 3.0], 0, 0.5, color="#aaa", alpha=0.35)
        ax.plot([0, 0], [0, 3.0], color="#555", lw=4)
        ax.text(0.08, 3.05, "Metal wall", fontsize=7.5, color="#333")

        th  = math.radians(self.theta)
        cos = math.cos(th)
        sin = math.sin(th)

        # normal (dashed horizontal line through reflection point P)
        P = (0.0, 1.5)
        ax.plot([-2.5, 0.5], [P[1], P[1]], color="#999", lw=0.9,
                ls="--", zorder=1)
        ax.text(0.12, P[1] + 0.05, "Normal", fontsize=6.5, color="#777")

        # Ray directions (unit vectors, axes coords):
        #   incident  travels (+cosθ, +sinθ) → hits wall from bottom-left
        #   reflected travels (-cosθ, +sinθ) → leaves wall toward top-left
        # Both make angle θ with the horizontal normal. ✓ law of reflection.
        #
        # Length is clamped independently per ray so neither arrow ever exits
        # the visible area regardless of θ (fixes disappearance at θ > 45°).
        x_left = -2.6   # left boundary
        y_bot  =  0.1   # bottom boundary (leave room for RX marker)
        y_top  =  3.0   # top boundary

        # incident: origin = P - L_inc*(cosθ, sinθ), clamped to visible area
        t_x_inc = (P[0] - x_left) / cos if cos > 1e-6 else 99.0
        t_y_inc = (P[1] - y_bot)  / sin if sin > 1e-6 else 99.0
        L_inc = min(t_x_inc, t_y_inc, 2.4)
        ix0 = P[0] - L_inc * cos
        iy0 = P[1] - L_inc * sin

        ax.annotate("", xy=P, xytext=(ix0, iy0),
                    arrowprops=dict(arrowstyle="-|>", color="#378ADD",
                                   lw=2.0, mutation_scale=12))
        ax.text((ix0 + P[0]) / 2 - 0.12, (iy0 + P[1]) / 2 - 0.20,
                "Incident", fontsize=7, color="#378ADD", ha="center")

        # reflected: endpoint = P + L_ref*(-cosθ, +sinθ), clamped to visible area
        t_x_ref = (P[0] - x_left) / cos if cos > 1e-6 else 99.0
        t_y_ref = (y_top - P[1])  / sin if sin > 1e-6 else 99.0
        L_ref = min(t_x_ref, t_y_ref, 2.4)
        rx1 = P[0] - L_ref * cos
        ry1 = P[1] + L_ref * sin

        ax.annotate("", xy=(rx1, ry1), xytext=P,
                    arrowprops=dict(arrowstyle="-|>", color="#D85A30",
                                   lw=2.0, mutation_scale=12))
        ax.text((rx1 + P[0]) / 2 - 0.12, (ry1 + P[1]) / 2 + 0.12,
                "Reflected", fontsize=7, color="#D85A30", ha="center")

        # angle arcs
        if self.theta > 1:
            # angle of incidence arc (below normal, on incident side)
            arc1 = np.linspace(math.pi, math.pi + th, 40)
            ax.plot(P[0] + 0.5 * np.cos(arc1),
                    P[1] + 0.5 * np.sin(arc1),
                    color="#378ADD", lw=1.2)
            ax.text(P[0] - 0.68, P[1] - 0.18,
                    f"θ={self.theta:.0f}°", fontsize=7, color="#378ADD")

            # angle of reflection arc (above normal, on reflected side)
            arc2 = np.linspace(math.pi - th, math.pi, 40)
            ax.plot(P[0] + 0.5 * np.cos(arc2),
                    P[1] + 0.5 * np.sin(arc2),
                    color="#D85A30", lw=1.2)
            ax.text(P[0] - 0.68, P[1] + 0.10,
                    f"θ={self.theta:.0f}°", fontsize=7, color="#D85A30")

        # wavefronts (perpendicular to ray, equally spaced along ray)
        wf_perp_inc = np.array([-sin,  cos])   # perpendicular to incident dir
        wf_perp_ref = np.array([-sin, -cos])   # perpendicular to reflected dir
        wf_half = 0.22
        for frac in [0.30, 0.60, 0.85]:
            # incident wavefronts
            cx = ix0 + frac * (P[0] - ix0)
            cy = iy0 + frac * (P[1] - iy0)
            ax.plot([cx - wf_half * wf_perp_inc[0],
                     cx + wf_half * wf_perp_inc[0]],
                    [cy - wf_half * wf_perp_inc[1],
                     cy + wf_half * wf_perp_inc[1]],
                    color="#378ADD", lw=1.2, alpha=0.7)
            # reflected wavefronts
            cx2 = P[0] + frac * (rx1 - P[0])
            cy2 = P[1] + frac * (ry1 - P[1])
            ax.plot([cx2 - wf_half * wf_perp_ref[0],
                     cx2 + wf_half * wf_perp_ref[0]],
                    [cy2 - wf_half * wf_perp_ref[1],
                     cy2 + wf_half * wf_perp_ref[1]],
                    color="#D85A30", lw=1.2, alpha=0.7)

        # receiver dot
        ix_vis = min(self.ix / MAX_X * 2.0, 2.0)
        rx_pos = (-ix_vis, P[1] - 0.55)
        ax.scatter([rx_pos[0]], [rx_pos[1]],
                   color="#1D9E75", zorder=6, s=80, marker="^")
        ax.text(rx_pos[0], rx_pos[1] - 0.22,
                f"RX\n{self.ix:.3f} m", ha="center", fontsize=6.5,
                color="#085041")
        if ix_vis > 0.08:
            ax.annotate("", xy=(0, rx_pos[1] - 0.08),
                        xytext=(rx_pos[0], rx_pos[1] - 0.08),
                        arrowprops=dict(arrowstyle="<->", color="#1D9E75", lw=1.2))
            ax.text(rx_pos[0] / 2, rx_pos[1] - 0.22,
                    f"{self.ix:.3f} m", ha="center", fontsize=6.5,
                    color="#085041")

        # λ info
        kp = k_perp(self.theta)
        if kp > 0:
            lam = 2 * math.pi / kp
            ax.text(-1.2, -0.3,
                    f"λ_eff = {lam:.3f} m  |  antinodes every {lam/2:.3f} m",
                    fontsize=6, color="#3C3489", ha="center")

    # ── standing wave ─────────────────────────────────────────────────────────
    def _draw_sw(self):
        ax = self.ax_sw; ax.cla()
        x0 = self.zoom_x0
        x1 = max(self.zoom_x1, x0 + 1e-6)
        x  = np.linspace(x0 + 1e-9, x1, 2000)
        kp = k_perp(self.theta)

        if kp <= 0:
            ax.text(0.5, 0.5, "θ = 90°: no perpendicular component",
                    transform=ax.transAxes, ha="center", va="center",
                    fontsize=9, color="#888")
        else:
            # standing wave = incident + reflected with π phase flip at wall
            inc  =  np.sin(kp * (x))       # e^{-jkx}  travelling toward wall
            refl = -np.sin(kp * (x))       # total reflection → π flip + e^{+jkx}
            # proper standing wave with time snapshot t=0:
            # E(x,t) = 2sin(kx)cos(ωt)  →  at t=0: E = 2sin(kx)
            standing = 2 * np.sin(kp * x)
            env      = sw_envelope(x, self.theta)

            ax.plot(x, inc,      color="#378ADD", lw=0.8, ls="--",
                    alpha=0.4, label="Incident →")
            ax.plot(x, -inc,     color="#D85A30", lw=0.8, ls="--",
                    alpha=0.4, label="← Reflected")
            ax.plot(x, standing, color="#9955CC", lw=1.2, alpha=0.55,
                    label="Standing (t=0)")
            ax.plot(x,  env,     color="#7F77DD", lw=2.2,
                    label="Envelope  2|sin(k⊥x)|")
            ax.plot(x, -env,     color="#7F77DD", lw=2.2)
            ax.fill_between(x, -env, env, alpha=0.07, color="#7F77DD")
            ax.axhline(0, color="#ccc", lw=0.4)

            # antinodes
            for nx in antinodes_list(self.theta, x0, x1):
                ax.axvline(nx, color="#D85A30", lw=0.8, ls=":", alpha=0.65)
                ax.text(nx, 2.08, f"{nx:.3f}m",
                        fontsize=5.5, color="#993C1D",
                        ha="center", rotation=90, va="bottom")

            # receiver
            if x0 <= self.ix <= x1:
                a = sw_amp(self.ix, self.theta)
                ax.axvline(self.ix, color="#1D9E75", lw=2.5, zorder=5)
                ax.scatter([self.ix], [a], color="#1D9E75", zorder=6, s=65)
                ax.text(self.ix + (x1 - x0) * 0.015, a + 0.12,
                        f"A={a:.3f}", fontsize=8, color="#085041")

        ax.set_xlim(x0, x1)
        ax.set_ylim(-2.4, 2.5)
        zoom_info = (f"{x0:.3f}–{x1:.3f} m"
                     if (x1 - x0) < MAX_X * 0.99 else "full 0–10 m")
        ax.set_title(
            f"Standing wave  θ={self.theta:.1f}°  [{zoom_info}]",
            fontsize=8)
        ax.set_xlabel("Distance from wall x (m)", fontsize=7)
        ax.set_ylabel("Amplitude", fontsize=7)
        ax.legend(fontsize=6, loc="upper right", ncol=2)
        ax.tick_params(labelsize=6)

    # ── DFT ──────────────────────────────────────────────────────────────────
    def _draw_dft(self, unique, cmap):
        ax = self.ax_dft; ax.cla()
        a  = sw_amp(self.ix, self.theta)
        for c in unique:
            burst    = make_burst(c, self.fc, self.dur_ms)
            filtered = demodulate(burst, a, self.fc)
            freqs    = np.fft.rfftfreq(len(filtered), d=1 / FS)
            mag      = np.abs(np.fft.rfft(filtered))
            mask     = freqs <= LPF_CUT * 1.1
            if mask.any():
                ax.plot(freqs[mask], mag[mask],
                        color=cmap[c], lw=1.3, alpha=0.85,
                        label=f"'{c}' {fof(c)}Hz")
                pidx = int(np.argmax(mag[mask]))
                ax.axvline(freqs[mask][pidx], color=cmap[c],
                           lw=0.8, ls=":", alpha=0.7)
        ax.set_title(f"DFT of demodulated  (LPF cut={LPF_CUT:.0f}Hz)",
                     fontsize=8)
        ax.set_xlabel("Frequency (Hz)", fontsize=7)
        ax.set_ylabel("Magnitude", fontsize=7)
        ax.legend(fontsize=5.5, loc="upper right", ncol=2)
        ax.tick_params(labelsize=6)

    # ── RX ───────────────────────────────────────────────────────────────────
    def _draw_rx(self, unique, cmap):
        """
        All characters share a GLOBAL scale so amplitude changes are visible.
        When receiver is near a node (A≈0) the plot is nearly flat — correctly.
        """
        ax = self.ax_rx; ax.cla()
        a  = sw_amp(self.ix, self.theta)

        # first pass: find global max across all characters
        all_demod = {}
        for c in self.message:
            burst = make_burst(c, self.fc, self.dur_ms)
            all_demod[c] = demodulate(burst, a, self.fc)

        # global normalisation (use amplitude at best position for reference)
        a_ref  = 2.0          # maximum possible amplitude
        ref_burst  = make_burst(self.message[0], self.fc, self.dur_ms)
        ref_demod  = demodulate(ref_burst, a_ref, self.fc)
        global_max = max(np.max(np.abs(ref_demod)), 1e-9)

        offset = 0.0
        for c in self.message:
            sig = all_demod[c]
            n   = len(sig)
            t   = np.arange(n) / FS
            ax.plot((t + offset) * 1000, sig / global_max,
                    color=cmap[c], lw=0.9)
            offset += n / FS

        ax.axhline(0, color="#ccc", lw=0.4)
        ax.axhline( THRESHOLD / 2, color="#1D9E75", lw=0.8,
                   ls="--", alpha=0.5, label=f"Decode threshold (A≥{THRESHOLD})")
        ax.axhline(-THRESHOLD / 2, color="#1D9E75", lw=0.8, ls="--", alpha=0.5)
        ax.set_ylim(-1.3, 1.45)
        ax.set_title(
            f"Received & demodulated  (A={a:.3f}/2.000 at x={self.ix:.4f} m)",
            fontsize=8)
        ax.set_xlabel("Time (ms)", fontsize=7)
        ax.set_ylabel("Amplitude (normalised to A=2)", fontsize=7)
        ax.legend(fontsize=6, loc="upper right")
        ax.tick_params(labelsize=6)

    # ── stat panel ────────────────────────────────────────────────────────────
    def _draw_stat(self, unique, cmap):
        ax = self.ax_stat; ax.cla(); ax.axis("off")
        a    = sw_amp(self.ix, self.theta)
        ok   = a >= THRESHOLD

        # Caesar cipher map (top section)
        ax.text(0.5, 0.99, f"Caesar shift = {self.shift}",
                transform=ax.transAxes, fontsize=8, fontweight="bold",
                color="#3C3489", ha="center", va="top")

        # show mapping for each unique character in message
        y = 0.91
        for c in sorted(set(self.plaintext)):
            enc_c = caesar_encrypt(c, self.shift)
            col   = cmap.get(enc_c, "#555")
            ax.text(0.05, y,
                    f"'{c}' → '{enc_c}'  ({fof(enc_c)} Hz)",
                    transform=ax.transAxes, fontsize=7,
                    color=col, va="top", family="monospace")
            y -= 0.085
            if y < 0.45:
                ax.text(0.05, y, "…", transform=ax.transAxes,
                        fontsize=7, color="#888")
                y -= 0.085
                break

        # separator
        ax.plot([0, 1], [y + 0.03, y + 0.03], color="#ccc", lw=0.5,
                transform=ax.transAxes, clip_on=False)

        # signal quality
        bar_n = int(a / 2 * 14)
        bar   = "█" * bar_n + "░" * (14 - bar_n)
        ax.text(0.5, y - 0.02,
                f"Signal A={a:.3f}  {'✔ DECODE OK' if ok else '✘ weak'}",
                transform=ax.transAxes, fontsize=8, fontweight="bold",
                color="#085041" if ok else "#993C1D",
                ha="center", va="top")
        ax.text(0.5, y - 0.10,
                bar, transform=ax.transAxes, fontsize=7,
                color="#1D9E75" if ok else "#aaa",
                ha="center", va="top", family="monospace")

    # ── cipher legend below figure ────────────────────────────────────────────
    def _draw_cipher_legend(self):
        parts = []
        for c in sorted(set(self.plaintext)):
            enc = caesar_encrypt(c, self.shift)
            parts.append(f"{c}→{enc}")
        self.legend.config(text="  Cipher: " + "  ".join(parts))

    # ── bottom bar ────────────────────────────────────────────────────────────
    def _update_bot(self):
        a   = sw_amp(self.ix, self.theta)
        ok  = a >= THRESHOLD

        # what we receive over the air (encrypted, possibly garbled)
        enc_received = "".join(c if ok else "?" for c in self.message)
        # decrypt it
        dec_received = "".join(
            (caesar_decrypt(c, self.shift) if ok and c in ALPHA else
             ("?" if not ok else c))
            for c in self.message
        )

        self.dec_var.set(enc_received)
        self.plain_var.set(dec_received)

        if ok:
            self.res_var.set(
                f"  A={a:.3f}  x={self.ix:.4f}m  — full decode ✔")
            self.dec_lbl.config(fg="#D85A30")
            self.plain_lbl.config(fg="#085041")
        else:
            self.res_var.set(
                f"  A={a:.3f}  — move receiver to an antinode (need ≥{THRESHOLD})")
            self.dec_lbl.config(fg="#aaa")
            self.plain_lbl.config(fg="#aaa")

        kp    = k_perp(self.theta)
        nodes = antinodes_list(self.theta)
        ns    = ", ".join(f"{n:.3f}m" for n in nodes[:5])
        self.hint.set(
            f"x={self.ix:.4f}m  θ={self.theta:.1f}°  fc={self.fc:.0f}Hz  "
            f"A={a:.3f}/2.000  LPF={LPF_CUT:.0f}Hz  |  antinodes: {ns}"
        )


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1360x920")
    App(root)
    root.mainloop()
