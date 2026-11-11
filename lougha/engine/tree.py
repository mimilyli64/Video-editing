"""The Lougha tree mascot, rebuilt in 3D from the logo's tree.

Geometry is authored in logo-pixel coordinates (the supplied 1315x1408 logo) and
converted to tree units (1 unit = 100 logo px, y up, origin at the trunk base).
Animation is hierarchical: every branch bends with its own damped spring, so
the impact, the gestures and the idle sway travel from the trunk out to the
leaves and flag fruits.  The roots are Root objects - the same renderer as the
luminous path through the film."""
import functools
import math

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .gfx import (col, mixc, tube, tube_shades, glow_dot, glow_line, clamp, smooth, spring,
                  hash01, to_premult, blit)
from .world import Root, curve, draw_quad, quad_corners, draw_sphere, NEAR


def L(px, py, z=0.0):
    return np.array([(px - 600) / 100.0, (1060 - py) / 100.0, z])


# id, parent, attach, ctrl(logo px), r0, r1 (logo px), z0, z1, grow window
BRANCHES = [
    ("trunk", None, 0, [(600, 1050), (603, 960), (597, 870), (590, 800), (588, 748)], 56, 32, 0.0, 0.0, (0.00, 0.30)),
    ("right", "trunk", 1.0, [(588, 748), (618, 690), (662, 618), (716, 528), (768, 432), (806, 352)], 30, 12, 0.0, 0.25, (0.18, 0.55)),
    ("left", "trunk", 0.93, [(588, 756), (566, 692), (545, 624), (516, 558), (480, 506)], 28, 12, 0.0, -0.45, (0.18, 0.55)),
    ("italy", "trunk", 0.62, [(593, 812), (552, 782), (492, 752), (440, 728)], 19, 8, 0.0, -0.3, (0.25, 0.58)),
    ("france", "right", 0.28, [(650, 640), (708, 612), (772, 590), (842, 574)], 15, 6, 0.1, -0.15, (0.38, 0.68)),
    ("germany", "left", 0.68, [(523, 572), (462, 556), (392, 540), (326, 524)], 10, 5, -0.3, 0.35, (0.40, 0.70)),
    ("spain", "right", 0.52, [(700, 556), (684, 470), (650, 370), (615, 282)], 9, 4, 0.2, 0.55, (0.40, 0.72)),
    ("tw1", "left", 0.45, [(536, 596), (500, 576), (466, 572)], 6, 3, -0.4, -0.5, (0.50, 0.78)),
    ("tw2", "right", 0.72, [(745, 470), (800, 458), (846, 452)], 6, 3, 0.2, 0.0, (0.50, 0.78)),
    ("tw3", "spain", 0.35, [(672, 438), (648, 418), (630, 404)], 5, 2.5, 0.45, 0.3, (0.55, 0.80)),
    ("tw4", "germany", 0.25, [(445, 552), (360, 440), (290, 360)], 5, 2.5, -0.2, 0.2, (0.55, 0.82)),
    ("tw5", "spain", 0.80, [(624, 306), (548, 258), (478, 226)], 5, 2.5, 0.5, 0.3, (0.58, 0.84)),
    ("tw6", "right", 0.92, [(796, 372), (870, 330), (930, 330)], 5, 2.5, 0.25, 0.1, (0.58, 0.84)),
    ("tw7", "left", 0.80, [(492, 524), (420, 470), (380, 430)], 5, 2.5, -0.4, -0.2, (0.58, 0.84)),
]
# flag fruits: code, branch, logo center, radius(px), z
SPHERES = [
    ("uk", "right", (838, 226), 134, 0.25),
    ("es", "spain", (590, 214), 64, 0.55),
    ("tr", "left", (452, 396), 114, -0.45),
    ("de", "germany", (263, 518), 64, 0.35),
    ("fr", "france", (912, 570), 75, -0.15),
    ("it", "italy", (360, 690), 90, -0.3),
]
# leaves: branch, attach u, logo tip position, size, shade
LEAVES = [
    ("tw1", 1.0, (448, 600), 1.05, 0), ("tw2", 1.0, (880, 448), 1.0, 1), ("tw3", 1.0, (606, 395), 1.1, 2),
    ("tw4", 1.0, (262, 320), 1.25, 0), ("tw5", 1.0, (440, 205), 0.9, 3), ("tw6", 1.0, (960, 318), 0.8, 2),
    ("tw7", 1.0, (350, 400), 0.85, 1),
    ("tw4", 0.6, (318, 420), 0.7, 3), ("tw5", 0.5, (520, 220), 0.7, 1), ("tw2", 0.5, (800, 420), 0.7, 0),
    ("tw1", 0.5, (500, 620), 0.6, 2), ("right", 0.45, (720, 560), 0.65, 3), ("left", 0.55, (556, 600), 0.6, 1),
    ("tw6", 0.4, (860, 300), 0.6, 0), ("tw3", 0.4, (690, 420), 0.6, 1), ("tw7", 0.5, (430, 450), 0.65, 2),
    ("spain", 0.6, (690, 380), 0.55, 3), ("france", 0.6, (790, 620), 0.6, 2), ("germany", 0.45, (420, 590), 0.55, 0),
    ("italy", 0.6, (470, 790), 0.55, 1),
]


