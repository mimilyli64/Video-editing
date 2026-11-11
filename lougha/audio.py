"""Original music (100 BPM, D major), the Lougha sonic identity, ~120 synthesized
sound cues locked to the picture, and the final mix.

  python3 -m lougha.audio     -> build/music.wav, build/sfx.wav, out/mix.wav, out/cue_sheet.csv

Mix targets: voice ~ -16 LUFS, music >= 12 dB under every spoken word,
master -14 LUFS integrated / -1.25 dBTP.
"""
import csv
import json
import math
import os
import subprocess

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter, sosfilt, fftconvolve

from . import config as C

SR = 48000
N = int(C.DUR * SR) + SR // 2
BPM = 100
BEAT = 60 / BPM          # 0.6 s
BAR = 4 * BEAT
RNG = np.random.RandomState(1234)
WT = C.word_times()


def mf(m):
    return 440.0 * 2 ** ((m - 69) / 12)


NOTE = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}


def m(name):
    p, o = name[:-1], int(name[-1])
    return 12 * (o + 1) + NOTE[p]


def tt(n):
    return np.arange(int(n)) / SR


def env_exp(n, decay, attack=0.004):
    t = tt(n)
    a = np.minimum(1, t / max(attack, 1e-4))
    return a * np.exp(-t * decay)


def bp(x, lo, hi, order=2):
    sos = butter(order, [lo / (SR / 2), min(hi / (SR / 2), 0.99)], btype="band", output="sos")
    return sosfilt(sos, x)


def lp(x, f, order=2):
    return sosfilt(butter(order, min(f / (SR / 2), 0.99), output="sos"), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f / (SR / 2), btype="high", output="sos"), x)


class Bus:
    def __init__(self):
        self.L = np.zeros(N, np.float64)
        self.R = np.zeros(N, np.float64)

    def add(self, t, sig, gain=1.0, pan=0.0):
        i = int(t * SR)
        if i >= N or len(sig) == 0:
            return
        if i < 0:
            sig = sig[-i:]
            i = 0
        j = min(N, i + len(sig))
        s = sig[:j - i] * gain
        lg = math.cos((pan + 1) * math.pi / 4)
        rg = math.sin((pan + 1) * math.pi / 4)
        self.L[i:j] += s * lg * 1.414
        self.R[i:j] += s * rg * 1.414

    def st(self):
        return np.stack([self.L, self.R], 1)


# ======================================================================= instruments
def mixa(*xs):
    n = max(len(x) for x in xs)
    out = np.zeros(n)
    for x in xs:
        out[:len(x)] += x
    return out


def mallet(f, dur=1.2, bright=1.0):
    n = int(dur * SR)
    t = tt(n)
    mod = np.sin(2 * np.pi * f * 3.5 * t) * 0.6 * np.exp(-t * 30) * bright
    s = np.sin(2 * np.pi * f * t + mod) * env_exp(n, 4.5, 0.002)
    s += 0.35 * np.sin(2 * np.pi * f * 3.99 * t) * env_exp(n, 14, 0.001) * bright
    s += 0.15 * np.sin(2 * np.pi * f * 9.2 * t) * env_exp(n, 40, 0.001) * bright
    return s * 0.5


def felt(f, dur=2.4, vel=1.0):
    n = int(dur * SR)
    t = tt(n)
    s = np.zeros(n)
    for h in range(1, 8):
        det = 1 + 0.0007 * h * h
        s += np.sin(2 * np.pi * f * h * det * t) / h ** 1.7 * np.exp(-t * (1.6 + 0.9 * h))
    s *= np.minimum(1, t / 0.008)
    thump = lp(RNG.randn(n), 600) * np.exp(-t * 60) * 0.08
    s = lp(s + thump, 2400 + 1800 * vel)
    rel = np.minimum(1, (dur - t) / 0.25)
    return s * rel * 0.35 * vel


def sub(f, dur, attack=0.02, decay=0.8):
    n = int(dur * SR)
    t = tt(n)
    s = np.sin(2 * np.pi * f * t) + 0.12 * np.sin(4 * np.pi * f * t)
    e = np.minimum(1, t / attack) * np.exp(-t * decay) * np.minimum(1, (dur - t) / 0.08)
    return s * e * 0.6


def kick(v=1.0):
    n = int(0.45 * SR)
    t = tt(n)
    f = 45 + 95 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-t * 7.5)
    s += hp(RNG.randn(n), 2500) * np.exp(-t * 250) * 0.25
    return s * 0.9 * v


def clap(v=1.0):
    n = int(0.35 * SR)
    t = tt(n)
    nz = bp(RNG.randn(n), 900, 5000)
    e = np.zeros(n)
    for k, d in enumerate((0.0, 0.011, 0.022)):
        e += (t >= d) * np.exp(-np.maximum(t - d, 0) * (140 if k < 2 else 22))
    return nz * e * 0.35 * v


def shaker(v=1.0):
    n = int(0.09 * SR)
    t = tt(n)
    return hp(RNG.randn(n), 5500) * np.minimum(1, t / 0.012) * np.exp(-t * 55) * 0.16 * v


def hat(v=1.0):
    n = int(0.06 * SR)
    t = tt(n)
    return hp(RNG.randn(n), 8000) * np.exp(-t * 110) * 0.14 * v


