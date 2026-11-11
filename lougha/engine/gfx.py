"""Low-level drawing: easing, fonts/text sprites, premultiplied RGBA blitting,
shaded 3D tubes, glow buffer.  All images are float32; RGBA sprites are
premultiplied so warping and blending stay correct."""
import functools
import math
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .. import config as C


# ------------------------------------------------------------------ easing
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lin(t, t0, t1):
    if t1 <= t0:
        return 1.0 if t >= t1 else 0.0
    return clamp((t - t0) / (t1 - t0))


def smooth(x):
    x = clamp(x)
    return x * x * x * (x * (x * 6 - 15) + 10)


def ease_out(x, p=3):
    x = clamp(x)
    return 1 - (1 - x) ** p


def ease_in(x, p=2):
    x = clamp(x)
    return x ** p


def back(x, s=1.70158):
    x = clamp(x) - 1
    return x * x * ((s + 1) * x + s) + 1


def spring(t, freq=3.0, damp=6.0):
    """Damped oscillation that starts at 1 and settles to 0 (t in seconds)."""
    if t < 0:
        return 0.0
    return math.exp(-damp * t) * math.cos(2 * math.pi * freq * t)


def mix(a, b, x):
    return a + (b - a) * x


def mixc(c1, c2, x):
    return tuple(c1[i] + (c2[i] - c1[i]) * x for i in range(3))


def col(name, a=1.0):
    r, g, b = C.RGB[name] if isinstance(name, str) else name
    return (r / 255.0, g / 255.0, b / 255.0)


def hash01(*k):
    h = 2166136261
    for v in k:
        for ch in str(v):
            h = (h ^ ord(ch)) * 16777619 & 0xFFFFFFFF
    return (h % 100000) / 100000.0


# ------------------------------------------------------------------ fonts
@functools.lru_cache(maxsize=64)
def font(weight, size):
    w = min((400, 600, 700, 800, 900), key=lambda x: abs(x - weight))
    return ImageFont.truetype(os.path.join(C.FONTS, f"Nunito-{w}.ttf"), max(4, int(round(size))))


@functools.lru_cache(maxsize=2048)
def text_sprite(text, size, weight=700, color=(255, 255, 255), tracking=0.0, shadow=0.0):
    """Premultiplied float32 RGBA sprite of a line of text.  Returns (img, baseline_y)."""
    f = font(weight, size)
    asc, desc = f.getmetrics()
    if tracking:
        widths = [f.getlength(ch) + tracking * size for ch in text]
        w = int(math.ceil(sum(widths))) + 8
    else:
        w = int(math.ceil(f.getlength(text))) + 8
    pad = int(size * 0.25 + shadow * 2)
    h = asc + desc + 2 * pad
    im = Image.new("L", (w + 2 * pad, h), 0)
    d = ImageDraw.Draw(im)
    if tracking:
        x = pad
        for ch, cw in zip(text, widths):
            d.text((x, pad), ch, font=f, fill=255)
            x += cw
    else:
        d.text((pad, pad), text, font=f, fill=255)
    a = np.asarray(im, np.float32) / 255.0
    out = np.zeros(a.shape + (4,), np.float32)
    c = np.array(color, np.float32) / 255.0
    if shadow:
        sh = cv2.GaussianBlur(a, (0, 0), shadow)
        sh = np.roll(sh, int(shadow * 0.8), axis=0) * 0.55
        out[..., 3] = sh
    out[..., :3] = out[..., :3] * (1 - a[..., None]) + c * a[..., None]
    out[..., 3] = a + out[..., 3] * (1 - a)
    out[..., :3] *= 1.0  # rgb already premultiplied by construction (shadow is black)
    out[..., :3] = c * a[..., None]
    return out, pad + asc


def text_w(text, size, weight=700, tracking=0.0):
    f = font(weight, size)
    if tracking:
        return sum(f.getlength(ch) + tracking * size for ch in text)
    return f.getlength(text)