@functools.lru_cache(maxsize=8)
def leaf_sprite(shade, size=160):
    """A modelled leaf: gradient body, darker rim, midrib + veins, satin highlight."""
    w, h = int(size * 0.62), size
    ss = 4
    W, H = w * ss, h * ss
    pal = [("purple", "lav"), ("violet", "lav"), ("plum", "violet"), ("purple", "violet")][shade]
    c0 = np.array(col(pal[0])) * 255
    c1 = np.array(col(pal[1])) * 255
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = 1 - yy / H                         # 0 at stem (bottom), 1 at tip
    half = np.clip(np.sin(np.clip(v, 0, 1) * np.pi), 0, 1) ** 0.85 * (W * 0.46) * (1 - 0.15 * v)
    bend = np.sin(v * np.pi) * W * 0.06
    dx = xx - (W / 2 + bend)
    inside = (np.abs(dx) <= half) & (v > 0.02)
    a = np.clip((half - np.abs(dx)) / (ss * 1.2), 0, 1) * (v > 0.02)
    side = dx / np.maximum(half, 1)
    shade_v = 0.55 + 0.45 * v
    lightside = np.clip(0.5 - side * 0.5, 0, 1)
    rgb = c0[None, None] * (1 - shade_v[..., None]) + c1[None, None] * shade_v[..., None]
    rgb = rgb * (0.72 + 0.38 * lightside[..., None])
    rim = np.clip(1 - (half - np.abs(dx)) / (ss * 5), 0, 1)
    rgb = rgb * (1 - 0.35 * rim[..., None])
    # midrib and veins
    rib = np.exp(-(dx / (ss * 1.3)) ** 2) * (v > 0.04) * (v < 0.92)
    rgb = rgb * (1 - 0.25 * rib[..., None]) + np.array([235, 215, 255]) * 0.25 * rib[..., None]
    for k in range(1, 6):
        vv = k / 6.5
        dy = (v - vv) * H - np.abs(dx) * 0.55
        vein = np.exp(-(dy / (ss * 1.1)) ** 2) * (np.abs(dx) < half * 0.85)
        rgb = rgb * (1 - 0.18 * vein[..., None])
    spec = np.exp(-((dx + W * 0.12) / (W * 0.12)) ** 2) * np.exp(-((v - 0.55) / 0.25) ** 2) * 0.25
    rgb = rgb + 255 * spec[..., None]
    img = np.dstack([np.clip(rgb, 0, 255), a * 255]).astype(np.uint8)
    img = cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)
    return to_premult(img)


