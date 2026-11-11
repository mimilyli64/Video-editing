"""World objects: textured station quads, THE shared root renderer, chunky
lesson nodes (pucks), glossy flag spheres, atmosphere."""
import functools
import math

import cv2
import numpy as np
from PIL import Image, ImageDraw

from .. import config as C
from .gfx import (col, mixc, tube, tube_shades, glow_line, glow_dot, clamp, hash01, to_premult)
from .cam import norm

NEAR = 0.6
BG = np.array(col("navy"), np.float32)


# ------------------------------------------------------------------ polygons
def fill_poly(cv, pts, rgb, alpha=1.0, glow=0.0):
    pts = np.asarray(pts, np.float64)
    x0 = int(max(0, np.floor(pts[:, 0].min() - 2)))
    y0 = int(max(0, np.floor(pts[:, 1].min() - 2)))
    x1 = int(min(cv.W, np.ceil(pts[:, 0].max() + 2)))
    y1 = int(min(cv.H, np.ceil(pts[:, 1].max() + 2)))
    if x1 <= x0 or y1 <= y0 or alpha <= 0.003:
        return
    m = np.zeros((y1 - y0, x1 - x0), np.uint8)
    p = ((pts - [x0, y0]) * 16).astype(np.int32)
    cv2.fillPoly(m, [p], 255, cv2.LINE_AA, 4)
    a = m.astype(np.float32) * (alpha / 255.0)
    d = cv.rgb[y0:y1, x0:x1]
    d *= (1 - a[..., None])
    d += np.array(rgb, np.float32) * a[..., None]


# ------------------------------------------------------------------ station quads
def quad_corners(Cn, R, U, w, h):
    Cn, R, U = (np.asarray(v, float) for v in (Cn, R, U))
    return np.array([Cn - R * w / 2 + U * h / 2, Cn + R * w / 2 + U * h / 2,
                     Cn + R * w / 2 - U * h / 2, Cn - R * w / 2 - U * h / 2])


