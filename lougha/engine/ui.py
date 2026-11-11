"""Elegant dimensional interface kit (cards with purple lips, tiles, pills,
icons, avatars, video-call portraits).  Every builder is cached and returns a
premultiplied float32 RGBA sprite at final pixel size."""
import functools
import math

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .. import config as C
from .gfx import text_sprite, to_premult, font

SS = 2


def _rgb(name):
    return C.RGB[name] if isinstance(name, str) else name


def _grad(w, h, top, bot):
    t = np.linspace(0, 1, h)[:, None, None]
    a = np.array(_rgb(top), np.float32)[None, None]
    b = np.array(_rgb(bot), np.float32)[None, None]
    g = a * (1 - t) + b * t
    return np.repeat(g, w, axis=1)


@functools.lru_cache(maxsize=256)
def card(w, h, r=40, top="deep", bot="plum", lip=14, shadow=36, border=0.30, lipc="lip", glow=0.0,
         hi=0.22):
    """Rounded card with a darker purple lip underneath and a soft shadow.
    Returns (sprite, ox, oy): (ox, oy) is where the card face's top-left sits in the sprite."""
    m = shadow + 4
    W, H = w + 2 * m, h + 2 * m + lip
    ss = SS
    # shadow
    sh = Image.new("L", (W * ss, H * ss), 0)
    ImageDraw.Draw(sh).rounded_rectangle([m * ss, (m + lip + shadow * 0.25) * ss, (m + w) * ss, (m + h + lip + shadow * 0.25) * ss],
                                         r * ss, fill=150)
    sh = sh.filter(ImageFilter.GaussianBlur(shadow * ss * 0.45)).resize((W, H), Image.BILINEAR)
    sha = np.asarray(sh, np.float32) / 255.0
    # lip
    lm = Image.new("L", (W * ss, H * ss), 0)
    ImageDraw.Draw(lm).rounded_rectangle([m * ss, (m + lip) * ss, (m + w) * ss, (m + h + lip) * ss], r * ss, fill=255)
    lm = np.asarray(lm.resize((W, H), Image.LANCZOS), np.float32) / 255.0
    # face
    fm = Image.new("L", (W * ss, H * ss), 0)
    ImageDraw.Draw(fm).rounded_rectangle([m * ss, m * ss, (m + w) * ss, (m + h) * ss], r * ss, fill=255)
    fm = np.asarray(fm.resize((W, H), Image.LANCZOS), np.float32) / 255.0
    # border ring
    bm = Image.new("L", (W * ss, H * ss), 0)
    ImageDraw.Draw(bm).rounded_rectangle([m * ss, m * ss, (m + w) * ss, (m + h) * ss], r * ss, outline=255, width=int(2.2 * ss))
    bm = np.asarray(bm.resize((W, H), Image.LANCZOS), np.float32) / 255.0
    face = np.zeros((H, W, 3), np.float32)
    face[m:m + h, m:m + w] = _grad(w, h, top, bot) / 255.0
    # top inner highlight
    yy = np.arange(H)[:, None]
    hl = np.exp(-((yy - m) / (h * 0.10)) ** 2) * hi
    face = face + hl[..., None] * np.array(_rgb("lav"), np.float32) / 255.0
    lipc_ = np.array(_rgb(lipc), np.float32) / 255.0
    out = np.zeros((H, W, 4), np.float32)
    # shadow (black)
    out[..., 3] = sha * 0.55
    # lip over shadow
    out[..., :3] = out[..., :3] * (1 - lm[..., None]) + lipc_ * lm[..., None]
    out[..., 3] = lm + out[..., 3] * (1 - lm)
    # face over
    out[..., :3] = out[..., :3] * (1 - fm[..., None]) + face * fm[..., None]
    out[..., 3] = fm + out[..., 3] * (1 - fm)
    # border
    ba = bm * border
    out[..., :3] = out[..., :3] * (1 - ba[..., None]) + np.array(_rgb("lav"), np.float32) / 255.0 * ba[..., None]
    if glow:
        g = cv2.GaussianBlur(fm, (0, 0), 18) * glow
        out[..., :3] += np.array(_rgb("violet"), np.float32) / 255.0 * g[..., None] * (1 - out[..., 3:4])
        out[..., 3] = np.clip(out[..., 3] + g * (1 - out[..., 3]), 0, 1)
    return out, m, m


def put_card(dst, x, y, w, h, alpha=1.0, **kw):
    from .gfx import blit
    spr, ox, oy = card(int(w), int(h), **kw)
    blit(dst, spr, x - ox, y - oy, alpha)