@functools.lru_cache(maxsize=2)
def book_sprite(w=1400):
    """Golden open book (logo foundation), modelled with page blocks, fanning pages,
    cover thickness and a spine shadow."""
    h = int(w * 0.30)
    ss = 3
    W, H = w * ss, h * ss
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    gold, goldd, goldl = (255, 212, 59), (217, 154, 18), (255, 232, 138)
    cx = W / 2
    base_y = H * 0.80
    # cover / thickness
    d.rounded_rectangle([W * 0.03, base_y - H * 0.02, W * 0.97, base_y + H * 0.10], radius=int(H * 0.05), fill=(176, 112, 10))
    d.rounded_rectangle([W * 0.04, base_y - H * 0.05, W * 0.96, base_y + H * 0.05], radius=int(H * 0.05), fill=goldd)

    def top(u):
        # open book: low at the spine, pages swell up then roll down to the edge
        return base_y - H * (0.10 + 0.34 * math.sin(min(u, 1) * math.pi * 0.92) ** 0.65) - H * 0.02

    def block(sign, k=0.0):
        pts = []
        for i in range(61):
            u = i / 60
            x = cx + sign * u * W * 0.45
            pts.append((x, base_y - (base_y - top(u)) * (1 - k)))
        return pts

    for sgn in (-1, 1):
        d.polygon(block(sgn) + [(cx + sgn * W * 0.45, base_y), (cx, base_y)], fill=gold)
        # lighter upper page surface
        d.polygon(block(sgn) + block(sgn, 0.35)[::-1], fill=goldl)
    # page edge lines
    for k in range(1, 8):
        for sgn in (-1, 1):
            d.line(block(sgn, 0.10 + k * 0.105), fill=(222, 158, 28, 170), width=int(ss * 1.5))
    # fanning pages lifting from the spine (as in the logo)
    for k in range(6):
        for sgn in (-1, 1):
            pts = []
            span = 0.20 + k * 0.045
            lift = 0.30 + k * 0.07
            for i in range(41):
                u = i / 40
                x = cx + sgn * u * W * span
                y = top(0) - H * lift * math.sin(u * math.pi * 0.8) ** 0.8 * (1 - 0.3 * u) + u * H * 0.18
                pts.append((x, y))
            d.line(pts, fill=(255, 205, 80, 235), width=int(ss * (3.2 - k * 0.35)))
    img = np.asarray(im).astype(np.float32)
    # spine shadow + top sheen
    xx = (np.arange(W) - cx) / (W * 0.5)
    yy = np.arange(H) / H
    spine = np.exp(-(xx / 0.035) ** 2)[None, :] * 0.45
    sheen = np.exp(-((yy[:, None] - 0.58) / 0.07) ** 2) * (0.5 + 0.5 * np.cos(xx[None, :] * 3)) * 0.25
    img[..., :3] = img[..., :3] * (1 - spine[..., None]) + 255 * sheen[..., None] * (img[..., 3:4] / 255)
    img = np.clip(img, 0, 255).astype(np.uint8)
    img = cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)
    return to_premult(img)


class Branch:
    def __init__(self, spec):
        (self.id, self.parent, self.attach, ctrl, r0, r1, z0, z1, gw) = spec
        n = len(ctrl)
        pts = [L(x, y, z0 + (z1 - z0) * i / max(1, n - 1)) for i, (x, y) in enumerate(ctrl)]
        self.P, self.s = curve(pts, step=0.08, wobble=0.0)
        self.u = self.s / self.s[-1]
        self.r0, self.r1 = r0 / 100.0, r1 / 100.0
        self.g0, self.g1 = gw
        self.level = 0