def draw_quad(cv, cam, tex, corners, alpha=1.0, dof=True, fog=True):
    """Warp a premultiplied RGBA texture onto the screen through the camera."""
    if alpha <= 0.003 or tex is None:
        return
    scr, z = cam.project(corners)
    if np.any(z < NEAR):
        return
    th, tw = tex.shape[:2]
    x0 = int(max(0, np.floor(scr[:, 0].min())))
    y0 = int(max(0, np.floor(scr[:, 1].min())))
    x1 = int(min(cv.W, np.ceil(scr[:, 0].max()) + 1))
    y1 = int(min(cv.H, np.ceil(scr[:, 1].max()) + 1))
    if x1 <= x0 or y1 <= y0:
        return
    # pre-shrink big textures that land small (avoid aliasing)
    span = max(np.linalg.norm(scr[1] - scr[0]), np.linalg.norm(scr[2] - scr[3]))
    src = tex
    sc = 1.0
    while span < src.shape[1] * 0.5 and src.shape[1] > 64:
        src = cv2.pyrDown(src)
        sc *= 0.5
    sh, sw = src.shape[:2]
    S = np.float32([[0, 0], [sw, 0], [sw, sh], [0, sh]])
    D = np.float32(scr - [x0, y0])
    M = cv2.getPerspectiveTransform(S, D)
    out = cv2.warpPerspective(src, M, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    zc = float(z.mean())
    if dof:
        coc = cam.coc(zc)
        if coc > 0.9:
            k = min(coc * 0.5, 40)
            if k > 6:
                small = cv2.resize(out, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
                small = cv2.GaussianBlur(small, (0, 0), k / 4)
                out = cv2.resize(small, (out.shape[1], out.shape[0]), interpolation=cv2.INTER_LINEAR)
            else:
                out = cv2.GaussianBlur(out, (0, 0), k)
    if fog:
        f = fog_amt(zc)
        if f > 0.01:
            out[..., :3] = out[..., :3] * (1 - f) + BG * out[..., 3:4] * f
    if alpha != 1.0:
        out *= alpha
    d = cv.rgb[y0:y1, x0:x1]
    d *= (1 - out[..., 3:4])
    d += out[..., :3]


def fog_amt(z):
    return clamp((z - 45.0) / 90.0) * 0.85


# ------------------------------------------------------------------ curves
def curve(ctrl, step=0.1, wobble=0.0, seed=0, wob_freq=0.35):
    """Catmull-Rom through control points, resampled to uniform arc length, with
    organic low-frequency wobble.  Returns (P (N,3), s (N,))."""
    ctrl = np.asarray(ctrl, float)
    ext = np.vstack([ctrl[0] * 2 - ctrl[1], ctrl, ctrl[-1] * 2 - ctrl[-2]])
    pts = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1:i + 3]
        seg = np.linalg.norm(p2 - p1)
        n = max(4, int(seg / step * 2))
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            pts.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    pts.append(ctrl[-1])
    P = np.array(pts)
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    L = d[-1]
    n = max(2, int(L / step) + 1)
    s = np.linspace(0, L, n)
    Q = np.stack([np.interp(s, d, P[:, k]) for k in range(3)], -1)
    if wobble:
        T = np.gradient(Q, axis=0)
        T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-9
        N = np.cross(T, [0, 0, 1.0])
        bad = np.linalg.norm(N, axis=1) < 0.2
        N[bad] = np.cross(T[bad], [1.0, 0, 0])
        N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-9
        B = np.cross(T, N)
        rng = np.random.RandomState(seed)
        ph = rng.rand(4) * 6.28
        env = np.minimum(1, np.minimum(s, L - s) / 0.8)
        w1 = (np.sin(s * wob_freq * 6.28 / 3 + ph[0]) + 0.5 * np.sin(s * wob_freq * 6.28 / 1.3 + ph[1])) * wobble * env
        w2 = (np.sin(s * wob_freq * 6.28 / 2.4 + ph[2]) + 0.4 * np.sin(s * wob_freq * 6.28 / 1.1 + ph[3])) * wobble * env
        Q = Q + N * w1[:, None] + B * w2[:, None]
    return Q, s


# ------------------------------------------------------------------ THE root
class Root:
    """One luminous, braided, dimensional purple root.  Every root, root branch,
    underline and waveform in the film is drawn by Root.draw()."""

    def __init__(self, ctrl, r0=0.22, r1=0.12, seed=1, wobble=0.10, rootlets=1.0,
                 strands=3, step=0.12, twist=1.6, hue=0.0, P=None):
        if P is None:
            self.P, self.s = curve(ctrl, step=step, wobble=wobble, seed=seed)
        else:
            self.P = np.asarray(P, float)
            self.s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(self.P, axis=0), axis=1))]
        self.L = self.s[-1]
        self.r0, self.r1 = r0, r1
        self.strands = strands
        self.twist = twist
        self.hue = hue
        self.seed = seed
        T = np.gradient(self.P, axis=0)
        T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-9
        N = np.cross(T, [0, 1.0, 0])
        bad = np.linalg.norm(N, axis=1) < 0.25
        N[bad] = np.cross(T[bad], [0, 0, 1.0])
        N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-9
        self.T, self.N, self.B = T, N, np.cross(T, N)
        # rootlets: small curling side roots
        rng = np.random.RandomState(seed * 7 + 3)
        self.rootlets = []
        if rootlets > 0 and self.L > 0.6:
            sp = 0.55 / rootlets
            u = 0.3 + rng.rand() * sp
            while u < self.L - 0.2:
                i = int(np.searchsorted(self.s, u))
                i = min(i, len(self.P) - 1)
                ang = rng.rand() * 6.28
                side = np.cos(ang) * self.N[i] + np.sin(ang) * self.B[i]
                side = side * 0.85 + np.array([0, -0.45, 0])
                ln = (0.35 + rng.rand() ** 1.6 * 1.4) * (0.5 + 0.5 * self.rad_at(u) / max(r0, 1e-3))
                curl = rng.randn(3) * 0.35
                pts = [self.P[i]]
                d = norm(side * 0.8 + self.T[i] * rng.uniform(-0.6, 0.9))
                for k in range(1, 6):
                    d = norm(d + curl * 0.35)
                    pts.append(pts[-1] + d * ln / 5)
                self.rootlets.append((u, np.array(pts), self.rad_at(u) * rng.uniform(0.3, 0.5),
                                      rng.rand() < 0.35))
                u += sp * (0.4 + rng.rand() * 1.2)

    def rad_at(self, u):
        return self.r0 + (self.r1 - self.r0) * (u / max(self.L, 1e-6))

    def point_at(self, frac):
        u = clamp(frac) * self.L
        return np.array([np.interp(u, self.s, self.P[:, k]) for k in range(3)])

    def draw(self, cv, cam, grow=1.0, t=0.0, alpha=1.0, glow=1.0, g0=0.0, head=True,
             pulses=True, rootlets=True, width=1.0, lit=1.0, offsets=None):
        """grow: visible fraction [g0, grow] of the root.  lit: lavender illumination."""
        if grow <= g0 or alpha <= 0.01:
            return
        u1 = grow * self.L
        u0 = g0 * self.L
        i0 = int(np.searchsorted(self.s, u0))
        i1 = int(np.searchsorted(self.s, u1))
        idx = np.arange(i0, min(i1 + 1, len(self.P)))
        if len(idx) < 2:
            return
        P = self.P[idx].copy()
        if offsets is not None:
            P += offsets[idx]
        if i1 < len(self.P) and grow < 1:
            # exact head
            P[-1] = self.point_at(grow) + (offsets[min(i1, len(offsets) - 1)] if offsets is not None else 0)
        su = self.s[idx]
        rad = (self.r0 + (self.r1 - self.r0) * su / self.L) * width
        if grow < 1:
            taper = np.clip((u1 - su) / 1.4, 0, 1) * 0.75 + 0.25
            rad = rad * taper
        scr, z = cam.project(P)
        ok = z > NEAR
        ppu = cam.fpx / np.maximum(z, NEAR)
        wpx = 2 * rad * ppu
        lav = col("lav")
        # --- glow underlay along the whole visible root
        runs = _runs(ok)
        for a, b in runs:
            sp, wp = _decimate(scr[a:b], wpx[a:b])
            if sp is None or not _onscreen(sp, cv, wp):
                continue
            glow_line(cv, sp, wp * 2.6 + 6 * cv.s, lav, 0.10 * glow * lit * alpha)
            glow_line(cv, sp, wp * 0.9 + 2, lav, 0.16 * glow * lit * alpha)
        # --- rootlets (behind the main strands)
        if rootlets:
            for (u, rp, rr, front) in self.rootlets:
                if u < u0 or u > u1 - 0.3 or front:
                    continue
                self._draw_rootlet(cv, cam, rp, rr * width, min(1.0, (u1 - u) / 0.8), alpha, lit, glow)
        # --- braided strands
        if self.strands > 1:
            ph0 = hash01(self.seed) * 6.28
            for k in range(self.strands):
                ph = ph0 + k * 6.28 / self.strands
                ang = ph + su * self.twist
                off = (np.cos(ang)[:, None] * self.N[idx] + np.sin(ang)[:, None] * self.B[idx]) * (rad * 0.42)[:, None]
                Ps = P + off
                ss, zs = cam.project(Ps)
                ws = 2 * rad * 0.66 * cam.fpx / np.maximum(zs, NEAR)
                shade = [("lip", "purple"), ("plum", "violet"), ("purple", "violet")][k % 3]
                self._tube_runs(cv, ss, ws, zs > NEAR, shade, alpha, lit)
        else:
            self._tube_runs(cv, scr, wpx, ok, ("lip", "purple"), alpha, lit)
        if rootlets:
            for (u, rp, rr, front) in self.rootlets:
                if u < u0 or u > u1 - 0.3 or not front:
                    continue
                self._draw_rootlet(cv, cam, rp, rr * width, min(1.0, (u1 - u) / 0.8), alpha, lit, glow)
        # --- travelling light pulses
        if pulses and lit > 0.05:
            Lvis = u1 - u0
            n = max(1, int(Lvis / 3.2))
            for k in range(n):
                u = u0 + ((t * 7.5 + k * 3.2 + hash01(self.seed, k) * 2) % max(Lvis, 1e-3))
                j = int(np.searchsorted(self.s, u))
                if j >= len(self.P):
                    continue
                pp = self.P[j] + (offsets[j] if offsets is not None else 0)
                sp, zz = cam.project(pp[None])
                if zz[0] < NEAR:
                    continue
                r = self.rad_at(u) * cam.fpx / zz[0] * width
                glow_dot(cv, sp[0, 0], sp[0, 1], r * 1.3 + 2, lav, 0.35 * glow * lit * alpha)
                glow_dot(cv, sp[0, 0], sp[0, 1], r * 0.5 + 1, (1, 1, 1), 0.25 * glow * lit * alpha)
        # --- growing head spark
        if head and grow < 0.999 and ok[-1]:
            hx, hy = scr[-1]
            r = max(3.0, wpx[-1] * 1.5)
            fl = 0.8 + 0.2 * math.sin(t * 60)
            glow_dot(cv, hx, hy, r * 3.2, lav, 0.35 * fl * alpha)
            glow_dot(cv, hx, hy, r * 1.2, (1, 0.95, 1), 0.9 * fl * alpha)
            rng = np.random.RandomState(int(t * 60) + self.seed)
            for _ in range(5):
                a = rng.rand() * 6.28
                d = rng.rand() * r * 4
                glow_dot(cv, hx + math.cos(a) * d, hy + math.sin(a) * d, 1.2 * cv.s + rng.rand() * 2, lav, 0.7 * alpha)

    def _tube_runs(self, cv, scr, wpx, ok, shade, alpha, lit):
        dark, base = shade
        sh = tube_shades(base=base, dark=dark, light_amt=0.55 + 0.45 * lit)
        for a, b in _runs(ok):
            sp, wp = _decimate(scr[a:b], wpx[a:b])
            if sp is None or not _onscreen(sp, cv, wp):
                continue
            if wp.max() < 2.5:
                sh2 = sh[:2] + sh[3:4]
            else:
                sh2 = sh
            tube(cv, sp, np.maximum(wp, 1.0), sh2, alpha)

    def _draw_rootlet(self, cv, cam, rp, rr, g, alpha, lit, glow):
        n = max(2, int(len(rp) * g))
        sp, z = cam.project(rp[:n])
        if np.any(z < NEAR):
            return
        if not _onscreen(sp, cv, np.array([20.0])):
            return
        w = 2 * rr * cam.fpx / z * np.linspace(1, 0.25, n)
        if w.max() < 0.7:
            return
        tube(cv, sp, np.maximum(w, 0.8), tube_shades(base="plum", dark="lip", light_amt=0.5 + 0.4 * lit)[:4], alpha * 0.95)
        glow_line(cv, sp, w * 1.8 + 2, col("lav"), 0.05 * glow * lit * alpha)