def bell(f, dur=1.6, v=1.0):
    n = int(dur * SR)
    t = tt(n)
    s = np.zeros(n)
    for r, a, d in ((1, 1, 2.2), (2.0, 0.5, 3.0), (3.01, 0.28, 5), (4.2, 0.16, 8), (5.4, 0.1, 12)):
        s += a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * d)
    return s * np.minimum(1, t / 0.002) * 0.3 * v


def noise_sweep(dur, f0, f1, q=0.6, shape=None):
    """Band-limited noise whose centre sweeps f0->f1 (whoosh / riser)."""
    n = int(dur * SR)
    nz = RNG.randn(n)
    out = np.zeros(n)
    blk = 512
    zi_state = None
    for i in range(0, n, blk):
        u = i / max(n - 1, 1)
        fc = f0 * (f1 / f0) ** u
        lo, hi = max(40, fc * (1 - q / 2)), min(SR / 2 * 0.95, fc * (1 + q / 2))
        b, a = butter(2, [lo / (SR / 2), hi / (SR / 2)], btype="band")
        if zi_state is None or len(zi_state) != max(len(a), len(b)) - 1:
            zi_state = np.zeros(max(len(a), len(b)) - 1)
        out[i:i + blk], zi_state = lfilter(b, a, nz[i:i + blk], zi=zi_state)
    t = tt(n)
    e = shape(t / dur) if shape else np.sin(np.pi * t / dur) ** 1.5
    return out * e


# ======================================================================= sound design
def sfx_whoosh(dur=0.45, up=True, v=1.0):
    return noise_sweep(dur, 300 if up else 3000, 3000 if up else 300, 0.8) * 0.5 * v


def sfx_crackle(dur=0.4, dens=60, v=1.0):
    """Organic root growth: woody micro-crackles + a soft rising 'grow' tone."""
    n = int(dur * SR)
    out = np.zeros(n)
    k = int(dens * dur)
    for _ in range(k):
        i = RNG.randint(0, max(1, n - 400))
        L = RNG.randint(60, 300)
        g = RNG.rand() ** 2
        out[i:i + L] += RNG.randn(L) * np.exp(-np.arange(L) / (L / 4)) * g
    out = bp(out, 900, 7000) * 0.5
    t = tt(n)
    tone = np.sin(2 * np.pi * np.cumsum(220 + 200 * t / dur) / SR) * 0.05 * np.sin(np.pi * t / dur)
    return (out + tone) * np.minimum(1, t / 0.02) * np.minimum(1, (dur - t) / 0.05) * v


def sfx_creak(dur=0.35, f=110, v=1.0):
    n = int(dur * SR)
    t = tt(n)
    fr = f * (1 + 0.15 * np.sin(2 * np.pi * 7 * t) + 0.08 * RNG.randn(n).cumsum() / np.sqrt(n))
    ph = 2 * np.pi * np.cumsum(fr) / SR
    saw = 2 * ((ph / (2 * np.pi)) % 1) - 1
    s = bp(saw, 200, 1800) * np.sin(np.pi * t / dur) * 0.22
    return s * v


def sfx_rustle(dur=0.5, v=1.0):
    n = int(dur * SR)
    t = tt(n)
    am = np.abs(lp(RNG.randn(n), 30)) * 3
    s = bp(RNG.randn(n), 2500, 9000) * am * np.sin(np.pi * t / dur) ** 0.7
    return s * 0.25 * v


def sfx_tick(f=2400, v=1.0):
    n = int(0.05 * SR)
    t = tt(n)
    return (np.sin(2 * np.pi * f * t) * np.exp(-t * 120) + bp(RNG.randn(n), 2000, 8000) * np.exp(-t * 300) * 0.3) * 0.35 * v


def sfx_click(v=1.0):
    n = int(0.08 * SR)
    t = tt(n)
    s = np.sin(2 * np.pi * 1400 * t) * np.exp(-t * 90) + np.sin(2 * np.pi * 180 * t) * np.exp(-t * 40) * 0.8
    return s * 0.4 * v


def sfx_pop(f0=380, f1=900, v=1.0):
    n = int(0.12 * SR)
    t = tt(n)
    f = f0 + (f1 - f0) * (1 - np.exp(-t * 60))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 32) * 0.35 * v


def sfx_thud(v=1.0, f=70):
    n = int(0.6 * SR)
    t = tt(n)
    fr = f * 0.6 + f * np.exp(-t * 25)
    s = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t * 7)
    s += lp(RNG.randn(n), 1200) * np.exp(-t * 35) * 0.4
    return s * 0.7 * v


def sfx_impact(v=1.0):
    """Big landing: sub boom + body thump + debris + air."""
    n = int(1.6 * SR)
    t = tt(n)
    boom = np.sin(2 * np.pi * np.cumsum(32 + 60 * np.exp(-t * 14)) / SR) * np.exp(-t * 2.4)
    body = sfx_thud(1.0, 90)
    deb = sfx_crackle(0.7, 120, 0.6)
    air = noise_sweep(1.0, 4000, 300, 1.2, shape=lambda u: np.exp(-u * 5)) * 0.25
    out = boom * 0.9
    out[:len(body)] += body
    out[:len(deb)] += deb
    out[:len(air)] += air
    return out * v


