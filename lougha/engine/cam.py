"""Real perspective camera + one continuous keyframed flight path."""
import math

import numpy as np

from .gfx import clamp, smooth


def norm(v):
    v = np.asarray(v, np.float64)
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


class Camera:
    def __init__(self, pos, target, fov, W, H, roll=0.0, focus=None, aperture=0.0):
        self.pos = np.asarray(pos, np.float64)
        self.target = np.asarray(target, np.float64)
        self.W, self.H = W, H
        self.fov = fov
        f = norm(self.target - self.pos)
        up = np.array([0.0, 1.0, 0.0])
        r = norm(np.cross(up, f))
        u = np.cross(f, r)
        if roll:
            c, s = math.cos(roll), math.sin(roll)
            r, u = r * c + u * s, -r * s + u * c
        self.f, self.r, self.u = f, r, u
        self.fpx = (H / 2) / math.tan(math.radians(fov) / 2)
        self.cx, self.cy = W / 2, H / 2
        self.focus = focus if focus is not None else float(np.linalg.norm(self.target - self.pos))
        self.aperture = aperture

    def to_cam(self, P):
        d = np.asarray(P, np.float64) - self.pos
        return np.stack([d @ self.r, d @ self.u, d @ self.f], -1)

    def project(self, P):
        """(...,3) world -> (...,2) screen px, (...) depth."""
        c = self.to_cam(P)
        z = c[..., 2]
        zs = np.where(z > 1e-3, z, 1e-3)
        x = self.cx + self.fpx * c[..., 0] / zs
        y = self.cy - self.fpx * c[..., 1] / zs
        return np.stack([x, y], -1), z

    def px_per_unit(self, z):
        return self.fpx / max(z, 1e-3)

    def coc(self, z):
        """Circle of confusion (px) for depth z."""
        if self.aperture <= 0:
            return 0.0
        return self.aperture * self.fpx * abs(z - self.focus) / max(z, 1e-3) / max(self.focus, 1e-3)


def catmull(p0, p1, p2, p3, t):
    t2, t3 = t * t, t * t * t
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)


class Path:
    """Keyframes: (t, pos, target, fov, ease, aperture).
    Positions/targets are Catmull-Rom interpolated; per-segment time is eased by
    `ease` in [0,1] (0 = constant speed through, 1 = settle into the key)."""

    def __init__(self, keys):
        self.keys = sorted(keys, key=lambda k: k[0])

    def sample(self, t):
        K = self.keys
        if t <= K[0][0]:
            k = K[0]
            return np.array(k[1], float), np.array(k[2], float), k[3], k[5]
        if t >= K[-1][0]:
            k = K[-1]
            return np.array(k[1], float), np.array(k[2], float), k[3], k[5]
        i = max(j for j in range(len(K) - 1) if K[j][0] <= t)
        k1, k2 = K[i], K[i + 1]
        u = (t - k1[0]) / (k2[0] - k1[0])
        e = k2[4]
        u = (1 - e) * u + e * smooth(u)
        k0 = K[max(0, i - 1)]
        k3 = K[min(len(K) - 1, i + 2)]
        P = [np.array(k[1], float) for k in (k0, k1, k2, k3)]
        T = [np.array(k[2], float) for k in (k0, k1, k2, k3)]
        pos = catmull(*P, u)
        tgt = catmull(*T, u)
        fov = k1[3] + (k2[3] - k1[3]) * smooth(u)
        ap = k1[5] + (k2[5] - k1[5]) * u
        return pos, tgt, fov, ap