def _runs(ok):
    runs, i, n = [], 0, len(ok)
    while i < n:
        if ok[i]:
            j = i
            while j < n and ok[j]:
                j += 1
            if j - i >= 2:
                runs.append((i, j))
            i = j
        else:
            i += 1
    return runs


def _decimate(sp, wp, minpx=3.0):
    if len(sp) < 2:
        return None, None
    keep = [0]
    last = sp[0]
    for i in range(1, len(sp) - 1):
        if abs(sp[i, 0] - last[0]) + abs(sp[i, 1] - last[1]) >= minpx:
            keep.append(i)
            last = sp[i]
    keep.append(len(sp) - 1)
    return sp[keep], wp[keep]


def _onscreen(sp, cv, wp):
    m = float(np.max(wp)) + 10
    return not (sp[:, 0].max() < -m or sp[:, 0].min() > cv.W + m or sp[:, 1].max() < -m or sp[:, 1].min() > cv.H + m)


# ------------------------------------------------------------------ chunky 3D lesson nodes
def draw_puck(cv, cam, center, axis, radius, thick, lit=0.0, icon=None, alpha=1.0, glow=1.0, face=None):
    axis = norm(axis)
    X = np.array([1.0, 0, 0])
    e1 = X - axis * np.dot(X, axis)
    if np.linalg.norm(e1) < 0.3:
        Z = np.array([0, 0, 1.0])
        e1 = Z - axis * np.dot(Z, axis)
    e1 = norm(e1)
    e2 = np.cross(axis, e1)
    ang = np.linspace(0, 2 * np.pi, 40, endpoint=False)
    ring = np.cos(ang)[:, None] * e1 + np.sin(ang)[:, None] * e2
    c = np.asarray(center, float)
    top = c + axis * thick
    Pt = top + ring * radius
    Pb = c + ring * radius
    st, zt = cam.project(Pt)
    sb, zb = cam.project(Pb)
    if np.any(zt < NEAR) or np.any(zb < NEAR):
        return
    allp = np.vstack([st, sb]).astype(np.float32)
    if allp[:, 0].max() < -50 or allp[:, 0].min() > cv.W + 50 or allp[:, 1].max() < -50 or allp[:, 1].min() > cv.H + 50:
        return
    hull = cv2.convexHull(allp)[:, 0, :]
    lip = mixc(col("lip"), col("purple"), 0.35 * lit)
    fill_poly(cv, hull, lip, alpha)
    # side sheen on the lower band
    sc, zc = cam.project(c[None])
    face_c = face or mixc(col("purple"), col("violet"), lit)
    fill_poly(cv, st, face_c, alpha)
    ctop, _ = cam.project(top[None])
    ctr = ctop[0]
    inner = ctr + (st - ctr) * 0.80
    fill_poly(cv, inner, mixc(face_c, col("lav"), 0.25 + 0.55 * lit), alpha)
    inner2 = ctr + (st - ctr) * 0.62 + np.array([0, -0.06]) * np.ptp(st[:, 1])
    fill_poly(cv, inner2, mixc(mixc(face_c, col("lav"), 0.25 + 0.55 * lit), (1, 1, 1), 0.12 + 0.2 * lit), alpha * 0.55)
    if lit > 0.02:
        rx = np.ptp(st[:, 0]) / 2
        k = min(1.0, 160.0 * cv.s / max(rx, 1))
        glow_dot(cv, ctr[0], ctr[1], rx * 1.2, col("lav"), 0.09 * lit * glow * alpha * k)
        glow_dot(cv, ctr[0], ctr[1], rx * 0.45, col("lav"), 0.10 * lit * glow * alpha * k)
    if icon is not None:
        # affine map of the icon onto the top face
        a = cam.project((top + e1 * radius * 0.5)[None])[0][0]
        b = cam.project((top + e2 * radius * 0.5)[None])[0][0]
        h, w = icon.shape[:2]
        src = np.float32([[w / 2, h / 2], [w, h / 2], [w / 2, 0]])
        # e2 points "up" on the face when axis faces camera; choose the one that is screen-up
        up = b if b[1] < ctr[1] else ctr * 2 - b
        dst = np.float32([ctr, a, up])
        M = cv2.getAffineTransform(src, dst)
        rpx = max(np.ptp(st[:, 0]), np.ptp(st[:, 1])) / 2 + 4
        x0, y0 = int(max(0, ctr[0] - rpx)), int(max(0, ctr[1] - rpx))
        x1, y1 = int(min(cv.W, ctr[0] + rpx)), int(min(cv.H, ctr[1] + rpx))
        if x1 > x0 and y1 > y0:
            M[:, 2] -= [x0, y0]
            warped = cv2.warpAffine(icon, M, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR)
            d = cv.rgb[y0:y1, x0:x1]
            d *= (1 - warped[..., 3:4] * alpha)
            d += warped[..., :3] * alpha


