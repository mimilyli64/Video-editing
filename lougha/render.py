"""Frame renderer + encoder.

  python3 -m lougha.render --fmt h            # 16:9 1920x1080 60 fps  -> out/picture_16x9.mp4
  python3 -m lougha.render --fmt v            # 9:16 1080x1920 60 fps  -> out/picture_9x16.mp4
  python3 -m lougha.render --fmt h --scale .5 --stills 0.2,2.4,4.3   # preview stills
  python3 -m lougha.render --fmt h --scale .5 --preview               # half-res preview video
"""
import argparse
import math
import os
import subprocess
import sys
import time
from multiprocessing import Pool

import cv2
import numpy as np

from . import config as C
from .engine.gfx import Canvas, add_glow_buffer, col, lin, smooth, clamp

_W = None


def _init(fmt, W, H):
    global _W
    from .engine.scenes import World
    _W = World(fmt, W, H)
    _W._bg = make_bg(W, H, fmt)
    _W._vig = make_vignette(W, H)
    rng = np.random.RandomState(7)
    _W._grain = [rng.randn(H // 2, W // 2).astype(np.float32) for _ in range(6)]


def make_bg(W, H, fmt):
    yy = np.linspace(0, 1, H)[:, None, None]
    xx = np.linspace(-1, 1, W)[None, :, None]
    navy = np.array(col("navy"), np.float32)
    top = np.array([0.090, 0.078, 0.170], np.float32)
    bot = np.array([0.050, 0.040, 0.098], np.float32)
    g = top * (1 - yy) + bot * yy
    asp = W / H
    r = np.sqrt((xx * asp / max(asp, 1)) ** 2 + ((yy - 0.45) * 2 / max(1 / asp, 1)) ** 2)
    glow = np.exp(-r ** 2 * 1.6) * np.array(col("purple"), np.float32) * 0.10
    return (g + glow).astype(np.float32)


def make_end_bg(W, H):
    yy = np.linspace(0, 1, H)[:, None, None]
    xx = np.linspace(-1, 1, W)[None, :, None]
    top = np.array(col("purple"), np.float32) * 0.62
    bot = np.array(col("navy"), np.float32) * 0.9
    g = top * (1 - yy) ** 1.3 + bot * (1 - (1 - yy) ** 1.3)
    r = np.sqrt(xx ** 2 + (yy - 0.35) ** 2 * 3)
    g = g + np.exp(-r ** 2 * 2.0) * np.array(col("violet"), np.float32) * 0.14
    return np.repeat(g, W, axis=1) if g.shape[1] == 1 else g


def make_vignette(W, H):
    yy = np.linspace(-1, 1, H)[:, None]
    xx = np.linspace(-1, 1, W)[None, :]
    r = np.sqrt(xx ** 2 + yy ** 2) / math.sqrt(2)
    return (1 - 0.42 * np.clip(r - 0.25, 0, 1) ** 1.6 / 0.75 ** 1.6)[..., None].astype(np.float32)


def exposure(t):
    e = 1.0
    # the breath before the final landing
    e *= 1 - 0.30 * smooth(lin(t, 16.42, 16.62)) * (1 - smooth(lin(t, 16.78, 16.86)))
    # flash on the two big impacts
    for th, amp in ((C.HIT["slam"], 0.35), (C.HIT["land"], 0.30), (C.HIT["drop"], 0.12)):
        d = t - th
        if 0 <= d < 0.3:
            e += amp * math.exp(-d * 18)
    # fade from black at the very start
    e *= 0.25 + 0.75 * smooth(lin(t, 0.0, 0.12))
    return e


def render_sample(t):
    W = _W
    cam = W.camera(t)
    cv = Canvas(W.W, W.H)
    endk = smooth(lin(t, 18.9, 19.8))
    if endk > 0:
        if not hasattr(W, "_endbg"):
            W._endbg = make_end_bg(W.W, W.H)
        cv.rgb[:] = W._bg * (1 - endk) + W._endbg * endk
    else:
        cv.rgb[:] = W._bg
    W.atmos.draw_bg(cv, cam, t)
    W.draw(cv, cam, t)
    W.atmos.draw_motes(cv, cam, t)
    add_glow_buffer(cv, 1.0)
    return cv.rgb


def motion_samples(t):
    """Number of temporal samples (180-degree shutter) from on-screen camera speed.
    t is in scene seconds; one delivered frame spans 1/(FPS*TS) scene seconds."""
    W = _W
    dt = 1.0 / C.FPS / C.TS
    c1, c2 = W.camera(t), W.camera(t + dt)
    P = c1.pos + c1.f * c1.focus
    s2, z = c2.project(P[None])
    shift = float(np.hypot(s2[0, 0] - W.W / 2, s2[0, 1] - W.H / 2))
    zoom = abs(c2.fov - c1.fov) / max(c1.fov, 1) * W.W
    shift = max(shift, zoom) / W.s
    return int(clamp(1 + shift / 9.0, 1, 6))


def render_frame(i):
    t = i / C.FPS / C.TS          # scene time of delivered frame i
    n = motion_samples(t)
    if n == 1:
        img = render_sample(t)
    else:
        img = None
        for k in range(n):
            ts = t + (k / (n - 1) - 0.5) * (0.5 / C.FPS / C.TS)
            s = render_sample(ts)
            img = s if img is None else img + s
        img /= n
    W = _W
    # bloom on bright areas
    small = cv2.resize(img, (W.W // 4, W.H // 4), interpolation=cv2.INTER_AREA)
    br = np.clip(small - 0.62, 0, None)
    br = cv2.GaussianBlur(br, (0, 0), 6 * W.s)
    img = img + cv2.resize(br, (W.W, W.H), interpolation=cv2.INTER_LINEAR) * 0.55
    img *= exposure(t)
    img *= W._vig
    # soft highlight roll-off
    img = img / (1 + np.maximum(img - 0.85, 0) * 0.9)
    g = W._grain[i % len(W._grain)]
    g = cv2.resize(g, (W.W, W.H), interpolation=cv2.INTER_LINEAR)
    img += g[..., None] * 0.012
    out = (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)
    return i, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fmt", default="h", choices=["h", "v"])
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--stills", default="")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=C.REAL_DUR)
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    W, H = (1920, 1080) if a.fmt == "h" else (1080, 1920)
    W, H = int(W * a.scale) // 2 * 2, int(H * a.scale) // 2 * 2
    os.makedirs(C.OUT, exist_ok=True)
    os.makedirs(C.BUILD, exist_ok=True)
    if a.stills:
        _init(a.fmt, W, H)
        d = os.path.join(C.BUILD, "stills")
        os.makedirs(d, exist_ok=True)
        for s in a.stills.split(","):
            t = float(s)
            t0 = time.time()
            _, img = render_frame(int(round(t * C.FPS)))   # --stills are delivered (real) seconds
            p = os.path.join(d, f"{a.fmt}_{t:05.2f}.png")
            cv2.imwrite(p, img[..., ::-1])
            print(p, f"{time.time() - t0:.2f}s")
        return
    f0, f1 = int(round(a.start * C.FPS)), min(C.NFRAMES, int(round(a.end * C.FPS)))
    name = a.out or os.path.join(C.BUILD if a.preview else C.OUT, f"picture_{'16x9' if a.fmt == 'h' else '9x16'}{'_preview' if a.preview else ''}.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(C.FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "medium" if not a.preview else "veryfast",
           "-crf", "18" if not a.preview else "22", "-pix_fmt", "yuv420p", "-movflags", "+faststart", name]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    with Pool(a.jobs, initializer=_init, initargs=(a.fmt, W, H)) as pool:
        for k, (i, img) in enumerate(pool.imap(render_frame, range(f0, f1), chunksize=2)):
            enc.stdin.write(img.tobytes())
            if k % 60 == 0:
                el = time.time() - t0
                print(f"[render {a.fmt}] frame {i}/{f1}  {el:.0f}s  ({(k + 1) / max(el, 1e-3):.2f} fps)", flush=True)
    enc.stdin.close()
    enc.wait()
    print("wrote", name, f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