def sfx_shimmer(dur=0.8, base=1800, v=1.0, rise=True):
    n = int(dur * SR)
    t = tt(n)
    s = np.zeros(n)
    for k in range(10):
        f = base * (1 + k * 0.37) * (1 + 0.004 * RNG.randn())
        ph = RNG.rand() * 6.28
        s += np.sin(2 * np.pi * f * t + ph) * (0.5 + 0.5 * np.sin(2 * np.pi * (5 + k) * t + ph))
    e = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** (0.6 if rise else 2)
    return s / 10 * e * 0.3 * v


def sfx_node(k, v=1.0):
    """Dimensional node activation: soft pluck in D major + small glass tick."""
    scale = [m("D5"), m("E5"), m("F#5"), m("A5"), m("B5"), m("D6"), m("E6")]
    f = mf(scale[k % len(scale)])
    s = mallet(f, 0.7, 0.8) * 0.8
    s[:int(0.05 * SR)] += sfx_tick(4200, 0.5)
    return s * v


def sfx_snap(v=1.0):
    n = int(0.12 * SR)
    t = tt(n)
    s = np.sin(2 * np.pi * 620 * t) * np.exp(-t * 60) + bp(RNG.randn(n), 1500, 6000) * np.exp(-t * 180) * 0.6
    s += np.sin(2 * np.pi * 150 * t) * np.exp(-t * 35) * 0.6
    return s * 0.4 * v


def lougha_success(v=1.0):
    """Original Lougha success sound: warm D-major lift (A5 -> D6) with felt
    under-chord and a short shimmer. Replaces any third-party correct chime."""
    n = int(1.6 * SR)
    out = np.zeros(n)
    for (dt, note, g) in ((0.0, "A5", 0.9), (0.085, "D6", 1.0)):
        s = mixa(bell(mf(m(note)), 1.4, g), mallet(mf(m(note)), 1.2, 0.7) * 0.6)
        i = int(dt * SR)
        out[i:i + len(s)] += s[:n - i]
    ch = sum(felt(mf(m(x)), 1.4, 0.6) for x in ("D4", "F#4", "A4"))
    out[:len(ch)] += ch * 0.5
    sh = sfx_shimmer(0.7, 2600, 0.6)
    out[int(0.08 * SR):int(0.08 * SR) + len(sh)] += sh
    return out * 0.9 * v


def lougha_signature(v=1.0, full=False):
    """The Lougha sonic signature: a root note, then three rising branches and a
    bright leaf on top (D3 . D5 F#5 A5 . D6), over a warm D chord."""
    dur = 3.2 if full else 2.4
    n = int(dur * SR)
    out = np.zeros(n)
    seq = [(0.0, "D3", 0.8, "felt"), (0.10, "D5", 0.8, "mallet"), (0.17, "F#5", 0.85, "mallet"),
           (0.24, "A5", 0.9, "mallet"), (0.38, "D6", 1.0, "bell")]
    if full:
        seq += [(0.52, "F#6", 0.5, "bell"), (0.60, "A6", 0.35, "bell")]
    for dt, note, g, inst in seq:
        f = mf(m(note))
        s = felt(f, 2.0, g) if inst == "felt" else (mallet(f, 1.6, 0.9) * g if inst == "mallet" else bell(f, 2.2, g) * 1.2)
        i = int(dt * SR)
        out[i:i + len(s)] += s[:n - i]
    ch = sum(felt(mf(m(x)), dur - 0.4, 0.55) for x in ("D3", "A3", "D4", "F#4"))
    out[int(0.38 * SR):int(0.38 * SR) + len(ch)] += ch[:n - int(0.38 * SR)] * 0.6
    sh = sfx_shimmer(1.2, 3000, 0.8)
    out[int(0.38 * SR):int(0.38 * SR) + len(sh)] += sh
    return out * 0.85 * v


def reverse_swell(dur=0.32):
    n = int(dur * SR)
    ch = sum(felt(mf(m(x)), dur + 0.6, 0.8) for x in ("D4", "F#4", "A4", "D5"))[:n][::-1]
    nz = noise_sweep(dur, 300, 6000, 1.0, shape=lambda u: u ** 2.5) * 0.4
    t = tt(n)
    return (ch * 1.4 + nz) * (t / dur) ** 1.5


# ======================================================================= music
CHORDS = {
    "D": ["D3", "A3", "D4", "F#4"], "Bm": ["B2", "F#3", "B3", "D4"],
    "G": ["G2", "D3", "G3", "B3"], "A": ["A2", "E3", "A3", "C#4"],
    "Em": ["E3", "B3", "E4", "G4"],
}
ROOT = {"D": "D2", "Bm": "B1", "G": "G1", "A": "A1", "Em": "E2"}
PROG = ["D", "Bm", "G", "A"]


def chord_at(t):
    b = int(t / BAR)
    return PROG[b % 4]