@functools.lru_cache(maxsize=512)
def tile(text, size, h=None, pad=None, top="violet", bot="purple", lip=None, txt="white", weight=800, r=None,
         border=0.45):
    """Chunky word tile (dimensional, with lip)."""
    h = h or int(size * 1.9)
    pad = pad if pad is not None else int(size * 0.7)
    lip = lip if lip is not None else max(4, int(h * 0.14))
    tw = text_w(text, size, weight)
    w = int(tw + 2 * pad)
    spr, ox, oy = card(w, h, r=r or int(h * 0.32), top=top, bot=bot, lip=lip, shadow=int(h * 0.3), border=border,
                       hi=0.35)
    spr = spr.copy()
    ts, base = text_sprite(text, size, weight, _rgb(txt))
    from .gfx import blit
    blit(spr, ts, ox + w / 2, oy + h / 2 - size * 0.05, anchor="c")
    return spr, ox, oy, w, h


def text_w(text, size, weight=700):
    return font(weight, size).getlength(text)


# ------------------------------------------------------------------ icons
@functools.lru_cache(maxsize=256)
def icon(name, size, color="white", stroke=0.085):
    ss = 4
    S = size * ss
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = _rgb(color) + (255,)
    lw = max(2, int(S * stroke))

    def arc(box, a0, a1, w=lw):
        d.arc(box, a0, a1, fill=c, width=w)

    if name == "speaker":
        d.polygon([(S * .18, S * .38), (S * .34, S * .38), (S * .54, S * .2), (S * .54, S * .8), (S * .34, S * .62), (S * .18, S * .62)], fill=c)
        arc([S * .42, S * .3, S * .72, S * .7], -50, 50)
        arc([S * .40, S * .16, S * .88, S * .84], -50, 50)
    elif name == "check":
        d.line([(S * .2, S * .52), (S * .42, S * .72), (S * .8, S * .3)], fill=c, width=int(lw * 1.4), joint="curve")
    elif name == "mic":
        d.rounded_rectangle([S * .36, S * .12, S * .64, S * .6], S * .14, fill=c)
        arc([S * .24, S * .3, S * .76, S * .72], 0, 180)
        d.line([(S * .5, S * .72), (S * .5, S * .86)], fill=c, width=lw)
        d.line([(S * .34, S * .87), (S * .66, S * .87)], fill=c, width=lw)
    elif name == "headphones":
        arc([S * .16, S * .14, S * .84, S * .82], 180, 360, int(lw * 1.1))
        d.rounded_rectangle([S * .12, S * .48, S * .32, S * .84], S * .07, fill=c)
        d.rounded_rectangle([S * .68, S * .48, S * .88, S * .84], S * .07, fill=c)
    elif name == "book":
        d.polygon([(S * .5, S * .3), (S * .14, S * .22), (S * .14, S * .76), (S * .5, S * .84)], outline=c, width=lw)
        d.polygon([(S * .5, S * .3), (S * .86, S * .22), (S * .86, S * .76), (S * .5, S * .84)], outline=c, width=lw)
        for k in range(3):
            y = S * (.38 + k * .12)
            d.line([(S * .22, y), (S * .42, y + S * .04)], fill=c, width=max(1, lw // 2))
            d.line([(S * .58, y + S * .04), (S * .78, y)], fill=c, width=max(1, lw // 2))
    elif name == "pen":
        d.polygon([(S * .70, S * .12), (S * .88, S * .30), (S * .38, S * .80), (S * .20, S * .62)], fill=c)
        d.polygon([(S * .20, S * .62), (S * .38, S * .80), (S * .12, S * .88)], fill=c)
        d.line([(S * .10, S * .92), (S * .55, S * .92)], fill=c, width=max(1, lw // 2))
    elif name == "wave":
        hs = [.25, .5, .8, .45, .95, .6, .35, .7, .3]
        n = len(hs)
        for k, hh in enumerate(hs):
            x = S * (.12 + .76 * k / (n - 1))
            d.line([(x, S * (.5 - hh * .32)), (x, S * (.5 + hh * .32))], fill=c, width=int(lw * 0.9))
    elif name == "chat":
        d.rounded_rectangle([S * .12, S * .18, S * .82, S * .66], S * .14, outline=c, width=lw)
        d.polygon([(S * .28, S * .64), (S * .44, S * .64), (S * .26, S * .82)], fill=c)
        hs = [.4, .7, .5, .8, .45]
        for k, hh in enumerate(hs):
            x = S * (.30 + .34 * k / 4)
            d.line([(x, S * (.42 - hh * .12)), (x, S * (.42 + hh * .12))], fill=c, width=max(1, int(lw * .7)))
    elif name == "speakwave":
        # speech bubble with a voice waveform inside
        d.rounded_rectangle([S * .08, S * .14, S * .92, S * .70], S * .18, outline=c, width=lw)
        d.polygon([(S * .22, S * .66), (S * .42, S * .66), (S * .18, S * .90)], fill=c)
        hs = [.35, .7, 1.0, .6, .85, .45]
        for k, hh in enumerate(hs):
            x = S * (.26 + .48 * k / (len(hs) - 1))
            d.line([(x, S * (.42 - hh * .16)), (x, S * (.42 + hh * .16))], fill=c, width=int(lw * 0.8))
    elif name == "video":
        d.rounded_rectangle([S * .1, S * .28, S * .64, S * .72], S * .08, fill=c)
        d.polygon([(S * .68, S * .44), (S * .9, S * .3), (S * .9, S * .7), (S * .68, S * .56)], fill=c)
    elif name == "hand":
        d.rounded_rectangle([S * .3, S * .38, S * .74, S * .86], S * .14, fill=c)
        for k in range(4):
            x = S * (.32 + k * .11)
            d.rounded_rectangle([x, S * (.14 + abs(k - 1.5) * .04), x + S * .09, S * .5], S * .045, fill=c)
        d.rounded_rectangle([S * .16, S * .46, S * .36, S * .58], S * .05, fill=c)
    elif name == "star":
        pts = []
        for k in range(10):
            r = S * (.42 if k % 2 == 0 else .18)
            a = -math.pi / 2 + k * math.pi / 5
            pts.append((S / 2 + r * math.cos(a), S / 2 + r * math.sin(a) + S * .03))
        d.polygon(pts, fill=c)
    elif name == "leaf":
        d.ellipse([S * .22, S * .1, S * .78, S * .9], fill=c)
    elif name == "heart":
        d.ellipse([S * .14, S * .22, S * .52, S * .58], fill=c)
        d.ellipse([S * .48, S * .22, S * .86, S * .58], fill=c)
        d.polygon([(S * .16, S * .46), (S * .84, S * .46), (S * .5, S * .86)], fill=c)
    elif name == "play":
        d.polygon([(S * .3, S * .18), (S * .82, S * .5), (S * .3, S * .82)], fill=c)
    elif name == "rec":
        d.ellipse([S * .2, S * .2, S * .8, S * .8], fill=c)
    elif name == "globe":
        d.ellipse([S * .12, S * .12, S * .88, S * .88], outline=c, width=lw)
        d.ellipse([S * .34, S * .12, S * .66, S * .88], outline=c, width=lw)
        d.line([(S * .12, S * .5), (S * .88, S * .5)], fill=c, width=lw)
    im = im.resize((size, size), Image.LANCZOS)
    return to_premult(np.asarray(im))


@functools.lru_cache(maxsize=64)
def disc(size, top="violet", bot="purple", ring=None, ring_w=0.06, lip=0.08):
    """Chunky round button/badge with lip."""
    ss = 3
    S = size * ss
    H = int(S * (1 + lip))
    im = Image.new("RGBA", (S, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, S * lip, S - 1, S * (1 + lip) - 1], fill=_rgb("lip") + (255,))
    g = _grad(S, S, top, bot).astype(np.uint8)
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, S - 1, S - 1], fill=255)
    im.paste(Image.fromarray(g), (0, 0), mask)
    if ring:
        d.ellipse([0, 0, S - 1, S - 1], outline=_rgb(ring) + (255,), width=int(S * ring_w))
    d.ellipse([S * .18, S * .06, S * .82, S * .36], fill=(255, 255, 255, 40))
    im = im.resize((size, int(size * (1 + lip))), Image.LANCZOS)
    return to_premult(np.asarray(im))


@functools.lru_cache(maxsize=64)
def avatar(initial, size, shade=0):
    tops = ["violet", "lav", "purple", (120, 70, 200), (176, 104, 230), (98, 44, 160), (150, 80, 220)]
    spr = disc(size, top=tops[shade % len(tops)], bot="purple", ring="lav", ring_w=0.04, lip=0.0).copy()
    ts, _ = text_sprite(initial, int(size * 0.46), 800, (255, 255, 255))
    from .gfx import blit
    blit(spr, ts, size / 2, size / 2, anchor="c")
    return spr


# ------------------------------------------------------------------ video-call portraits
@functools.lru_cache(maxsize=64)
def portrait(who, w, h, mouth=0, blink=0, smile=0):
    """Stylised but recognisably real person on a warm home-classroom background.
    who: 'teacher' or 'student'.  mouth 0..3 (talking), blink 0/1, smile 0/1."""
    ss = 2
    W, H = w * ss, h * ss
    im = Image.new("RGB", (W, H))
    bgt = (58, 38, 92) if who == "teacher" else (40, 32, 76)
    bgb = (26, 20, 52) if who == "teacher" else (22, 18, 44)
    g = _grad(W, H, bgt, bgb).astype(np.uint8)
    im = Image.fromarray(g)
    d = ImageDraw.Draw(im, "RGBA")
    # room: shelves / window / warm lamp bokeh
    if who == "teacher":
        for k in range(3):
            y = H * (0.22 + k * 0.17)
            d.rectangle([W * 0.04, y, W * 0.34, y + H * 0.012], fill=(90, 60, 130, 255))
            x = W * 0.05
            rng = np.random.RandomState(k)
            while x < W * 0.33:
                bw = W * (0.012 + rng.rand() * 0.016)
                bh = H * (0.07 + rng.rand() * 0.06)
                cc = [(120, 70, 190), (190, 130, 240), (255, 212, 59), (90, 50, 150), (150, 90, 210)][rng.randint(5)]
                d.rectangle([x, y - bh, x + bw, y], fill=cc + (210,))
                x += bw + W * 0.004
        d.ellipse([W * 0.78, H * 0.12, W * 0.94, H * 0.30], fill=(255, 212, 59, 70))
        d.ellipse([W * 0.82, H * 0.16, W * 0.90, H * 0.26], fill=(255, 230, 150, 110))
        d.rectangle([W * 0.70, H * 0.42, W * 0.98, H * 0.43], fill=(110, 70, 160, 255))
        d.ellipse([W * 0.74, H * 0.34, W * 0.80, H * 0.42], fill=(150, 90, 220, 255))
    else:
        d.rounded_rectangle([W * 0.62, H * 0.10, W * 0.94, H * 0.48], W * 0.01, fill=(70, 60, 130, 255))
        d.rectangle([W * 0.775, H * 0.10, W * 0.785, H * 0.48], fill=(46, 36, 90, 255))
        d.rectangle([W * 0.62, H * 0.29, W * 0.94, H * 0.30], fill=(46, 36, 90, 255))
        d.ellipse([W * 0.06, H * 0.16, W * 0.18, H * 0.30], fill=(193, 122, 245, 60))
        d.ellipse([W * 0.12, H * 0.48, W * 0.30, H * 0.70], fill=(144, 47, 232, 50))
    im = im.filter(ImageFilter.GaussianBlur(ss * 3.5))
    d = ImageDraw.Draw(im, "RGBA")
    cx = W * (0.52 if who == "teacher" else 0.48)
    hy = H * 0.40
    hr = H * 0.165
    if who == "teacher":
        skin, skin_d = (198, 139, 99), (168, 110, 76)
        hair = (43, 26, 26)
        top = (122, 63, 192)
    else:
        skin, skin_d = (227, 180, 143), (200, 150, 115)
        hair = (176, 120, 220)   # lilac hijab
        top = (40, 34, 86)
    # shoulders / torso
    d.rounded_rectangle([cx - W * 0.30, H * 0.70, cx + W * 0.30, H * 1.15], W * 0.12, fill=top + (255,))
    d.polygon([(cx - W * 0.07, H * 0.66), (cx + W * 0.07, H * 0.66), (cx + W * 0.09, H * 0.76), (cx, H * 0.80), (cx - W * 0.09, H * 0.76)],
              fill=skin_d + (255,))
    if who == "teacher":
        # hair behind head (shoulder length)
        d.rounded_rectangle([cx - hr * 1.18, hy - hr * 1.05, cx + hr * 1.18, hy + hr * 1.55], hr * 0.9, fill=hair + (255,))
        d.rectangle([cx - W * 0.06, H * 0.70, cx + W * 0.06, H * 0.74], fill=top + (255,))
        d.ellipse([cx - W * 0.012, H * 0.775, cx + W * 0.012, H * 0.80], fill=(255, 212, 59, 255))
    else:
        # hijab drape
        d.ellipse([cx - hr * 1.32, hy - hr * 1.25, cx + hr * 1.32, hy + hr * 1.35], fill=hair + (255,))
        d.polygon([(cx - hr * 1.3, hy + hr * 0.2), (cx + hr * 1.3, hy + hr * 0.2), (cx + W * 0.2, H * 0.86), (cx - W * 0.2, H * 0.86)],
                  fill=(160, 104, 206, 255))
    # neck + face
    d.rectangle([cx - hr * 0.36, hy + hr * 0.6, cx + hr * 0.36, hy + hr * 1.35], fill=skin_d + (255,))
    d.ellipse([cx - hr * 0.86, hy - hr, cx + hr * 0.86, hy + hr * 1.06], fill=skin + (255,))
    # soft cheek shading
    d.ellipse([cx + hr * 0.25, hy - hr * 0.2, cx + hr * 0.85, hy + hr * 0.9], fill=skin_d + (60,))
    if who == "teacher":
        # fringe
        d.chord([cx - hr * 0.95, hy - hr * 1.12, cx + hr * 0.95, hy + hr * 0.25], 180, 360, fill=hair + (255,))
        d.ellipse([cx - hr * 0.98, hy - hr * 0.1, cx - hr * 0.80, hy + hr * 0.25], fill=skin_d + (255,))
        d.ellipse([cx - hr * 0.96, hy + hr * 0.2, cx - hr * 0.86, hy + hr * 0.32], fill=(255, 212, 59, 255))
    else:
        d.chord([cx - hr * 1.0, hy - hr * 1.15, cx + hr * 1.0, hy + hr * 0.05], 180, 360, fill=hair + (255,))
    # eyes
    ey = hy + hr * 0.10
    ex = hr * 0.36
    for sx in (-1, 1):
        x = cx + sx * ex
        if blink:
            d.line([(x - hr * 0.13, ey), (x + hr * 0.13, ey)], fill=(40, 24, 30, 255), width=int(ss * 3))
        elif smile:
            d.arc([x - hr * 0.14, ey - hr * 0.08, x + hr * 0.14, ey + hr * 0.14], 200, 340, fill=(40, 24, 30, 255), width=int(ss * 3.5))
        else:
            d.ellipse([x - hr * 0.10, ey - hr * 0.10, x + hr * 0.10, ey + hr * 0.10], fill=(40, 24, 30, 255))
            d.ellipse([x - hr * 0.035, ey - hr * 0.07, x + hr * 0.015, ey - hr * 0.02], fill=(255, 255, 255, 220))
        d.arc([x - hr * 0.18, ey - hr * 0.36, x + hr * 0.18, ey - hr * 0.10], 210, 330, fill=hair[:3] + (255,) if who == "teacher" else (70, 40, 40, 255), width=int(ss * 3))
    # nose
    d.arc([cx - hr * 0.10, hy + hr * 0.18, cx + hr * 0.10, hy + hr * 0.46], 30, 150, fill=skin_d + (255,), width=int(ss * 2.5))
    # mouth
    my = hy + hr * 0.62
    mw = hr * (0.30 + 0.06 * smile)
    if mouth == 0:
        d.arc([cx - mw, my - hr * 0.16, cx + mw, my + hr * (0.10 + 0.08 * smile)], 20, 160, fill=(150, 50, 70, 255), width=int(ss * 3.5))
    else:
        oh = hr * (0.06 + 0.07 * mouth)
        d.chord([cx - mw * 0.85, my - oh * 0.6, cx + mw * 0.85, my + oh * 1.4], 0, 180, fill=(120, 36, 60, 255))
        d.chord([cx - mw * 0.6, my - oh * 0.2, cx + mw * 0.6, my + oh * 0.6], 0, 180, fill=(255, 255, 255, 200))
    # blush
    for sx in (-1, 1):
        d.ellipse([cx + sx * hr * 0.55 - hr * 0.14, hy + hr * 0.38, cx + sx * hr * 0.55 + hr * 0.14, hy + hr * 0.52], fill=(230, 110, 140, 40 + 30 * smile))
    im = im.resize((w, h), Image.LANCZOS)
    a = np.asarray(im.convert("RGBA"))
    return to_premult(a)


def rounded_mask(w, h, r):
    m = Image.new("L", (w * 2, h * 2), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w * 2 - 1, h * 2 - 1], r * 2, fill=255)
    return np.asarray(m.resize((w, h), Image.LANCZOS), np.float32) / 255.0


def clip_round(spr, r):
    h, w = spr.shape[:2]
    m = rounded_mask(w, h, r)
    return spr * m[..., None]