class Tree:
    def __init__(self):
        self.br = {b[0]: Branch(b) for b in BRANCHES}
        for b in self.br.values():
            p = b.parent
            while p:
                b.level += 1
                p = self.br[p].parent
        self.order = [b[0] for b in BRANCHES]
        # leaves: stored as offset from attach point
        self.leaves = []
        for i, (bid, u, tip, size, shade) in enumerate(LEAVES):
            self.leaves.append(dict(b=bid, u=u, tip=L(*tip), size=size, shade=shade,
                                    ph=hash01("leaf", i) * 6.28, z=(hash01("lz", i) - 0.5) * 0.8))
        self.spheres = [dict(code=c, b=bid, ctr=L(*p, z), r=r / 100.0) for c, bid, p, r, z in SPHERES]
        self._roots = {}

    # ------------------------------------------------------------ roots
    def roots(self, key, origin, scale, seed=11, count=9, reach=1.0):
        if key in self._roots:
            return self._roots[key]
        rng = np.random.RandomState(seed)
        o = np.asarray(origin, float)
        R = []
        for k in range(count):
            a = math.pi * (0.04 + 0.92 * k / (count - 1)) + rng.uniform(-0.12, 0.12)
            dirx, dirz = math.cos(a), -math.sin(a) * 0.9   # spread toward the camera and sideways
            ln = (4.0 + rng.rand() * 3.8) * reach
            pts = [o + scale * np.array([0.0, 0.25, 0.0])]
            for j in range(1, 6):
                u = j / 5
                p = np.array([dirx * ln * u, -0.35 - 0.55 * u ** 1.5 + 0.25 * math.sin(u * 5 + k), dirz * ln * u * 0.75])
                p[0] += rng.uniform(-0.3, 0.3)
                pts.append(o + scale * p)
            R.append(Root(pts, r0=0.30 * scale, r1=0.05 * scale, seed=seed * 31 + k, wobble=0.10 * scale,
                          rootlets=1.2, strands=3, step=0.06 * max(scale, 0.4), twist=2.4 / max(scale, 0.3)))
        self._roots[key] = R
        return R

    # ------------------------------------------------------------ animation
    def angles(self, st):
        """Per-branch bend angle (radians) from springs, sway and gestures."""
        t = st.get("time", 0.0)
        imp = st.get("impact")          # seconds since landing (None = no impact)
        gest = st.get("gesture")        # seconds since gesture start
        happy = st.get("happy", 0.0)    # amplitude of rhythmic happy bounce
        out = {}
        for bid, b in self.br.items():
            lv = b.level
            side = 1 if b.P[-1, 0] > b.P[0, 0] else -1
            a = 0.018 * (lv + 0.5) * math.sin(t * 1.5 + lv * 0.9 + hash01(bid) * 3)     # idle sway
            if imp is not None and imp >= 0:
                # branches whip down then rebound; delay grows with level
                d = imp - 0.03 * lv
                a += -side * 0.20 * (0.6 + 0.5 * lv) * spring(max(0, d), 2.2 + 0.4 * lv, 4.0)  * (1 if d > 0 else 0)
            if gest is not None and 0 <= gest < 1.2:
                g = gest - 0.05 * lv
                if g > 0:
                    a += side * 0.10 * (0.4 + 0.4 * lv) * math.sin(g * 9.5) * math.exp(-g * 3.2)
            if happy:
                a += side * happy * 0.06 * (0.5 + 0.4 * lv) * math.sin(t * 2 * math.pi * 100 / 60 + lv * 0.6)
            out[bid] = a
        return out

    def pose(self, st):
        ang = self.angles(st)
        D, base = {}, {}
        for bid in self.order:
            b = self.br[bid]
            rest = b.P
            if b.parent is None:
                anchor = rest[0]
                brot = 0.0
            else:
                pd = D[b.parent]
                pb = self.br[b.parent]
                i = min(len(pd) - 1, int(b.attach * (len(pd) - 1)))
                anchor = pd[i]
                brot = base[b.parent] + ang[b.parent] * (b.attach ** 1.3)
            rel = rest - rest[0]
            th = brot + ang[bid] * (b.u ** 1.3)
            c, s = np.cos(th), np.sin(th)
            x = rel[:, 0] * c - rel[:, 1] * s
            y = rel[:, 0] * s + rel[:, 1] * c
            D[bid] = np.c_[x, y, rel[:, 2]] + anchor
            base[bid] = brot
        return D, ang, base

    def _attach(self, D, bid, u):
        P = D[bid]
        i = min(len(P) - 1, int(u * (len(P) - 1)))
        return P[i], i

    def _xf(self, P, st, origin, scale):
        """squash/stretch + lean, then to world."""
        sy = st.get("sy", 1.0)
        lean = st.get("lean", 0.0)
        Q = np.array(P, float, copy=True)
        Q[..., 0] /= math.sqrt(sy)
        Q[..., 2] /= math.sqrt(sy)
        Q[..., 1] *= sy
        if lean:
            c, s = math.cos(lean), math.sin(lean)
            x, y = Q[..., 0] * c - Q[..., 1] * s, Q[..., 0] * s + Q[..., 1] * c
            Q[..., 0], Q[..., 1] = x, y
        return np.asarray(origin, float) + scale * Q + np.array([0, st.get("dy", 0.0), 0])

    # ------------------------------------------------------------ draw
    def draw(self, cv, cam, origin, scale, st, roots_key=None):
        """st: grow, sy, lean, dy, time, impact, gesture, happy, glint, alpha, roots (0..1),
        lit (root illumination), book (0..1 visibility)"""
        alpha = st.get("alpha", 1.0)
        g = st.get("grow", 1.0)
        t = st.get("time", 0.0)
        if alpha <= 0.01:
            return
        D, ang, base = self.pose(st)
        items = []   # (depth, kind, payload)

        # roots first (they lie on the ground under the book)
        rg = st.get("roots", 1.0)
        if rg > 0 and roots_key:
            for k, r in enumerate(self.roots(roots_key, origin, scale)):
                gk = clamp(rg * 1.15 - k * 0.015)
                r.draw(cv, cam, grow=gk, t=t, alpha=alpha, lit=st.get("lit", 1.0), glow=1.0,
                       head=gk < 1)

        for bid in self.order:
            b = self.br[bid]
            f = clamp((g - b.g0) / max(1e-3, b.g1 - b.g0))
            if f <= 0:
                continue
            P = self._xf(D[bid], st, origin, scale)
            n = max(2, int(len(P) * f))
            P = P[:n]
            rad = (b.r0 + (b.r1 - b.r0) * b.u[:n]) * scale
            if f < 1:
                rad = rad * np.clip((n - np.arange(n)) / 6.0, 0.3, 1)
            sp, z = cam.project(P)
            if np.any(z < NEAR):
                continue
            items.append((float(z.mean()) + 0.02 * b.level, "branch", (bid, sp, rad * cam.fpx / z * 2, b.level)))
        # spheres
        for sph in self.spheres:
            b = self.br[sph["b"]]
            f = clamp((g - b.g1 + 0.05) / 0.2)
            if f <= 0:
                continue
            end, _ = self._attach(D, sph["b"], 1.0)
            rest_end = b.P[-1]
            ctr = sph["ctr"] - rest_end
            th = base[sph["b"]] + ang[sph["b"]]
            c, s = math.cos(th), math.sin(th)
            ctr = np.array([ctr[0] * c - ctr[1] * s, ctr[0] * s + ctr[1] * c, ctr[2]]) + end
            W = self._xf(ctr, st, origin, scale)
            sp, z = cam.project(W[None])
            items.append((float(z[0]), "sphere", (W, sph["r"] * scale, sph["code"], 0.6 + 0.4 * _pop(f))))
        # leaves
        for i, lf in enumerate(self.leaves):
            b = self.br[lf["b"]]
            f = clamp((g - (b.g1 - 0.05)) / 0.25 - i * 0.01)
            if f <= 0:
                continue
            att, _ = self._attach(D, lf["b"], lf["u"])
            rest_att = b.P[min(len(b.P) - 1, int(lf["u"] * (len(b.P) - 1)))]
            th = base[lf["b"]] + ang[lf["b"]] * (lf["u"] ** 1.3)
            v = lf["tip"] - rest_att
            c, s = math.cos(th), math.sin(th)
            v = np.array([v[0] * c - v[1] * s, v[0] * s + v[1] * c, 0.0])
            vlen = np.linalg.norm(v[:2]) + 1e-6
            base_ang = math.atan2(v[1], v[0])
            flutter = 0.10 * math.sin(t * 3.1 + lf["ph"]) + 0.05 * math.sin(t * 7.3 + lf["ph"] * 2)
            imp = st.get("impact")
            if imp is not None and imp >= 0:
                flutter += 0.45 * spring(imp - 0.04, 3.2, 3.5) * (1 if imp > 0.04 else 0) * (1 if i % 2 else -1)
            flip = math.cos(t * 1.7 + lf["ph"]) * 0.25 + 0.75
            Wp = self._xf(att + np.array([0, 0, lf["z"] * 0.2]), st, origin, scale)
            sp, z = cam.project(Wp[None])
            items.append((float(z[0]) - 0.01, "leaf", (sp[0], base_ang + flutter, lf["size"] * scale * _pop(f),
                                                         lf["shade"], flip, z[0])))
        # book
        if st.get("book", 1.0) > 0:
            bc = self._xf(np.array([0.25, -0.05, -0.55]), dict(st, sy=1 + (st.get("sy", 1) - 1) * 0.3, lean=0), origin, scale)
            items.append((float(cam.project(bc[None])[1][0]), "book", bc))

        items.sort(key=lambda x: -x[0])
        for z, kind, p in items:
            if kind == "branch":
                bid, sp, wpx, lv = p
                self._draw_branch(cv, sp, wpx, lv, alpha, bid)
            elif kind == "sphere":
                W, r, code, sc = p
                draw_sphere(cv, cam, W, r, code, alpha, scale=sc)
            elif kind == "leaf":
                self._draw_leaf(cv, cam, *p, alpha=alpha)
            elif kind == "book":
                self._draw_book(cv, cam, p, scale, st, alpha)

    def _draw_branch(self, cv, sp, wpx, lv, alpha, bid):
        sh = [
            (col("lip"), 1.0, 0.0),
            (mixc(col("bark"), col("purple"), 0.5), 0.82, 0.10),
            (col("purple"), 0.58, 0.22),
            (mixc(col("purple"), col("violet"), 0.8), 0.32, 0.30),
            (mixc(col("violet"), col("lav"), 0.7), 0.12, 0.36),
        ]
        tube(cv, sp, np.maximum(wpx, 1.0), sh, alpha)
        if bid == "trunk" or lv == 1:
            # warm golden bounce light from the book on the shadow side
            n = len(sp)
            k = max(2, int(n * (0.75 if bid == "trunk" else 0.3)))
            gold = mixc(col("gold"), col("violet"), 0.35)
            tube(cv, sp[:k], np.maximum(wpx[:k] * 0.12, 0.8), [(gold, 1.0, 0.0)], alpha * 0.55,
                 light=(0.38, 0.0), fade=None)
            # bark grooves
            d = np.gradient(sp, axis=0)
            nrm = np.c_[-d[:, 1], d[:, 0]] / (np.linalg.norm(d, axis=1, keepdims=True) + 1e-6)
            for o in (-0.22, 0.12, 0.30):
                gp = sp + nrm * (wpx[:, None] * o)
                tube(cv, gp, np.maximum(wpx * 0.05, 0.7), [(col("lip"), 1.0, 0.0)], alpha * 0.45)
            glow_line(cv, sp, wpx * 1.3, col("violet"), 0.04 * alpha)

    def _draw_leaf(self, cv, cam, p, ang, size, shade, flip, z, alpha=1.0):
        if z < NEAR:
            return
        spr = leaf_sprite(shade if flip > 0 else 2)
        h, w = spr.shape[:2]
        Lpx = size * 1.55 * cam.fpx / z
        if Lpx < 3:
            return
        sc = Lpx / h
        # map stem (w/2, h) -> p, axis up -> direction ang
        ca, sa = math.cos(ang), math.sin(ang)
        ux, uy = ca, -sa         # leaf axis on screen (y down)
        vx, vy = -uy, ux         # leaf width axis
        fx = abs(flip) * sc
        M = np.float32([[vx * fx, -ux * sc, 0], [vy * fx, -uy * sc, 0]])
        M[:, 2] = np.array(p) - M[:, :2] @ np.array([w / 2, h])
        r = int(Lpx + 4)
        x0, y0 = int(max(0, p[0] - r)), int(max(0, p[1] - r))
        x1, y1 = int(min(cv.W, p[0] + r)), int(min(cv.H, p[1] + r))
        if x1 <= x0 or y1 <= y0:
            return
        M[:, 2] -= [x0, y0]
        out = cv2.warpAffine(spr, M, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR)
        if flip < 0:
            out[..., :3] *= 0.7
        d = cv.rgb[y0:y1, x0:x1]
        d *= (1 - out[..., 3:4] * alpha)
        d += out[..., :3] * alpha
        glow_dot(cv, p[0] + ux * Lpx * 0.5, p[1] + uy * Lpx * 0.5, Lpx * 0.45, col("lav"), 0.03 * alpha)

    def _draw_book(self, cv, cam, bc, scale, st, alpha):
        spr = book_sprite()
        bh, bw = spr.shape[:2]
        wd = 10.6 * scale
        hd = wd * bh / bw
        corners = quad_corners(bc, [1, 0, 0], [0, 1, 0], wd, hd)
        glint = st.get("glint")
        tex = spr
        if glint is not None and 0 <= glint <= 1:
            tex = spr.copy()
            xx = np.linspace(-0.3, 1.3, bw)[None, :]
            yy = np.linspace(0, 1, bh)[:, None]
            band = np.exp(-((xx - glint * 1.6 + 0.3 + (yy - 0.5) * 0.25) / 0.05) ** 2) * 0.9
            tex[..., :3] += band[..., None] * np.array([1.0, 0.92, 0.6], np.float32) * tex[..., 3:4]
        draw_quad(cv, cam, tex, corners, alpha=alpha * st.get("book", 1.0), dof=False, fog=False)


def _pop(f):
    """0..1 -> overshooting pop-in."""
    if f >= 1:
        return 1.0
    x = f - 1
    return max(0.0, x * x * (2.7 * x + 1.7) + 1)