def music():
    bus = Bus()
    breath0, land = C.HIT["breath"], C.HIT["land"]
    nbeats = int(C.DUR / BEAT) + 1

    def live(t):
        return not (breath0 <= t < land) and t < C.DUR

    # felt-key chords every half bar (soft from frame 0), round sub on roots
    for hb in range(int(C.DUR / (BAR / 2)) + 1):
        t = hb * BAR / 2
        if not live(t) or t >= land:
            continue
        ch = chord_at(t)
        soft = 0.55 if 9.33 <= t < 11.4 else 0.75
        for k, nt in enumerate(CHORDS[ch]):
            bus.add(t + k * 0.012, felt(mf(m(nt)), BAR / 2 + 0.6, soft), 0.55, (k - 1.5) * 0.25)
        if hb % 2 == 0:
            bus.add(t, sub(mf(m(ROOT[ch])), BAR, 0.03, 0.35), 0.75)
    # mallet arpeggios (8ths) - intro, root path, lift sections
    arp = {"D": ["D5", "F#5", "A5", "D6"], "Bm": ["B4", "D5", "F#5", "B5"], "G": ["G4", "B4", "D5", "G5"],
           "A": ["A4", "C#5", "E5", "A5"]}
    for e in range(int(C.DUR / (BEAT / 2))):
        t = e * BEAT / 2
        if not live(t) or t >= land:
            continue
        sect_gain = 0.0
        if t < 1.67:
            sect_gain = 0.35
        elif t < 2.93:
            sect_gain = 0.42
        elif t < 4.8:
            sect_gain = 0.0
        elif t < 7.2:
            sect_gain = 0.32
        elif t < 9.33:
            sect_gain = 0.42
        elif t < 11.4:
            sect_gain = 0.0
        elif t < 14.67:
            sect_gain = 0.48
        elif t < 16.5:
            sect_gain = 0.30
        if sect_gain:
            nts = arp[chord_at(t)]
            nt = nts[e % 4] if (e // 4) % 2 == 0 else nts[3 - e % 4]
            bus.add(t, mallet(mf(m(nt)), 0.9), sect_gain * 0.55, 0.35 * math.sin(e))
    # lesson: delicate melody of single notes (progression)
    mel = [(2.95, "A5"), (3.30, "B5"), (3.60, "D6"), (3.90, "F#5"), (4.20, "A5"), (4.50, "B5")]
    for t, nt in mel:
        bus.add(t, mallet(mf(m(nt)), 1.2, 0.9), 0.32, 0.2)
        bus.add(t, bell(mf(m(nt)) * 2, 0.8, 0.3), 0.15, -0.2)
    # rhythm
    for b in range(nbeats * 4):
        t = b * BEAT / 4          # 16ths
        if not live(t) or t >= land:
            continue
        beat_i = b // 4
        sub16 = b % 4
        if 1.67 <= t < 2.93 and sub16 % 2 == 0:
            bus.add(t, hat(0.7), 0.6, 0.3)
        if 4.8 <= t < 7.2:
            ramp = (t - 4.8) / 2.4
            bus.add(t, shaker(0.4 + 0.6 * ramp), 0.7, -0.3)
            if sub16 == 0 and beat_i % 2 == 0 and t > 5.4:
                bus.add(t, kick(0.5 + 0.4 * ramp), 0.7)
        if 7.2 <= t < 9.33:
            if sub16 == 0:
                bus.add(t, kick(), 0.85)
                if beat_i % 2 == 1:
                    bus.add(t, clap(), 0.7, 0.05)
            bus.add(t, shaker(0.8 if sub16 % 2 else 0.5), 0.6, -0.3)
        if 11.4 <= t < 14.67:
            if sub16 == 0:
                bus.add(t, kick(0.85), 0.75)
                if beat_i % 2 == 1:
                    bus.add(t, clap(0.8), 0.6)
            if sub16 % 2 == 0:
                bus.add(t, hat(0.8), 0.5, 0.3)
        if 14.67 <= t < 16.5 and sub16 == 0:
            bus.add(t, kick(0.5), 0.5)
    # rising build into the breath
    bus.add(15.2, noise_sweep(1.3, 400, 7000, 0.9, shape=lambda u: u ** 2) * 0.35, 0.6)
    # the breath: only a reversed swell
    bus.add(land - 0.32, reverse_swell(0.32), 0.9)
    # 16.80 full chord + low hit, ringing under the end card
    for k, nt in enumerate(["D2", "A2", "D3", "F#3", "A3", "D4", "F#4", "A4", "D5"]):
        bus.add(land + k * 0.008, felt(mf(m(nt)), 4.4, 0.95), 0.62, (k - 4) * 0.12)
    for nt in ("D5", "F#5", "A5", "D6"):
        bus.add(land, mallet(mf(m(nt)), 2.5, 0.8), 0.25)
    bus.add(land, sub(mf(m("D1")), 4.4, 0.005, 0.5), 1.0)
    bus.add(land, kick(1.2), 0.8)
    # end-card pad (keeps ringing)
    for k, nt in enumerate(["D3", "A3", "D4", "F#4", "A4"]):
        n = int(2.8 * SR)
        t_ = tt(n)
        pad = sum(np.sin(2 * np.pi * mf(m(nt)) * h * t_) / h ** 2 for h in (1, 2, 3))
        pad *= np.minimum(1, t_ / 1.0) * np.minimum(1, (2.8 - t_) / 1.2)
        bus.add(18.4, lp(pad, 1800), 0.05, (k - 2) * 0.3)
    # gentle mallet motif in the end card
    for i, (dt, nt) in enumerate([(0, "A5"), (0.3, "D6"), (0.6, "F#6")]):
        bus.add(19.35 + dt, mallet(mf(m(nt)), 1.5, 0.6), 0.18, 0.3 * (i - 1))
    st = bus.st()
    return reverb(st, 0.28, 1.8)


def reverb(st, wet=0.25, rt=1.6):
    n = int(rt * SR)
    t = tt(n)
    out = st.copy()
    for ch in range(2):
        ir = RNG.randn(n) * np.exp(-t * 6.9 / rt)
        ir = lp(ir, 5000)
        ir[: int(0.012 * SR)] = 0
        ir /= np.sqrt(np.sum(ir ** 2))
        out[:, ch] = st[:, ch] * (1 - wet) + fftconvolve(st[:, ch], ir)[:len(st)] * wet * 0.9
    return out


# ======================================================================= cue list
def cues():
    """Every visible move gets a sound.  Returns [(t, name, fn, gain, pan)]."""
    Q = []

    def q(t, name, fn, g=1.0, pan=0.0):
        Q.append((t, name, fn, g, pan))

    H = C.HIT
    # S1 hook
    q(0.00, "seed root shimmer", lambda: sfx_shimmer(0.25, 2200, 0.8), 0.6)
    q(0.02, "root accelerates toward camera", lambda: noise_sweep(0.17, 500, 5000, 0.9, shape=lambda u: u ** 2), 0.7)
    q(0.04, "root growth crackle", lambda: sfx_crackle(0.15, 120), 0.6)
    q(H["slam"], "TREE SLAM - sub hit", lambda: sfx_impact(1.2), 1.0)
    q(H["slam"] + 0.03, "leaves react", lambda: sfx_rustle(0.6, 1.2), 0.8, 0.2)
    q(H["slam"] + 0.06, "branch creak L", lambda: sfx_creak(0.3, 120), 0.7, -0.4)
    q(H["slam"] + 0.12, "branch creak R", lambda: sfx_creak(0.28, 150), 0.6, 0.4)
    q(H["slam"] + 0.02, "light particles", lambda: sfx_shimmer(0.6, 3000, 0.7, False), 0.5)
    q(H["slam"] + 0.08, "roots spread", lambda: sfx_crackle(0.5, 70), 0.7)
    q(0.40, "camera eases back (air)", lambda: sfx_whoosh(0.7, False, 0.5), 0.5)
    for k, t in enumerate((0.47, 0.62, 0.78, 0.92)):
        q(t, f"wordmark root crawl {k + 1}", lambda: sfx_crackle(0.18, 60, 0.7), 0.5, -0.5 + k * 0.33)
    q(0.60, "wordmark reveal shimmer", lambda: sfx_shimmer(0.5, 2400, 0.6), 0.6)
    q(H["book_glint"], "golden book glint", lambda: bell(mf(m("A6")), 1.0, 0.6), 0.45, 0.1)
    q(H["tree_gesture"], "tree gesture rustle", lambda: sfx_rustle(0.5), 0.6)
    q(H["tree_gesture"] + 0.05, "branch creak (gesture)", lambda: sfx_creak(0.25, 135), 0.5)
    q(H["dive"], "dive into the roots", lambda: sfx_whoosh(0.45, False, 1.0), 0.8)
    # S2 root path
    q(1.45, "root races along the path", lambda: sfx_crackle(0.75, 90), 0.6)
    for k, t in enumerate((1.48, 1.60, 1.72, 1.84, 1.96, 2.08, 2.18)):
        q(t, f"lesson node {k + 1} lights", lambda k=k: sfx_node(k), 0.55, -0.6 + k * 0.2)
    q(1.92, "interface rises from node", lambda: sfx_whoosh(0.3, True, 0.7), 0.6, 0.3)
    q(2.20, "interface settles", lambda: sfx_thud(0.4, 140), 0.5, 0.3)
    q(2.08, "touch moves in", lambda: sfx_whoosh(0.25, True, 0.3), 0.4, 0.4)
    q(H["start_press"], "START pressed", lambda: sfx_click(1.2), 0.9)
    q(H["start_press"] + 0.02, "start ripple", lambda: sfx_shimmer(0.4, 1500, 0.7, False), 0.5)
    q(2.42, "root to lesson", lambda: sfx_crackle(0.5, 70), 0.55)
    q(2.72, "camera flies to lesson", lambda: sfx_whoosh(0.35, True, 0.8), 0.7)
    # S3 lesson
    q(2.90, "lesson panel arrives", lambda: sfx_thud(0.35, 160), 0.45)
    q(2.98, "prompt pops", lambda: sfx_pop(500, 900, 0.6), 0.5)
    q(3.08, "sentence audio button", lambda: sfx_tick(1800, 0.8), 0.6)
    q(3.10, "speaker plays (soft)", lambda: mallet(mf(m("F#5")), 0.5, 0.5), 0.3)
    for i, t0 in enumerate(C.TILE_TIMES):
        q(t0, f"tile {i + 1} lifts", lambda: sfx_whoosh(0.18, True, 0.45), 0.45, -0.3 + 0.15 * i)
        q(t0 + 0.30, f"tile {i + 1} snaps", lambda: sfx_snap(1.0), 0.7, -0.3 + 0.15 * i)
    q(3.20, "root crawls under the lesson", lambda: sfx_crackle(1.2, 25, 0.6), 0.4)
    q(H["chime1"], "LOUGHA SUCCESS #1", lambda: lougha_success(1.0), 0.95)
    q(H["chime1"] + 0.02, "correction strip pops", lambda: sfx_pop(420, 820, 0.7), 0.45)
    q(H["chime1"] + 0.05, "progress bar fills", lambda: noise_sweep(0.5, 800, 5000, 0.4) * 0.4 + sfx_shimmer(0.5, 2000, 0.5), 0.5)
    q(4.74, "root leans out", lambda: sfx_whoosh(0.35, True, 0.8), 0.7)
    # S4 progress
    q(4.95, "progress card pops", lambda: sfx_thud(0.35, 170), 0.45)
    q(5.00, "root curls upward", lambda: sfx_crackle(0.5, 80), 0.65)
    q(5.25, "trunk lights up", lambda: sfx_shimmer(0.7, 1600, 0.8), 0.55)
    for k, t in enumerate((5.4, 5.8, 6.2)):
        q(t, f"young tree grows {k + 1}", lambda: sfx_creak(0.4, 100 + 20 * k), 0.5, -0.5)
    for k, t in enumerate((6.20, 6.30, 6.42, 6.55)):
        q(t, f"leaf / flag pops {k + 1}", lambda k=k: sfx_pop(500 + 80 * k, 1100 + 80 * k, 0.6), 0.4, -0.6 + 0.1 * k)
    vals = np.linspace(5.47, 6.70, 14)
    for k, t in enumerate(vals):
        q(t, f"counter digit tick {k + 1}", lambda: sfx_tick(3000, 0.5), 0.35, 0.3)
    for k in range(7):
        q(5.75 + k * 0.17, f"progress node {k + 1}", lambda k=k: sfx_node(k, 0.7), 0.45, 0.1 * k)
    q(5.62, "course bar fills", lambda: noise_sweep(1.2, 600, 4000, 0.3, shape=lambda u: np.sin(np.pi * u)) * 0.35, 0.45)
    q(6.88, "fly to the community", lambda: sfx_whoosh(0.35, True, 0.8), 0.7)
    # S5 community
    q(H["drop"], "DROP - card lands", lambda: sfx_thud(1.0, 80), 0.8)
    for k in range(7):
        q(H["drop"] + 0.25 + k * 0.05, f"row {k + 1} appears", lambda: sfx_tick(2200, 0.4), 0.35, 0.4)
    q(H["drop"] + 0.22, "'Grow' pops", lambda: sfx_pop(400, 800), 0.4, -0.4)
    q(H["drop"] + 0.40, "'together.' pops", lambda: sfx_pop(500, 1000), 0.4, -0.4)
    q(7.80, "Amira's row lifts", lambda: sfx_whoosh(0.25, True, 0.6), 0.6, 0.3)
    q(7.95, "row rises", lambda: noise_sweep(0.7, 600, 3500, 0.5) * 0.4, 0.55, 0.3)
    for k in range(5):
        q(8.05 + k * 0.12, f"passes a classmate {k + 1}", lambda k=k: sfx_tick(1600 + k * 250, 0.5), 0.4, 0.3)
    q(H["rank1"], "LOUGHA SUCCESS #2 (#1)", lambda: lougha_success(1.0), 0.95, 0.2)
    q(H["rank1"], "sparkle burst", lambda: sfx_shimmer(0.6, 3200, 0.9, False), 0.5, 0.2)
    q(9.05, "fly to the class", lambda: sfx_whoosh(0.35, True, 0.7), 0.6)
    # S6 talk
    q(9.15, "video call opens", lambda: sfx_pop(300, 600, 0.8) + 0, 0.5)
    q(9.30, "recording indicator", lambda: sfx_tick(1200, 0.5), 0.3, 0.6)
    q(9.42, "teacher caption appears", lambda: sfx_pop(600, 900, 0.4), 0.3, -0.4)
    for k in range(3):
        q(9.45 + k * 0.12, f"caption type {k + 1}", lambda: sfx_tick(3500, 0.25), 0.25, -0.4)
    q(9.55, "camera orbits", lambda: sfx_whoosh(1.4, True, 0.2), 0.3)
    q(10.12, "student caption appears", lambda: sfx_pop(650, 950, 0.4), 0.3, 0.4)
    for k in range(3):
        q(10.15 + k * 0.12, f"caption type {k + 4}", lambda: sfx_tick(3500, 0.25), 0.25, 0.4)
    q(10.10, "root becomes a voice wave", lambda: sfx_shimmer(0.9, 900, 0.6) + 0, 0.4, 0.4)
    q(10.98, "teacher reacts", lambda: lougha_success(0.5)[: int(0.6 * SR)], 0.35, -0.3)
    for k in range(3):
        q(11.0 + k * 0.12, f"heart {k + 1}", lambda k=k: sfx_pop(700 + 120 * k, 1300 + 120 * k, 0.4), 0.3, -0.3)
    q(11.18, "push into the call", lambda: sfx_whoosh(0.25, True, 0.8), 0.6)
    # S7 languages + skills
    q(11.38, "FAST pull-back", lambda: sfx_whoosh(0.4, False, 1.1), 0.9)
    q(11.40, "root to the hub", lambda: sfx_crackle(0.3, 90), 0.55)
    for k, (key, nt) in enumerate((("en", "A5"), ("fr", "D6"), ("de", "F#6"))):
        q(WT[key] - 0.30, f"branch to {key}", lambda: sfx_crackle(0.32, 90), 0.5, -0.5 + 0.5 * k)
        q(WT[key], f"language node {key.upper()} lights", lambda nt=nt: bell(mf(m(nt)), 1.2, 0.9) + 0, 0.5, -0.5 + 0.5 * k)
        q(WT[key] + 0.05, f"vocab tiles orbit {key}", lambda: sfx_whoosh(0.5, True, 0.25), 0.3, -0.5 + 0.5 * k)
    q(13.05, "central learning structure", lambda: sfx_thud(0.5, 120) + 0, 0.5)
    q(13.08, "golden book node", lambda: bell(mf(m("D5")), 1.0, 0.7), 0.4)
    q(13.30, "camera drops to the skills", lambda: sfx_whoosh(0.35, False, 0.8), 0.7)
    for k, (key, nt) in enumerate((("speaking", "D5"), ("listening", "F#5"), ("reading", "A5"), ("writing", "D6"))):
        q(WT[key] - 0.22, f"root to {key}", lambda: sfx_crackle(0.25, 80, 0.8), 0.45, -0.6 + 0.4 * k)
        q(WT[key], f"skill node {key} lights", lambda nt=nt: mixa(mallet(mf(m(nt)), 1.0), bell(mf(m(nt)) * 2, 0.7, 0.4)),
          0.5, -0.6 + 0.4 * k)
    # S8 message
    q(14.80, "skills merge into light", lambda: sfx_shimmer(0.5, 1400, 0.9), 0.55)
    q(14.82, "roots converge", lambda: sfx_crackle(0.35, 100), 0.55)
    q(WT["strong_roots_2"] - 0.05, "underline root grows", lambda: sfx_crackle(1.0, 40, 0.8), 0.45)
    q(WT["strong_roots_2"], "'Strong roots,' appears", lambda: sfx_pop(400, 700, 0.5), 0.3)
    q(15.50, "'endless possibilities.' appears", lambda: sfx_pop(500, 900, 0.5), 0.3)
    q(16.08, "camera cranes up", lambda: sfx_whoosh(0.5, True, 0.7), 0.55)
    q(16.10, "root climbs to the landing spot", lambda: sfx_crackle(0.5, 70), 0.45)
    # S9 hero
    q(H["land"] - 0.17, "tree drops", lambda: noise_sweep(0.17, 3000, 300, 0.9, shape=lambda u: u ** 1.5), 0.6)
    q(H["land"], "TREE LANDS ON THE HIT", lambda: sfx_impact(1.25), 1.0)
    q(H["land"] + 0.02, "roots spread under the book", lambda: sfx_crackle(0.55, 90), 0.6)
    q(H["land"] + 0.04, "leaves", lambda: sfx_rustle(0.7, 1.2), 0.7, 0.3)
    q(H["land"] + 0.10, "branches extend L", lambda: sfx_creak(0.35, 120), 0.55, -0.5)
    q(H["land"] + 0.20, "branches extend R", lambda: sfx_creak(0.35, 145), 0.5, 0.5)
    for k in range(6):
        q(H["land"] + 0.18 + k * 0.06, f"flag {k + 1} pops", lambda k=k: sfx_pop(450 + 70 * k, 1000 + 90 * k, 0.5), 0.35, -0.6 + 0.24 * k)
    q(WT["logo"] - 0.30, "roots reveal the wordmark", lambda: sfx_crackle(0.45, 70), 0.45)
    q(WT["logo"], "LOUGHA SONIC SIGNATURE", lambda: lougha_signature(1.0), 0.9)
    q(H["fanfare"], "Lougha lesson-complete fanfare", lambda: lougha_signature(0.8, True), 0.65)
    q(18.10, "happy branches", lambda: sfx_rustle(0.6), 0.45, -0.2)
    q(18.70, "leaf flutter", lambda: sfx_rustle(0.5, 0.7), 0.35, 0.3)
    # S10
    q(19.25, "end card tagline", lambda: sfx_shimmer(0.8, 1800, 0.5), 0.35)
    q(19.62, "'Learn. Grow. Connect.'", lambda: bell(mf(m("A5")), 1.0, 0.5), 0.25)
    return Q


# ======================================================================= mix
def lufs(x):
    import pyloudnorm as pyln
    meter = pyln.Meter(SR)
    return meter.integrated_loudness(x)


def main():
    os.makedirs(C.OUT, exist_ok=True)
    print("[audio] music...")
    mus = music()
    print("[audio] sfx...")
    bus = Bus()
    Q = cues()
    rows = []
    for t, name, fn, g, pan in Q:
        sig = fn()
        bus.add(t, sig, g, pan)
        rows.append((f"{t:.3f}", int(round(t * C.FPS)), name))
    sfx = reverb(bus.st(), 0.16, 1.2)
    with open(os.path.join(C.OUT, "cue_sheet.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time_s", "frame_60fps", "cue"])
        w.writerows(sorted(rows, key=lambda r: float(r[0])))
    print(f"[audio] {len(Q)} sound cues")

    # voice
    sr, vo = wavfile.read(os.path.join(C.BUILD, "vo.wav"))
    vo = vo.astype(np.float64) / 32768
    vo = np.pad(vo, (0, max(0, N - len(vo))))[:N]
    vo = hp(vo, 90)
    vo_st = np.stack([vo, vo], 1)
    g_vo = 10 ** ((-16 - lufs(vo_st)) / 20)
    vo_st *= g_vo

    # music level & ducking: under every spoken word music sits >= 12 dB below
    mus *= 10 ** ((-24 - lufs(mus)) / 20)
    env = np.abs(vo)
    win = int(0.04 * SR)
    env = np.convolve(env, np.ones(win) / win, "same")
    act = (env > env.max() * 0.04).astype(np.float64)
    # attack 40 ms / release 350 ms smoothing
    k = np.exp(-1 / (0.35 * SR))
    ka = np.exp(-1 / (0.04 * SR))
    sm = np.zeros_like(act)
    s = 0.0
    for i in range(0, len(act), 64):
        a = act[i]
        s = a + (s - a) * (ka ** 64 if a > s else k ** 64)
        sm[i:i + 64] = s
    duck_db = -9.0 * sm
    # dip music under the hero brand sounds
    for th in (C.HIT["chime1"], C.HIT["rank1"], WT["logo"], C.HIT["fanfare"]):
        i0, i1 = int((th - 0.05) * SR), int((th + 0.7) * SR)
        ramp = np.sin(np.linspace(0, np.pi, i1 - i0)) * -5.0
        duck_db[i0:i1] = np.minimum(duck_db[i0:i1], ramp + duck_db[i0:i1])
    gain = 10 ** (duck_db / 20)
    mus_d = mus * gain[:, None]

    # verify >= 12 dB voice-over-music per word; fix any word that is short
    with open(os.path.join(C.BUILD, "vo_timing.json")) as f:
        words = json.load(f)["words"]

    def rms_db(x):
        return 10 * np.log10(np.mean(x ** 2) + 1e-12)

    def word_margin(ws, we):
        i0, i1 = int(ws * SR), int(max(we, ws + 0.08) * SR)
        msk = act[i0:i1] > 0
        if msk.sum() < 0.03 * SR:
            return None
        return rms_db(vo_st[i0:i1, 0][msk]) - rms_db(mus_d[i0:i1, 0][msk])
    report = []
    for _ in range(6):
        worst = 99
        for (ws, we, w) in words:
            d = word_margin(ws, we)
            if d is None:
                continue
            if d < 13.0:
                fix = 10 ** ((d - 13.6) / 20)
                j0, j1 = int((ws - 0.1) * SR), int((we + 0.15) * SR)
                mus_d[j0:j1] *= fix
            worst = min(worst, d)
        if worst >= 13.0:
            break
    for (ws, we, w) in words:
        d = word_margin(ws, we)
        if d is not None:
            report.append((w, round(float(d), 1)))
    sfx *= 10 ** ((-23 - lufs(sfx)) / 20)

    for name, x in (("music", mus_d), ("sfx", sfx), ("vo", vo_st)):
        wavfile.write(os.path.join(C.BUILD, f"stem_{name}.wav"), SR, np.clip(x, -1, 1).astype(np.float32))
    mix = vo_st + mus_d + sfx
    mix = mix[: int(C.DUR * SR)]
    # gentle fade at the very end of the end card
    n = len(mix)
    fade = np.ones(n)
    f0 = int((C.DUR - 0.5) * SR)
    fade[f0:] = np.linspace(1, 0, n - f0) ** 1.5
    mix *= fade[:, None]
    pre = os.path.join(C.BUILD, "mix_pre.wav")
    wavfile.write(pre, SR, np.clip(mix, -1, 1).astype(np.float32))
    # master: two-pass loudnorm to -14 LUFS / -1.25 dBTP
    out = os.path.join(C.OUT, "mix.wav")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", pre, "-af", "loudnorm=I=-14:TP=-1.25:LRA=11:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    js = r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1]
    meas = json.loads(js)
    af = (f"loudnorm=I=-14:TP=-1.25:LRA=11:measured_I={meas['input_i']}:measured_TP={meas['input_tp']}:"
          f"measured_LRA={meas['input_lra']}:measured_thresh={meas['input_thresh']}:offset={meas['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", pre, "-af", af + ",alimiter=limit=0.85:level=false",
                    "-ar", str(SR), "-c:a", "pcm_s24le", out], check=True)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", out, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    summ = r.stderr[r.stderr.rindex("Summary:"):]
    print(summ)
    lo = min(report, key=lambda x: x[1])
    print(f"[audio] voice-over-music margin: min {lo[1]} dB (word '{lo[0]}'), words checked: {len(report)}")
    with open(os.path.join(C.BUILD, "mix_report.json"), "w") as f:
        json.dump({"cues": len(Q), "vo_over_music_db": report, "ebur128": summ}, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