# ------------------------------------------------------------------ flag spheres
def _flag(code, w=600, h=400):
    im = Image.new("RGB", (w, h), (255, 255, 255))
    d = ImageDraw.Draw(im)
    if code == "fr":
        d.rectangle([0, 0, w // 3, h], fill=(0, 85, 164))
        d.rectangle([2 * w // 3, 0, w, h], fill=(239, 65, 53))
    elif code == "de":
        d.rectangle([0, 0, w, h // 3], fill=(0, 0, 0))
        d.rectangle([0, h // 3, w, 2 * h // 3], fill=(221, 0, 0))
        d.rectangle([0, 2 * h // 3, w, h], fill=(255, 206, 0))
    elif code == "it":
        d.rectangle([0, 0, w // 3, h], fill=(0, 146, 70))
        d.rectangle([2 * w // 3, 0, w, h], fill=(206, 43, 55))
    elif code == "es":
        d.rectangle([0, 0, w, h], fill=(170, 21, 27))
        d.rectangle([0, h // 4, w, 3 * h // 4], fill=(241, 191, 0))
        x, y = int(w * 0.32), h // 2
        d.rounded_rectangle([x - 26, y - 34, x + 26, y + 34], 14, fill=(190, 40, 30), outline=(150, 100, 10), width=4)
        d.rectangle([x - 40, y - 30, x - 33, y + 34], fill=(190, 160, 120))
        d.rectangle([x + 33, y - 30, x + 40, y + 34], fill=(190, 160, 120))
        d.ellipse([x - 16, y - 56, x + 16, y - 36], fill=(200, 150, 20))
    elif code == "tr":
        d.rectangle([0, 0, w, h], fill=(227, 10, 23))
        cx, cy = int(w * 0.40), h // 2
        R1, R2 = int(h * 0.25), int(h * 0.20)
        d.ellipse([cx - R1, cy - R1, cx + R1, cy + R1], fill=(255, 255, 255))
        o = int(h * 0.0625)
        d.ellipse([cx + o - R2, cy - R2, cx + o + R2, cy + R2], fill=(227, 10, 23))
        sx, sy, rs = int(w * 0.55), cy, int(h * 0.125)
        pts = []
        for k in range(10):
            r = rs if k % 2 == 0 else rs * 0.4
            a = -math.pi + k * math.pi / 5
            pts.append((sx + r * math.cos(a), sy + r * math.sin(a)))
        d.polygon(pts, fill=(255, 255, 255))
    elif code == "uk":
        blue, red = (1, 33, 105), (200, 16, 46)
        d.rectangle([0, 0, w, h], fill=blue)
        lw = int(h * 0.2)
        d.line([(0, 0), (w, h)], fill=(255, 255, 255), width=lw)
        d.line([(0, h), (w, 0)], fill=(255, 255, 255), width=lw)
        lr = int(h * 0.066)
        # counterchanged red saltire (offset)
        off = lr * 0.5
        d.line([(0, 0 + off), (w / 2, h / 2 + off)], fill=red, width=lr)
        d.line([(w / 2, h / 2 - off), (w, h - off)], fill=red, width=lr)
        d.line([(0, h - off), (w / 2, h / 2 - off)], fill=red, width=lr)
        d.line([(w / 2, h / 2 + off), (w, 0 + off)], fill=red, width=lr)
        d.rectangle([w / 2 - h / 6, 0, w / 2 + h / 6, h], fill=(255, 255, 255))
        d.rectangle([0, h / 2 - h / 6, w, h / 2 + h / 6], fill=(255, 255, 255))
        d.rectangle([w / 2 - h / 10, 0, w / 2 + h / 10, h], fill=red)
        d.rectangle([0, h / 2 - h / 10, w, h / 2 + h / 10], fill=red)
    return np.asarray(im, np.float32) / 255.0


@functools.lru_cache(maxsize=16)
def sphere_sprite(code, size=384):
    flag = _flag(code)
    fh, fw = flag.shape[:2]
    ss = size * 2
    yy, xx = np.mgrid[0:ss, 0:ss].astype(np.float32)
    x = (xx + 0.5) / ss * 2 - 1
    y = (yy + 0.5) / ss * 2 - 1
    r2 = x * x + y * y
    inside = r2 <= 1
    nz = np.sqrt(np.clip(1 - r2, 0, 1))
    lon = np.arctan2(x, nz)
    lat = np.arcsin(np.clip(y, -1, 1))
    u = (0.5 + lon / np.pi * 0.98) * (fw - 1)
    v = (0.5 + lat / np.pi * 1.02) * (fh - 1)
    tex = cv2.remap(flag, u.astype(np.float32), v.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    L = np.array([-0.45, -0.6, 0.66])
    L /= np.linalg.norm(L)
    ndl = np.clip(x * L[0] + y * L[1] + nz * L[2], 0, 1)
    diff = 0.42 + 0.68 * ndl
    H = L + np.array([0, 0, 1.0])
    H /= np.linalg.norm(H)
    spec = np.clip(x * H[0] + y * H[1] + nz * H[2], 0, 1) ** 60 * 0.9
    rim = (1 - nz) ** 3
    rgb = tex * diff[..., None] + spec[..., None]
    rgb = rgb * (1 - rim[..., None] * 0.5) + np.array(col("lav"), np.float32) * rim[..., None] * 0.3
    # glossy glass highlight arc
    hl = np.exp(-(((x + 0.28) ** 2) / 0.05 + ((y + 0.48) ** 2) / 0.012)) * 0.45
    rgb = rgb + hl[..., None]
    a = np.clip((1 - np.sqrt(r2)) * ss * 0.5, 0, 1).astype(np.float32)
    out = np.zeros((ss, ss, 4), np.float32)
    out[..., :3] = np.clip(rgb, 0, 1.4) * a[..., None]
    out[..., 3] = a
    return cv2.resize(out, (size, size), interpolation=cv2.INTER_AREA)


def draw_sphere(cv, cam, center, radius, code, alpha=1.0, scale=1.0, glow=0.3):
    sp, z = cam.project(np.asarray(center, float)[None])
    if z[0] < NEAR:
        return None
    r = radius * scale * cam.fpx / z[0]
    if r < 1:
        return None
    spr = sphere_sprite(code, 384 if r < 160 else 768)
    from .gfx import blit
    # soft contact shadow / glow
    glow_dot(cv, sp[0, 0], sp[0, 1], r * 1.35, col("violet"), glow * 0.25 * alpha)
    blit(cv.rgb, spr, sp[0, 0], sp[0, 1], alpha, scale=(2 * r) / spr.shape[0], anchor="c")
    return sp[0], r


# ------------------------------------------------------------------ atmosphere
class Atmos:
    def __init__(self, seed=5):
        rng = np.random.RandomState(seed)
        n = 520
        self.P = np.c_[rng.uniform(-40, 40, n), rng.uniform(-14, 18, n), rng.uniform(-40, 330, n)]
        self.r = rng.uniform(0.02, 0.07, n)
        self.ph = rng.rand(n) * 6.28
        self.c = rng.rand(n)
        nb = 26
        self.B = np.c_[rng.uniform(-45, 45, nb), rng.uniform(-14, 20, nb), np.linspace(-20, 330, nb) + rng.uniform(-8, 8, nb)]
        self.Br = rng.uniform(8, 18, nb)
        self.Bc = rng.rand(nb)

    def draw_bg(self, cv, cam, t, dim=1.0):
        H, W = cv.H, cv.W
        lw, lh = W // 8, H // 8
        low = np.zeros((lh, lw, 3), np.float32)
        sp, z = cam.project(self.B)
        for i in range(len(self.B)):
            if z[i] < 2:
                continue
            r = self.Br[i] * cam.fpx / z[i] / 8
            if r < 2:
                continue
            c = mixc(col("purple"), col("violet"), self.Bc[i] * 0.6)
            k = 0.05 * min(1.0, 60 / z[i]) * dim
            cv2.circle(low, (int(sp[i, 0] / 8), int(sp[i, 1] / 8)), int(r), tuple(v * k for v in c), -1, cv2.LINE_AA)
        low = cv2.GaussianBlur(low, (0, 0), max(3, lw / 22))
        cv.rgb += cv2.resize(low, (W, H), interpolation=cv2.INTER_LINEAR)

    def draw_motes(self, cv, cam, t, dim=1.0):
        sp, z = cam.project(self.P)
        ok = (z > 1.0) & (sp[:, 0] > -20) & (sp[:, 0] < cv.W + 20) & (sp[:, 1] > -20) & (sp[:, 1] < cv.H + 20)
        for i in np.nonzero(ok)[0]:
            r = self.r[i] * cam.fpx / z[i]
            coc = cam.coc(z[i]) * 0.5
            rr = max(r, coc, 0.8 * cv.s)
            tw = 0.55 + 0.45 * math.sin(t * 2.3 + self.ph[i])
            inten = (0.5 + 0.5 * min(1, r / rr)) * tw * 0.55 * dim * min(1, 40 / z[i]) * (1 - fog_amt(z[i]) * 0.8)
            c = mixc(col("lav"), col("violet"), self.c[i])
            glow_dot(cv, sp[i, 0], sp[i, 1], rr, c, inten * min(1.0, 2.0 / rr + 0.15))