# ------------------------------------------------------------------ blitting (premultiplied)
def blit(dst, spr, x, y, alpha=1.0, scale=1.0, anchor="tl"):
    """Composite premultiplied sprite onto premultiplied dst (H,W,4) or rgb (H,W,3)."""
    if alpha <= 0.003:
        return
    if scale != 1.0:
        h0, w0 = spr.shape[:2]
        nw, nh = max(1, int(round(w0 * scale))), max(1, int(round(h0 * scale)))
        spr = cv2.resize(spr, (nw, nh), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
    h, w = spr.shape[:2]
    if anchor == "c":
        x, y = x - w / 2, y - h / 2
    elif anchor == "tc":
        x = x - w / 2
    elif anchor == "bc":
        x, y = x - w / 2, y - h
    elif anchor == "tr":
        x = x - w
    elif anchor == "cl":
        y = y - h / 2
    elif anchor == "cr":
        x, y = x - w, y - h / 2
    x, y = int(round(x)), int(round(y))
    H, W = dst.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    s = spr[y0 - y:y1 - y, x0 - x:x1 - x]
    if alpha != 1.0:
        s = s * alpha
    d = dst[y0:y1, x0:x1]
    a = s[..., 3:4]
    if dst.shape[2] == 4:
        d *= (1 - a)
        d += s
    else:
        d *= (1 - a)
        d += s[..., :3]


def tint(spr, rgb):
    out = spr.copy()
    out[..., :3] = np.array(rgb, np.float32)[None, None] * spr[..., 3:4]
    return out


def to_premult(rgba_u8):
    a = rgba_u8[..., 3:4].astype(np.float32) / 255.0
    out = np.empty(rgba_u8.shape, np.float32)
    out[..., :3] = rgba_u8[..., :3].astype(np.float32) / 255.0 * a
    out[..., 3:4] = a
    return out


def pil_sprite(w, h, draw_fn, ss=3):
    """Supersampled PIL drawing -> premultiplied float sprite."""
    im = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    draw_fn(d, ss)
    im = im.resize((w, h), Image.LANCZOS)
    return to_premult(np.asarray(im))


# ------------------------------------------------------------------ glow / tubes
class Canvas:
    """Per-frame render target: rgb (H,W,3) float + half-res additive glow."""

    def __init__(self, W, H):
        self.W, self.H = W, H
        self.rgb = np.zeros((H, W, 3), np.float32)
        self.glow = np.zeros((H // 2, W // 2, 3), np.float32)
        self.s = min(W, H) / 1080.0   # design px -> output px


def glow_line(cv, pts, widths, color, inten=1.0):
    """Additive glow strokes into the half-res glow buffer."""
    g = cv.glow
    c = tuple(float(v) * inten for v in color)
    p = (pts * 0.5 * 4).astype(np.int32)
    for i in range(len(pts) - 1):
        w = max(1, int(widths[i] * 0.5))
        cv2.line(g, tuple(p[i]), tuple(p[i + 1]), c, w, cv2.LINE_AA, 2)


def glow_dot(cv, x, y, r, color, inten=1.0):
    c = tuple(float(v) * inten for v in color)
    cv2.circle(cv.glow, (int(x * 0.5 * 4), int(y * 0.5 * 4)), max(1, int(r * 0.5 * 4)), c, -1, cv2.LINE_AA, 2)


def tube(cv, pts, widths, shades, alpha=1.0, light=(-0.2, -0.26), fade=None):
    """Shaded tube along screen polyline.
    shades: list of (rgb, width_mult, highlight_offset_mult) drawn in order.
    The first shade is the silhouette (defines coverage)."""
    if len(pts) < 2:
        return
    wmax = float(np.max(widths)) * 0.5 + 3
    x0 = int(max(0, np.floor(pts[:, 0].min() - wmax)))
    y0 = int(max(0, np.floor(pts[:, 1].min() - wmax)))
    x1 = int(min(cv.W, np.ceil(pts[:, 0].max() + wmax)))
    y1 = int(min(cv.H, np.ceil(pts[:, 1].max() + wmax)))
    if x1 <= x0 or y1 <= y0:
        return
    pw, ph = x1 - x0, y1 - y0
    patch = np.zeros((ph, pw, 3), np.uint8)
    mask = np.zeros((ph, pw), np.uint8)
    loc = (pts - np.array([x0, y0])) * 16
    n = len(pts)
    for si, (rgb, wm, om) in enumerate(shades):
        c = tuple(int(v * 255) for v in rgb)
        for i in range(n - 1):
            w = widths[i] * wm
            if w < 0.6:
                continue
            ox, oy = light[0] * om * widths[i] * 16, light[1] * om * widths[i] * 16
            p1 = (int(loc[i, 0] + ox), int(loc[i, 1] + oy))
            p2 = (int(loc[i + 1, 0] + ox), int(loc[i + 1, 1] + oy))
            th = max(1, int(round(w)))
            cv2.line(patch, p1, p2, c, th, cv2.LINE_AA, 4)
            if si == 0:
                cv2.line(mask, p1, p2, 255, th, cv2.LINE_AA, 4)
    a = mask.astype(np.float32) * (alpha / 255.0)
    d = cv.rgb[y0:y1, x0:x1]
    d *= (1 - a[..., None])
    d += patch.astype(np.float32) * (1 / 255.0) * a[..., None]


def tube_shades(base="purple", hi="lav", dark="lip", mid="violet", light_amt=1.0):
    """Standard purple tube material (dark rim -> body -> violet -> lavender spec)."""
    return [
        (col(dark), 1.0, 0.0),
        (col(base), 0.80, 0.10),
        (mixc(col(base), col(mid), 0.65 * light_amt), 0.50, 0.24),
        (mixc(col(mid), col(hi), 0.8 * light_amt), 0.22, 0.34),
        (mixc(col(hi), (1, 1, 1), 0.45 * light_amt), 0.07, 0.38),
    ]


def add_glow_buffer(cv, strength=1.0):
    g = cv.glow
    if g.max() <= 0:
        return
    b1 = cv2.GaussianBlur(g, (0, 0), 3 * cv.s)
    small = cv2.resize(g, (g.shape[1] // 4, g.shape[0] // 4), interpolation=cv2.INTER_AREA)
    b2 = cv2.GaussianBlur(small, (0, 0), 6 * cv.s)
    b2 = cv2.resize(b2, (g.shape[1], g.shape[0]), interpolation=cv2.INTER_LINEAR)
    tot = (g * 0.55 + b1 * 0.9 + b2 * 1.4) * strength
    up = cv2.resize(tot, (cv.W, cv.H), interpolation=cv2.INTER_LINEAR)
    cv.rgb += up
