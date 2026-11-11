"""The world of "The Roots": stations, the root network, the camera flight and
every animated beat, for both the 16:9 and the re-laid-out 9:16 film."""
import math

import cv2
import numpy as np

from .. import config as C
from . import ui
from .cam import Camera, Path, norm
from .gfx import (blit, clamp, lin, smooth, ease_out, ease_in, back, spring, col, mixc, text_sprite,
                  glow_dot, hash01, text_w, tint)
from .tree import Tree
from .world import Root, Atmos, draw_quad, quad_corners, draw_puck, draw_sphere, NEAR, curve

D0 = 22.0
FOV = {"h": 34.0, "v": 2 * math.degrees(math.atan((2 * D0 * math.tan(math.radians(17)) * 16 / 9 / 2) / D0))}
WT = C.word_times()


def vis(fmt, D=D0):
    a = 2 * D * math.tan(math.radians(17))      # 16:9 visible height at D
    b = a * 16 / 9
    return (b, a) if fmt == "h" else (a, b)


class Plane:
    def __init__(self, Cn, w, h, dw, dh, tw, th, yaw=0.0):
        self.C = np.asarray(Cn, float)
        c, s = math.cos(yaw), math.sin(yaw)
        self.R = np.array([c, 0, -s])
        self.U = np.array([0, 1.0, 0])
        self.N = np.array([s, 0, c])
        self.w, self.h, self.dw, self.dh, self.tw, self.th = w, h, dw, dh, tw, th

    def corners(self, off=(0, 0, 0)):
        return quad_corners(self.C + np.asarray(off), self.R, self.U, self.w, self.h)

    def pt(self, u, v, dz=0.0):
        return self.C + self.R * u * self.w / 2 + self.U * v * self.h / 2 - self.N * dz

    def px(self, x, y, dz=0.0):
        return self.pt(x / self.dw * 2 - 1, 1 - y / self.dh * 2, dz)

    def home(self, D=D0, dmul=1.0, du=0.0, dv=0.0):
        tgt = self.C + self.R * du + self.U * dv
        return tgt - self.N * D * dmul, tgt


class Tex:
    """Drawing helper on a premultiplied texture in design units."""

    def __init__(self, tw, th, s):
        self.a = np.zeros((th, tw, 4), np.float32)
        self.s = s

    def text(self, txt, x, y, size, weight=700, color="white", anchor="tl", alpha=1.0, tracking=0.0):
        c = C.RGB[color] if isinstance(color, str) else color
        spr, base = text_sprite(txt, int(round(size * self.s)), weight, c, tracking)
        blit(self.a, spr, x * self.s, y * self.s, alpha, anchor=anchor)
        return spr.shape[1] / self.s

    def card(self, x, y, w, h, alpha=1.0, **kw):
        s = self.s
        if "r" in kw:
            kw["r"] = int(kw["r"] * s)
        if "lip" in kw:
            kw["lip"] = int(kw["lip"] * s)
        if "shadow" in kw:
            kw["shadow"] = int(kw["shadow"] * s)
        spr, ox, oy = ui.card(int(w * s), int(h * s), **kw)
        blit(self.a, spr, x * s - ox, y * s - oy, alpha)

    def spr(self, spr, x, y, anchor="tl", alpha=1.0, scale=1.0):
        blit(self.a, spr, x * self.s, y * self.s, alpha, scale=scale, anchor=anchor)

    def rect(self, x, y, w, h, color, alpha=1.0, r=0):
        s = self.s
        x0, y0, x1, y1 = int(x * s), int(y * s), int((x + w) * s), int((y + h) * s)
        c = np.array(col(color) if isinstance(color, str) else color, np.float32)
        if c.max() > 1.0:
            c = c / 255.0
        if r <= 0:
            reg = self.a[max(0, y0):y1, max(0, x0):x1]
            reg *= (1 - alpha)
            reg[..., :3] += c * alpha
            reg[..., 3] += alpha
            return
        m = np.zeros((y1 - y0 + 2, x1 - x0 + 2), np.uint8)
        rr = int(r * s)
        cv2.rectangle(m, (rr, 0), (x1 - x0 - rr, y1 - y0), 255, -1)
        cv2.rectangle(m, (0, rr), (x1 - x0, y1 - y0 - rr), 255, -1)
        for cx, cy in ((rr, rr), (x1 - x0 - rr, rr), (rr, y1 - y0 - rr), (x1 - x0 - rr, y1 - y0 - rr)):
            cv2.circle(m, (cx, cy), rr, 255, -1, cv2.LINE_AA)
        a = m.astype(np.float32)[..., None] / 255 * alpha
        spr = np.concatenate([c * a, a], -1)
        blit(self.a, spr, x0, y0)

    def bar(self, x, y, w, h, frac, alpha=1.0, track="lip", fill=("violet", "lav"), headglow=True):
        self.rect(x, y, w, h, track, alpha * 0.9, r=h / 2)
        fw = max(0.0, min(1.0, frac)) * w
        if fw > h * 0.5:
            self.rect(x, y, fw, h, fill[0], alpha, r=h / 2)
            self.rect(x + 2, y + 2, max(0, fw - 4), h * 0.38, fill[1], alpha * 0.55, r=h * 0.2)
            if headglow and frac < 0.999:
                g = ui.disc(int(h * 3 * self.s), top="lav", bot="violet", lip=0.0)
                blit(self.a, g, (x + fw) * self.s, (y + h / 2) * self.s, alpha * 0.35, anchor="c")


def tween(a, b, x):
    return a + (b - a) * x


# ====================================================================== WORLD
class World:
    def __init__(self, fmt, W, H):
        self.fmt = fmt
        self.W, self.H = W, H
        self.s = min(W, H) / 1080.0
        self.DW, self.DH = (1920, 1080) if fmt == "h" else (1080, 1920)
        self.fov = FOV[fmt]
        self.vw, self.vh = vis(fmt)
        self.tree = Tree()
        self.atmos = Atmos()
        v = fmt == "v"
        self.v = v

        def full(Cn, yaw=0.0):
            return Plane(Cn, self.vw, self.vh, self.DW, self.DH, W, H, yaw)

        # ---------------- stations
        self.O1 = np.array([0, -2.6 if not v else -1.2, 0.0])          # hook tree base
        self.tree_scale = 0.62 if not v else 0.78
        self.word1 = Plane(self.O1 + [0, -2.25 if not v else -2.9, -0.8], 11.0 if not v else 11.6,
                           3.3 if not v else 3.48, 1400, 420, int(1400 * self.s), int(420 * self.s))
        self.nodes = []
        for k in range(7):
            z = 8 + k * 4.6
            x = 3.4 * math.sin((k / 6) * math.pi * 1.5)
            self.nodes.append(np.array([x, -7.2, z]))
        jw, jh = (9.4, 6.2) if not v else (10.4, 8.4)
        self.jour = Plane([3.0, -3.0, 48], jw, jh, 940, 620 if not v else 840, int(940 * self.s), int((620 if not v else 840) * self.s))
        self.jour_D = (jw / 0.66) / (self.vw / D0)
        self.lesson = full([-3, 0, 80])
        self.prog = full([4, 3, 114])
        self.comm = full([-2, 0, 148])
        self.call = full([3, 1, 182], yaw=math.radians(-8))
        self.lang = full([3, 1, 212])
        self.sk = full([3, -15, 218])
        self.Oh = np.array([3, -5.6 if not v else -1.0, 217.4])           # hero tree base (above the tagline)
        self.hero_scale = 0.84 if not v else 0.98
        wy = -(1.65 * self.hero_scale + 1.15)
        self.word2 = Plane(self.Oh + [0, wy, -0.8], self.word1.w * 1.12, self.word1.h * 1.12, 1400, 420,
                           self.word1.tw, self.word1.th)
        self.endtag = Plane(self.Oh + [0, wy - (3.05 if not v else 3.6), -0.8], 15.6 if not v else 12.6,
                            3.36 if not v else 3.9, 1300 if not v else 1080, 280 if not v else 335,
                            int((1300 if not v else 1080) * self.s), int((280 if not v else 335) * self.s))
        self._build_roots()
        self._build_camera()

    # ------------------------------------------------------------------ roots
    def _build_roots(self):
        v = self.v
        R = {}
        O1 = self.O1
        sc = self.tree_scale
        # S1 seed root: from deep darkness toward the camera, ends at the tree base
        R["seed"] = Root([O1 + [0.0, 2.2, 60], O1 + [-1.0, 1.6, 38], O1 + [1.2, 0.8, 18], O1 + [-0.6, -0.2, 0], O1 + [0.6, -1.2, -9],
                          O1 + [0.0, -2.4, -14]], r0=0.05, r1=0.32, seed=2, wobble=0.45, rootlets=1.8)
        # wordmark underline: from the tree base, down, then left->right under the type
        wl, wr = self.word1.px(130, 400, 0.35), self.word1.px(1270, 400, 0.35)
        R["word1"] = Root([wl + [-0.8, 0.2, 0], wl, (wl + wr) / 2 + [0, -0.12, 0], wr, wr + [0.6, 0.15, 0]],
                          r0=0.13, r1=0.07, seed=4, wobble=0.05, rootlets=0.9, strands=3)
        # S2: hook -> S-curve of nodes -> journey card
        jb = self.jour.pt(-0.7, -1.0, 0.4)
        pts = [O1 + [0.2, -0.4, -0.3], O1 + [0.3, -3.4, 3.0]]
        for n in self.nodes:
            pts.append(n + [0, 0.42, 0])
        pts += [jb + [-1.2, -2.6, -1.0], jb, self.jour.pt(0.75, -1.0, 0.4)]
        R["path"] = Root(pts, r0=0.30, r1=0.22, seed=6, wobble=0.18, rootlets=1.0)
        self.node_frac = []
        for n in self.nodes:
            d = np.linalg.norm(R["path"].P - (n + [0, 0.42, 0]), axis=1)
            self.node_frac.append(R["path"].s[np.argmin(d)] / R["path"].L)
        # S3: journey -> lesson bottom, then along under the lesson card
        lb = self.lesson
        a = self.jour.pt(0.75, -1.0, 0.4)
        R["to_lesson"] = Root([a, a + [1.5, -2.5, 6], lb.pt(0.75, -1.25, 6.0), lb.pt(0.2, -0.98, 2.0), lb.pt(-0.86, -0.90, 0.6),
                               lb.pt(-0.92, -0.84, 0.6)], r0=0.24, r1=0.2, seed=8, wobble=0.15)
        R["lesson_under"] = Root([lb.pt(-0.92, -0.84, 0.6), lb.pt(-0.5, -0.88, 0.6), lb.pt(0.0, -0.86, 0.6), lb.pt(0.5, -0.88, 0.6),
                                  lb.pt(0.90, -0.84, 0.6)], r0=0.2, r1=0.16, seed=9, wobble=0.08, rootlets=1.4)
        # S4: lesson -> progress, leans out and curls up into the young tree
        pg = self.prog
        tb = self.prog_tree_origin()
        R["to_prog"] = Root([lb.pt(0.90, -0.84, 0.6), lb.pt(1.2, -1.1, -4), pg.pt(-0.2, -1.4, 6), pg.pt(0.1 if v else -0.3, -0.95, 2.5)] + ([pg.pt(0.93, -0.6, 1.2), pg.pt(0.93, 0.12, 1.2)] if v else []) + [
                             tb + [1.4, -0.6, -0.5], tb + [0.9, 0.1, -0.4], tb + [0.35, 0.2, -0.2], tb + [0.0, 0.3, 0]],
                            r0=0.24, r1=0.30, seed=10, wobble=0.12)
        R["prog_under"] = Root([pg.pt(0.1 if v else -0.3, -0.95, 2.5), pg.pt(0.5, -0.9, 0.6), pg.pt(0.95, -0.86, 0.6)],
                               r0=0.18, r1=0.12, seed=12, wobble=0.1, rootlets=1.4)
        # S5
        cm = self.comm
        R["to_comm"] = Root([pg.pt(0.95, -0.86, 0.6), pg.pt(1.3, -1.2, -3), cm.pt(0.6, -1.3, 5), cm.pt(-0.6, -0.92, 0.6),
                             cm.pt(0.95, -0.9, 0.6)], r0=0.22, r1=0.18, seed=14, wobble=0.12)
        # S6
        ca = self.call
        R["to_call"] = Root([cm.pt(0.95, -0.9, 0.6), cm.pt(1.3, -1.3, -3), ca.pt(-0.4, -1.4, 5), ca.pt(-0.92, -0.94, 0.6),
                             ca.pt(0.95, -0.94, 0.6)], r0=0.22, r1=0.18, seed=16, wobble=0.12)
        # waveform root (inside the student's tile)
        x0, x1, y = self.call_wave_span()
        wpts = np.array([ca.px(x, y, 0.35) for x in np.linspace(x0, x1, 160)])
        R["wave"] = Root(None, r0=0.10, r1=0.10, seed=18, rootlets=0.0, strands=2, twist=3.0, P=wpts)
        self.wave_N = len(wpts)
        # S7: call -> language hub; three branches; then down to the skills
        la = self.lang
        hub = la.pt(0, -0.72 if not v else -0.80, 0.8)
        self.hub = hub
        R["to_lang"] = Root([ca.pt(0.95, -0.94, 0.6), ca.pt(1.2, -1.3, -2), la.pt(0.5, -1.4, 8), hub + [0.6, -1.4, 1.5], hub],
                            r0=0.24, r1=0.28, seed=20, wobble=0.15)
        self.flag_pos = self.lang_flag_pos()
        R["br"] = []
        for k, fp in enumerate(self.flag_pos):
            mid = (hub + fp) / 2 + np.array([(-1) ** k * 0.6, -0.4, -0.4])
            R["br"].append(Root([hub, hub + (fp - hub) * 0.25 + [0, 0.35, 0], mid, fp + [0, -self.flag_r() * 1.0, 0.3]],
                                r0=0.24, r1=0.12, seed=30 + k, wobble=0.12, rootlets=1.2))
        sk = self.sk
        self.skill_pos = self.skill_positions()
        top = sk.pt(0, 0.95 if not v else 0.88, 0.8)
        self.sk_hub = sk.pt(0, 0.55 if not v else 0.62, 0.8)
        R["to_skills"] = Root([hub, hub + [0, -1.6, -0.5], hub + [0.0, -4.0, 0.0], top + [0, 1.5, 0], top, self.sk_hub],
                              r0=0.28, r1=0.26, seed=40, wobble=0.18)
        R["sk"] = []
        for k, p in enumerate(self.skill_pos):
            mid = (self.sk_hub + p) / 2 + np.array([0, 0.5 if not v else 0.2, -0.3])
            R["sk"].append(Root([self.sk_hub, mid, p + [0, self.skill_r() * 1.05, 0.2]], r0=0.22, r1=0.14, seed=50 + k,
                                wobble=0.10, rootlets=1.2))
        # S8: converge into one line that becomes the tagline's baseline
        ux0, ux1, uy = self.tag_underline()
        conv = sk.px(ux0, uy, 0.4)
        self.conv = conv
        R["conv"] = []
        for k, p in enumerate(self.skill_pos):
            R["conv"].append(Root([p, (p + conv) / 2 + [0, -0.6, -0.4], conv], r0=0.16, r1=0.20, seed=60 + k, wobble=0.12,
                                  rootlets=0.6))
        uend = sk.px(ux1, uy, 0.4)
        R["under"] = Root([conv, sk.px((ux0 + ux1) / 2, uy + 6, 0.4), uend], r0=0.20, r1=0.14, seed=70, wobble=0.04,
                          rootlets=1.0)
        # S9: underline -> hero tree base
        Oh = self.Oh
        R["to_hero"] = Root([uend, uend + [1.2, 1.2, -0.3], Oh + [4.2, -1.8, -0.6], Oh + [1.4, -0.6, -0.4],
                             Oh + [0, 0.1, -0.2]], r0=0.20, r1=0.28, seed=72, wobble=0.12)
        wl2, wr2 = self.word2.px(130, 400, 0.35), self.word2.px(1270, 400, 0.35)
        R["word2"] = Root([wl2 + [-0.8, 0.2, 0], wl2, (wl2 + wr2) / 2 + [0, -0.12, 0], wr2, wr2 + [0.6, 0.15, 0]],
                          r0=0.13, r1=0.07, seed=74, wobble=0.05, rootlets=0.9)
        self.R = R

    def prog_tree_origin(self):
        return self.prog.pt(-0.56, -0.62, 0.8) if not self.v else self.prog.pt(0.0, 0.26, 0.8)

    def call_wave_span(self):
        if not self.v:
            return 1010, 1720, 700
        return 90, 990, 1300

    def flag_r(self):
        return 1.55 if not self.v else 1.45

    def lang_flag_pos(self):
        la = self.lang
        if not self.v:
            return [la.pt(-0.56, 0.02, 0.8), la.pt(0.0, 0.10, 0.8), la.pt(0.56, 0.02, 0.8)]
        return [la.pt(-0.40, 0.22, 0.8), la.pt(0.40, 0.0, 0.8), la.pt(-0.28, -0.28, 0.8)]

    def skill_r(self):
        return 1.45 if not self.v else 1.55

    def skill_positions(self):
        sk = self.sk
        if not self.v:
            return [sk.pt(u, 0.0, 0.9) for u in (-0.66, -0.22, 0.22, 0.66)]
        return [sk.pt(-0.46, 0.22, 0.9), sk.pt(0.46, 0.22, 0.9), sk.pt(-0.46, -0.26, 0.9), sk.pt(0.46, -0.26, 0.9)]

    def tag_underline(self):
        if not self.v:
            return 300, 1620, 745
        return 120, 960, 1330

    # ------------------------------------------------------------------ camera
    def _build_camera(self):
        v = self.v
        fv = self.fov
        K = []

        def k(t, pos, tgt, ease=0.6, fov=None, ap=0.35):
            K.append((t, list(pos), list(tgt), fov or fv, ease, ap))

        O1 = self.O1
        cy = O1[1] + 10.4 * self.tree_scale * 0.5
        d_slam = 18.0 if not v else 15.5
        d_rev = 24.5 if not v else 23.0
        rev_y = O1[1] - 0.8 if not v else O1[1] + 1.0
        k(0.00, [0, cy, -d_slam], [0, cy, 0], 0)
        k(0.17, [0, cy, -d_slam], [0, cy, 0], 0)
        k(0.75, [0, cy - 0.9, -d_slam - 4.5], [0, rev_y + 0.4, 0], 0.4)
        k(1.30, [0, rev_y + 0.3, -d_rev], [0, rev_y, 0], 0.8)
        k(1.47, [0, rev_y + 0.1, -d_rev + 1.0], [0, rev_y - 0.4, 0], 0.5)
        # dive into the roots
        k(1.67, [0.0, -3.2, -6.0], [0.6, -6.8, 8.0], 0.0)
        n = self.nodes
        k(1.86, n[1] + [-1.4, 4.2, -7], n[3] + [0, 0.2, 0], 0.0)
        k(2.05, n[4] + [-2.0, 4.6, -6], n[6] + [0, 1.6, 4], 0.0)
        jp, jt = self.jour.home(self.jour_D)
        k(2.27, jp + [0, -0.4, -2], jt, 0.7)
        jp2, jt2 = self.jour.home(self.jour_D, 0.94)
        k(2.62, jp2, jt2, 0.4)
        # to lesson (push in)
        lp, lt = self.lesson.home(D0, 1.10)
        k(2.80, (np.array(jp2) + np.array(lp)) / 2 + [0, -2.6, 0], self.lesson.pt(0, -0.4), 0.0)
        k(2.93, lp, lt, 0.5)
        lp2, lt2 = self.lesson.home(D0, 1.0)
        k(3.35, lp2, lt2, 0.8)
        lp3, lt3 = self.lesson.home(D0, 0.97, du=0.3)
        k(4.72, lp3, lt3, 0.3)
        # progress
        pg = self.prog
        k(4.92, (np.array(lp3) + np.array(pg.home()[0])) / 2 + [0, -1.5, -6], pg.pt(-0.3, 0), 0.0)
        pp, pt_ = pg.home(D0, 1.06, du=-1.5 if not v else 0, dv=0 if not v else 1.0)
        k(5.12, pp, pt_, 0.6)
        pp2, pt2 = pg.home(D0, 0.99, du=0.4 if not v else 0, dv=0 if not v else -0.3)
        k(6.95, pp2, pt2, 0.3)
        # community (arrive ON the drop)
        cm = self.comm
        k(7.07, (np.array(pp2) + np.array(cm.home()[0])) / 2 + [0, -1.2, 0], cm.pt(0.2, 0), 0.0)
        cp, ct = cm.home(D0, 1.03)
        k(7.20, cp, ct, 0.85)
        cp2, ct2 = cm.home(D0, 0.96, du=0.3)
        k(9.05, cp2, ct2, 0.3)
        # call: orbit around the floating interface
        ca = self.call

        def orbit(a_deg, dm=1.0):
            a = math.radians(a_deg)
            dirv = ca.N * math.cos(a) + ca.R * math.sin(a)
            return ca.C - dirv * D0 * dm, ca.C
        k(9.20, (np.array(cp2) + np.array(orbit(-14)[0])) / 2 + [0, -1, 0], ca.pt(-0.2, 0), 0.0)
        p, tg = orbit(-12, 1.04)
        k(9.36, p, tg, 0.6)
        p, tg = orbit(0, 0.99)
        k(10.30, p, tg, 0.0)
        p, tg = orbit(10, 0.96)
        k(11.15, p, tg, 0.4)
        # push into the call, then FAST pull-back onto the three languages
        k(11.38, ca.C - ca.N * 7.0, ca.C + ca.N * 10, 0.6, fov=fv)
        la = self.lang
        k(11.52, la.C - la.N * 34.0, la.pt(0, -0.2), 0.0, fov=fv * 0.55)
        lp, lt = la.home(D0, 1.14)
        k(11.80, lp, lt, 0.9)
        fx = [p[0] - la.C[0] for p in self.flag_pos]
        fy = [p[1] - la.C[1] for p in self.flag_pos]
        lp, lt = la.home(D0, 1.10, du=fx[0] * 0.18, dv=fy[0] * 0.12)
        k(12.20, lp, lt, 0.5)
        lp, lt = la.home(D0, 1.08, du=fx[1] * 0.18, dv=fy[1] * 0.12)
        k(12.75, lp, lt, 0.5)
        lp, lt = la.home(D0, 1.08, du=fx[2] * 0.18, dv=fy[2] * 0.12)
        k(13.22, lp, lt, 0.5)
        # down to the four skills; travel through them
        sk = self.sk
        sp_ = self.skill_pos
        dm = 0.74 if not v else 0.86

        def at_skill(i, dm_=dm):
            p = sp_[i]
            return sk.home(D0, dm_, du=p[0] - sk.C[0], dv=(p[1] - sk.C[1]) * (0.5 if not v else 0.8))
        p0, t0 = at_skill(0)
        k(13.40, (np.array(lp) + np.array(p0)) / 2 + [0, 1.0, -2], sk.pt(-0.3, 0.6), 0.0)
        k(13.62, p0, t0, 0.6)
        k(13.98, *at_skill(1), 0.5)
        k(14.30, *at_skill(2), 0.5)
        k(14.62, *at_skill(3), 0.5)
        # pull back: the four skills merge, the tagline appears
        sp, st = sk.home(D0, 1.0)
        k(15.05, sp, st, 0.7)
        sp2, st2 = sk.home(D0, 0.95)
        k(16.05, sp2, st2, 0.3)
        sp2, st2 = np.array(sp2), np.array(st2)
        # crane up and back from the tagline to the hero space, breath, landing
        Oh = self.Oh
        hc = Oh + [0, 10.4 * self.hero_scale * 0.5 - (2.5 if not v else 0.2), 0]
        dh = 24.5 if not v else 24.0
        k(16.30, sp2 + [0, 0.3, -0.4], st2 + [0, 0.4, 0], 0.4)
        k(16.62, hc - [0, 0, dh + 0.6], hc, 0.8)
        k(16.80, hc - [0, 0, dh - 0.7], hc, 0.0)
        k(19.20, hc - [0, 0.4, dh + 1.2], hc - [0, 0.4, 0], 0.5)
        # end card: rise and settle to fit the tagline
        e_y = -2.6 if not v else -3.0
        k(20.30, hc - [0, -e_y, dh + 3.2], hc + [0, e_y, 0], 0.8)
        k(21.20, hc - [0, -e_y, dh + 3.5], hc + [0, e_y, 0], 0.3)
        self.path = Path(K)

    def camera(self, t):
        pos, tgt, fov, ap = self.path.sample(t)
        # impact shake
        sh = 0.0
        for th, amp in ((C.HIT["slam"], 0.30), (C.HIT["land"], 0.26), (C.HIT["drop"], 0.10)):
            dt = t - th
            if 0 <= dt < 0.6:
                sh += amp * math.exp(-dt * 9)
        roll = 0.0
        if sh > 0:
            r = np.random.RandomState(int(t * 600) % 100000)
            off = (r.rand(3) - 0.5) * sh
            pos = pos + off
            tgt = tgt + off * 0.4
            roll = (r.rand() - 0.5) * sh * 0.05
        foc = float(np.linalg.norm(np.asarray(tgt) - pos))
        return Camera(pos, tgt, fov, self.W, self.H, roll=roll, focus=foc, aperture=ap)

    # ================================================================== beats
    # -- growth schedule for every root (t0, t1)
    def grows(self, t):
        g = {}
        g["seed"] = lin(t, 0.0, 0.19) ** 2.2
        g["word1"] = smooth(lin(t, 0.45, 1.00))
        g["path"] = lin(t, 1.42, 2.22)
        g["to_lesson"] = smooth(lin(t, 2.42, 2.96))
        g["lesson_under"] = smooth(lin(t, 2.96, 4.70))
        g["to_prog"] = smooth(lin(t, 4.72, 5.45))
        g["prog_under"] = smooth(lin(t, 5.3, 6.9))
        g["to_comm"] = smooth(lin(t, 6.88, 7.22))
        g["to_call"] = smooth(lin(t, 9.02, 9.40))
        g["wave"] = smooth(lin(t, 10.05, 10.30))
        g["to_lang"] = smooth(lin(t, 11.36, 11.62))
        g["br"] = [smooth(lin(t, WT["en"] - 0.30, WT["en"] + 0.05)), smooth(lin(t, WT["fr"] - 0.30, WT["fr"] + 0.05)),
                   smooth(lin(t, WT["de"] - 0.30, WT["de"] + 0.05))]
        g["to_skills"] = smooth(lin(t, 13.22, 13.62))
        sk_t = [WT["speaking"], WT["listening"], WT["reading"], WT["writing"]]
        g["sk"] = [smooth(lin(t, x - 0.22, x + 0.02)) for x in sk_t]
        g["conv"] = [smooth(lin(t, 14.80 + 0.04 * k, 15.12 + 0.04 * k)) for k in range(4)]
        g["under"] = smooth(lin(t, WT["strong_roots_2"] - 0.05, WT["endless"] + 0.75))
        g["to_hero"] = smooth(lin(t, 16.10, 16.70))
        g["word2"] = smooth(lin(t, WT["logo"] - 0.30, WT["logo"] + 0.25))
        return g

    # ------------------------------------------------------------------ draw everything
    def draw(self, cv, cam, t):
        g = self.grows(t)
        groups = []   # (depth, fn)

        def add(point, fn):
            z = float(cam.project(np.asarray(point, float)[None])[1][0])
            groups.append((z, fn))

        # ---- S1/S9 trees, wordmarks
        if t < 2.2:
            add(self.O1 + [0, 0, 0.5], lambda: self.draw_hook(cv, cam, t, g))
        if 1.3 < t < 3.0:
            add(self.nodes[3], lambda: self.draw_nodes(cv, cam, t, g))
        if 1.85 < t < 3.1:
            add(self.jour.C, lambda: self.draw_jour(cv, cam, t, g))
        if 2.3 < t < 5.2:
            add(self.lesson.C, lambda: self.draw_lesson(cv, cam, t, g))
        if 4.6 < t < 7.4:
            add(self.prog.C, lambda: self.draw_prog(cv, cam, t, g))
        if 6.8 < t < 9.6:
            add(self.comm.C, lambda: self.draw_comm(cv, cam, t, g))
        if 9.0 < t < 11.47:
            add(self.call.C, lambda: self.draw_call(cv, cam, t, g))
        if 11.3 < t < 13.9:
            add(self.lang.C, lambda: self.draw_lang(cv, cam, t, g))
        if 13.1 < t < 16.7:
            add(self.sk.C, lambda: self.draw_skills(cv, cam, t, g))
        if t > 16.2:
            add(self.Oh + [0, 0, 0.5], lambda: self.draw_hero(cv, cam, t, g))
        groups.sort(key=lambda x: -x[0])
        for z, fn in groups:
            fn()

    # ------------------------------------------------------------------ S1 hook
    def tree_state(self, t, t_land, grow=1.0, extra=None):
        st = dict(time=t, grow=grow, roots=1.0, lit=1.0)
        fall = 0.17
        if t < t_land:
            x = clamp((t - (t_land - fall)) / fall)
            st["dy"] = (1 - ease_in(x, 2)) * 14.0
            st["sy"] = 1.10
            st["alpha"] = 1.0 if x > 0 else 0.0
            st["roots"] = 0.0
            st["impact"] = None
        else:
            d = t - t_land
            st["impact"] = d * C.TS          # springs run in real seconds (stay snappy)
            st["sy"] = 1.0 - 0.20 * spring(d * C.TS, 2.6, 5.5)
            st["roots"] = ease_out(clamp(d / 0.55), 2)
        if extra:
            st.update(extra)
        return st

    def draw_hook(self, cv, cam, t, g):
        R = self.R
        if t < 0.55:
            R["seed"].draw(cv, cam, grow=g["seed"], t=t, alpha=1 - smooth(lin(t, 0.25, 0.55)), glow=1.4)
        st = self.tree_state(t, C.HIT["slam"])
        if t >= C.HIT["book_glint"] - 0.2:
            st["glint"] = lin(t, C.HIT["book_glint"], C.HIT["book_glint"] + 0.45) if t < C.HIT["book_glint"] + 0.5 else None
        st["gesture"] = t - C.HIT["tree_gesture"] if t > C.HIT["tree_gesture"] else None
        if t > C.HIT["tree_gesture"]:
            gg = t - C.HIT["tree_gesture"]
            st["lean"] = 0.05 * math.sin(gg * 7.5) * math.exp(-gg * 3)
        if t > 1.62:
            st["alpha"] = 1 - smooth(lin(t, 1.62, 1.95))
        if st.get("alpha", 1) > 0:
            self.tree.draw(cv, cam, self.O1, self.tree_scale, st, roots_key="hook")
        # wordmark + underline root
        a = 1 - smooth(lin(t, 1.48, 1.64))
        if g["word1"] > 0 and a > 0:
            self.draw_wordmark(cv, cam, self.word1, g["word1"], t, a)
            R["word1"].draw(cv, cam, grow=g["word1"], t=t, alpha=a)

    def draw_wordmark(self, cv, cam, plane, reveal, t, alpha):
        tex = wordmark_tex(plane.tw, plane.th, self.s)
        x = int(plane.tw * (0.06 + 0.92 * reveal))
        m = np.zeros(plane.tw, np.float32)
        edge = int(40 * self.s)
        ramp = np.clip((x - np.arange(plane.tw)) / max(1, edge), 0, 1)
        out = tex * ramp[None, :, None]
        draw_quad(cv, cam, out, plane.corners(), alpha=alpha, dof=False)
        if 0 < reveal < 1:
            hp = plane.px(x / self.s / (plane.tw / self.s) * 1400, 210, 0.3)
            sp, z = cam.project(hp[None])
            glow_dot(cv, sp[0, 0], sp[0, 1], 22 * self.s, col("lav"), 0.10 * alpha)

    # ------------------------------------------------------------------ S2 nodes + journey card
    def draw_nodes(self, cv, cam, t, g):
        R = self.R
        a = 1 - smooth(lin(t, 2.55, 2.95))
        R["path"].draw(cv, cam, grow=g["path"], t=t, alpha=a)
        icons = ["book", "speakwave", "headphones", "pen", "chat", "star", "leaf"]
        for k, n in enumerate(self.nodes):
            lit = clamp((g["path"] - self.node_frac[k]) / 0.025)
            pop = 1 + 0.18 * spring(t - (1.42 + self.node_frac[k] * 0.8), 4, 7) * (lit > 0)
            draw_puck(cv, cam, n, [0, 1, 0], 1.05 * pop, 0.42, lit=lit, alpha=a,
                      icon=ui.icon(icons[k], int(120 * self.s), "white"))

    def draw_jour(self, cv, cam, t, g):
        pl = self.jour
        rise = back(lin(t, 1.92, 2.22), 1.2)
        dy = (1 - rise) * -6.5
        a = smooth(lin(t, 1.92, 2.05)) * (1 - smooth(lin(t, 2.82, 3.05)))
        if a <= 0:
            return
        tex = Tex(pl.tw, pl.th, self.s)
        v = self.v
        W_, H_ = 940, (620 if not v else 840)
        tex.card(20, 20, W_ - 40, H_ - 60, r=46, lip=16, shadow=20, top="deep", bot="plum", border=0.4)
        tex.spr(ui.avatar("A", int(84 * self.s), 0), 60, 58)
        tex.text(C.UI["journey_title"], 166, 54, 42, 800)
        tex.text(C.UI["journey_sub"], 166, 108, 30, 600, "lav")
        tex.text(C.UI["journey_unit"], 60, 182, 34, 700, "mist")
        # mini journey path
        n = 6
        px0, px1, py = 90, 850, 290
        for k in range(n):
            x = px0 + (px1 - px0) * k / (n - 1)
            if k < n - 1:
                done = k < 3
                tex.rect(x, py - 5, (px1 - px0) / (n - 1), 10, "violet" if done else "lip", 0.9)
        for k in range(n):
            x = px0 + (px1 - px0) * k / (n - 1)
            if k < 3:
                tex.spr(ui.disc(int(70 * self.s), "lav", "violet"), x, py, "c")
                tex.spr(ui.icon("check", int(40 * self.s)), x, py - 4, "c")
            elif k == 3:
                pulse = 0.5 + 0.5 * math.sin(t * 9)
                tex.spr(ui.disc(int(96 * self.s), "gold", (230, 160, 20), lip=0.06), x, py + 4, "c", alpha=0.25 * pulse)
                tex.spr(ui.disc(int(78 * self.s), "violet", "purple", ring="lav"), x, py, "c")
                tex.spr(ui.icon("play", int(36 * self.s)), x + 3, py - 3, "c")
            else:
                tex.spr(ui.disc(int(64 * self.s), "plum", "lip"), x, py, "c")
        # START button
        by = 420 if not v else 560
        press = C.HIT["start_press"]
        pr = 1 - 0.07 * clamp(1 - abs(t - press) / 0.09)
        lit = 0.35 * clamp(1 - abs(t - press - 0.05) / 0.25)
        bw, bh = 400 * pr, 110 * pr
        tex.card(470 - bw / 2, by + (1 - pr) * 40, bw, bh, r=int(55 * pr), lip=int(14 * pr), shadow=14,
                 top=mixc(C.RGB["violet"], C.RGB["lav"], 0.2 + lit), bot="violet", border=0.6, hi=0.4)
        tex.text(C.UI["start"], 470, by + (1 - pr) * 40 + bh / 2 - 4, 42 * pr, 900, "white", anchor="c", tracking=0.08)
        # touch indicator
        if press - 0.35 < t < press + 0.4:
            mv = smooth(lin(t, press - 0.35, press - 0.04))
            fx = tween(760, 520, mv)
            fy = tween(by + 260, by + 70, mv)
            tex.spr(ui.disc(int(64 * self.s), "white", (230, 220, 255), lip=0.0), fx, fy, "c", alpha=0.85 * (1 - lin(t, press + 0.2, press + 0.4)))
            if t > press:
                rr = lin(t, press, press + 0.4)
                ring = ui.disc(int((80 + 260 * rr) * self.s), "lav", "lav", lip=0.0)
                inner = ui.disc(int((70 + 250 * rr) * self.s), "deep", "deep", lip=0.0)
                tex.spr(ring, 470, by + 55, "c", alpha=0.35 * (1 - rr))
        draw_quad(cv, cam, tex.a, pl.corners((0, dy, 0)), alpha=a)

    # ------------------------------------------------------------------ S3 lesson
    def lesson_layout(self):
        if not self.v:
            return dict(card=(200, 90, 1520, 880), lab=(270, 132), bar=(270, 190, 1380, 24), title=(270, 250), spk=(318, 410),
                        src=(395, 410), lines=[(270, 590, 1380), (270, 690, 1380)], ans0=(275, 590), answ=1380,
                        bank_y=[820], ts=54, strip=(240, 800, 1440, 140))
        return dict(card=(50, 210, 980, 1500), lab=(110, 255), bar=(110, 315, 860, 26), title=(110, 380), spk=(158, 545),
                    src=(232, 545), lines=[(110, 860, 860), (110, 990, 860)], ans0=(115, 860), answ=860,
                    bank_y=[1240, 1370], ts=56, strip=(90, 1480, 900, 170))

    def tile_positions(self, Lyt):
        s = self.s
        sizes = []
        for w in C.LESSON_TILES:
            spr, ox, oy, tw, th = ui.tile(w, int(Lyt["ts"] * s))
            sizes.append((tw / s, th / s))
        gap = 22
        # answer slots (left aligned, wrap)
        ans = []
        x, line = Lyt["ans0"][0], 0
        for (tw, th) in sizes:
            if x + tw > Lyt["ans0"][0] + Lyt["answ"]:
                line += 1
                x = Lyt["ans0"][0]
            ans.append((x + tw / 2, Lyt["lines"][line][1] - th / 2 - 8))
            x += tw + gap
        # bank (shuffled, centered rows)
        order = C.LESSON_BANK_ORDER
        rows, cur, cw = [], [], 0
        maxw = Lyt["answ"]
        for i in order:
            tw = sizes[i][0]
            if cur and cw + tw + gap > maxw:
                rows.append(cur)
                cur, cw = [], 0
            cur.append(i)
            cw += tw + gap
        rows.append(cur)
        bank = [None] * len(sizes)
        cxm = Lyt["card"][0] + Lyt["card"][2] / 2
        for r, row in enumerate(rows):
            tot = sum(sizes[i][0] for i in row) + gap * (len(row) - 1)
            x = cxm - tot / 2
            y = Lyt["bank_y"][min(r, len(Lyt["bank_y"]) - 1)]
            for i in row:
                bank[i] = (x + sizes[i][0] / 2, y)
                x += sizes[i][0] + gap
        return sizes, ans, bank

    def draw_lesson(self, cv, cam, t, g):
        pl = self.lesson
        a = smooth(lin(t, 2.35, 2.75)) * (1 - smooth(lin(t, 4.76, 4.95)))
        if a <= 0:
            return
        Lyt = self.lesson_layout()
        tex = Tex(pl.tw, pl.th, self.s)
        x0, y0, w0, h0 = Lyt["card"]
        tex.card(x0, y0, w0, h0, r=50, lip=22, shadow=40, top="deep", bot=(44, 22, 84), border=0.35)
        tex.text(C.LESSON_LABEL, *Lyt["lab"], 34, 700, "lav")
        chime = C.HIT["chime1"]
        prog = 0.62 * smooth(lin(t, 2.95, 3.3)) + 0.38 * smooth(lin(t, chime, chime + 0.5))
        bx, by, bw, bh = Lyt["bar"]
        tex.bar(bx, by, bw, bh, prog)
        ty = Lyt["title"][1] + (1 - ease_out(lin(t, 2.85, 3.2))) * 30
        tex.text(C.LESSON_PROMPT, Lyt["title"][0], ty, 70 if not self.v else 72, 900, alpha=smooth(lin(t, 2.85, 3.15)))
        sa = smooth(lin(t, 3.0, 3.3))
        sx, sy = Lyt["spk"]
        tex.spr(ui.disc(int(96 * self.s), "violet", "purple", ring="lav"), sx, sy, "c", alpha=sa)
        wv = 1 + 0.12 * math.sin(t * 20) * clamp(1 - abs(t - 3.15) / 0.3)
        tex.spr(ui.icon("speaker", int(56 * self.s)), sx + 2, sy - 4, "c", alpha=sa, scale=wv)
        srcsz = 56 if not self.v else 42
        w_ = tex.text(C.LESSON_SRC, Lyt["src"][0], Lyt["src"][1], srcsz, 700, "white", anchor="cl", alpha=sa)
        for k in range(int((w_ - 40) / 16)):
            tex.rect(Lyt["src"][0] + 12 + k * 16, Lyt["src"][1] + srcsz * 0.62, 8, 3, "lav", 0.6 * sa)
        for (lx, ly, lw) in Lyt["lines"]:
            tex.rect(lx, ly, lw, 3, "lav", 0.28 * sa)
        sizes, ans, bank = self.tile_positions(Lyt)
        # bank slots (empty sockets)
        for i, (bxx, byy) in enumerate(bank):
            tw, th = sizes[i]
            tex.rect(bxx - tw / 2, byy - th / 2 + 6, tw, th, "lip", 0.65 * sa, r=th * 0.32)
        # tiles: lift -> fly -> snap
        subs = []
        tiles_in = smooth(lin(t, 3.05, 3.3))
        for i, word in enumerate(C.LESSON_TILES):
            t0 = C.TILE_TIMES[i]
            m = smooth(lin(t, t0 + 0.05, t0 + 0.30))
            lift = 0.0
            if t0 <= t < t0 + 0.42:
                lift = math.sin(math.pi * clamp((t - t0) / 0.40)) * 1.25
            px_ = tween(bank[i][0], ans[i][0], m)
            py_ = tween(bank[i][1], ans[i][1], m) - math.sin(math.pi * m) * 70
            snap = 1 + 0.10 * spring(t - (t0 + 0.30), 5, 9) * (t > t0 + 0.30)
            pop = 0.85 + 0.15 * back(lin(t, 3.05 + i * 0.03, 3.3 + i * 0.03))
            # contact shadow on the card
            tw, th = sizes[i]
            sh_a = 0.45 * tiles_in
            tex.rect(px_ - tw / 2 + lift * 14, py_ - th / 2 + 18 + lift * 26, tw, th, (10, 6, 22), sh_a * (0.5 + 0.3 * (1 - lift)), r=th * 0.32)
            subs.append((word, px_, py_, lift, snap * pop, tiles_in, i))
        # teacher-guided correction strip
        if t > chime - 0.05:
            sx_, sy_, sw, sh = Lyt["strip"]
            e = back(lin(t, chime, chime + 0.32), 1.4)
            yy = sy_ + (1 - e) * 120
            tex.card(sx_, yy, sw, sh, r=36, lip=12, shadow=20, top=(124, 52, 200), bot="purple", border=0.6, hi=0.4,
                     alpha=clamp(e * 1.5))
            tex.spr(ui.disc(int(86 * self.s), "gold", (225, 160, 20)), sx_ + 70, yy + sh / 2 - 4, "c")
            tex.spr(ui.icon("check", int(52 * self.s), "deep"), sx_ + 70, yy + sh / 2 - 8, "c")
            tex.text(C.UI["excellent"], sx_ + 130, yy + (10 if not self.v else 22), 56, 900)
            sub = C.UI["correction_h"] if not self.v else C.UI["correction_v"]
            tex.text(sub, sx_ + 132, yy + (80 if not self.v else 100), 32, 600, "mist")
            if not self.v:
                tex.spr(ui.avatar("L", int(70 * self.s), 1), sx_ + sw - 70, yy + sh / 2 - 4, "c")
        draw_quad(cv, cam, tex.a, pl.corners(), alpha=a)
        # the root beneath the interface
        self.R["to_lesson"].draw(cv, cam, grow=g["to_lesson"], t=t, alpha=a)
        self.R["lesson_under"].draw(cv, cam, grow=g["lesson_under"], t=t, alpha=a, width=0.9)
        # floating 3D tiles
        for (word, px_, py_, lift, sc, al, i) in sorted(subs, key=lambda x: x[3]):
            spr, ox, oy, tw, th = ui.tile(word, int(Lyt["ts"] * self.s))
            correct = t > C.HIT["chime1"]
            if correct:
                spr, ox, oy, tw, th = ui.tile(word, int(Lyt["ts"] * self.s), top="lav", bot="violet")
            self.draw_sub(cv, cam, pl, spr, px_, py_, lift, sc, a * al)

    def draw_sub(self, cv, cam, pl, spr, x, y, lift, scale=1.0, alpha=1.0):
        h, w = spr.shape[:2]
        ww = w / pl.tw * pl.w * scale
        hh = h / pl.th * pl.h * scale
        c = pl.px(x, y, 0.05 + lift)
        draw_quad(cv, cam, spr, quad_corners(c, pl.R, pl.U, ww, hh), alpha=alpha, dof=False)

    # ------------------------------------------------------------------ S4 progress
    def draw_prog(self, cv, cam, t, g):
        pl = self.prog
        a = smooth(lin(t, 4.62, 5.0)) * (1 - smooth(lin(t, 7.0, 7.3)))
        if a <= 0:
            return
        v = self.v
        tex = Tex(pl.tw, pl.th, self.s)
        cx, cy, cw, ch = (840, 140, 940, 800) if not v else (60, 1000, 960, 820)
        e = back(lin(t, 4.95, 5.35), 1.2)
        cyy = cy + (1 - e) * 80
        tex.card(cx, cyy, cw, ch, r=50, lip=22, shadow=40, top="deep", bot=(44, 22, 84), border=0.35, alpha=clamp(e * 1.4))
        hx = cx + 60
        hl = smooth(lin(t, 5.05, 5.4))
        hl2 = smooth(lin(t, 5.25, 5.6))
        tex.text(C.UI["every_lesson"], hx, cyy + 50 + (1 - hl) * 24, 76, 900, alpha=hl)
        tex.text(C.UI["helps_grow"], hx, cyy + 140 + (1 - hl2) * 24, 76, 900, "lav", alpha=hl2)
        # counter in fixed digit cells (illustrative)
        val = 365 * smooth(lin(t, 5.45, 6.75))
        cell_w, cell_h = 128, 168
        dx = hx
        dy = cyy + 280
        for d in range(3):
            place = 10 ** (2 - d)
            x = dx + d * (cell_w + 18)
            tex.card(x, dy, cell_w, cell_h, r=26, lip=14, shadow=14, top=(70, 30, 120), bot="lip", border=0.4,
                     alpha=hl)
            v_ = val / place
            if place == 1:
                frac = v_ - math.floor(v_)
            else:
                lower = val % place
                frac = clamp(lower - (place - 1))
            dig = int(math.floor(v_)) % 10
            nxt = (dig + 1) % 10
            off = frac * cell_h
            self._digit(tex, str(dig), x + cell_w / 2, dy + cell_h / 2 - off, dy, cell_h, hl)
            self._digit(tex, str(nxt), x + cell_w / 2, dy + cell_h / 2 + cell_h - off, dy, cell_h, hl)
        lx = dx + 3 * (cell_w + 18) + 20
        tex.text(C.UI["days_of"], lx, dy + 22, 46, 800, alpha=hl)
        tex.text(C.UI["progress"], lx, dy + 76, 46, 800, alpha=hl)
        tw_ = text_w(C.UI["illustrative"], int(30 * self.s), 700) / self.s
        tex.rect(lx, dy + 136, tw_ + 32, 44, "lip", 0.9 * hl, r=22)
        tex.text(C.UI["illustrative"], lx + 16, dy + 158, 30, 700, "lav", anchor="cl", alpha=hl)
        # course bar
        by = dy + 230
        tex.text(C.UI["course_progress"], hx, by, 32, 700, "mist", alpha=hl)
        pf = smooth(lin(t, 5.6, 6.9)) * 0.86
        tex.text(f"{int(round(pf * 100))}%", cx + cw - 60, by, 32, 900, "lav", anchor="tr", alpha=hl)
        tex.bar(hx, by + 52, cw - 120, 26, pf, alpha=hl)
        # lesson nodes lighting in sequence
        ny = by + 150
        n = 7
        for k in range(n):
            x = hx + 40 + (cw - 200) * k / (n - 1)
            tl = 5.75 + k * 0.17
            lit = smooth(lin(t, tl, tl + 0.12))
            if k < n - 1:
                tex.rect(x, ny - 4, (cw - 200) / (n - 1), 8, "violet" if lit > 0.5 else "lip", 0.9 * hl)
        for k in range(n):
            x = hx + 40 + (cw - 200) * k / (n - 1)
            tl = 5.75 + k * 0.17
            lit = smooth(lin(t, tl, tl + 0.12))
            pop = 1 + 0.25 * spring(t - tl, 4, 8) * (t > tl)
            tex.spr(ui.disc(int(70 * self.s), "plum", "lip"), x, ny, "c", alpha=hl)
            if lit > 0:
                tex.spr(ui.disc(int(70 * self.s), "lav", "violet"), x, ny, "c", alpha=hl * lit, scale=pop)
                tex.spr(ui.icon("check", int(38 * self.s)), x, ny - 4, "c", alpha=hl * lit, scale=pop)
        draw_quad(cv, cam, tex.a, pl.corners(), alpha=a)
        self.R["to_lesson"].draw(cv, cam, grow=1.0, t=t, alpha=a * (1 - smooth(lin(t, 4.9, 5.2))))
        self.R["to_prog"].draw(cv, cam, grow=g["to_prog"], t=t, alpha=a)
        self.R["prog_under"].draw(cv, cam, grow=g["prog_under"], t=t, alpha=a, width=0.85)
        # the young tree: the root grows into its trunk and lights it
        gr = smooth(lin(t, 5.20, 6.85))
        if gr > 0:
            st = dict(time=t, grow=0.02 + 0.98 * gr, roots=smooth(lin(t, 5.25, 6.3)), lit=gr,
                      impact=None, happy=0.6 * smooth(lin(t, 6.6, 6.9)), alpha=a)
            self.tree.draw(cv, cam, self.prog_tree_origin(), 0.50 if not v else 0.60, st, roots_key="prog")

    def _digit(self, tex, d, x, y, top, h, alpha):
        s = self.s
        spr, _ = text_sprite(d, int(116 * s), 900, (255, 255, 255))
        # clip into the cell
        hh, ww = spr.shape[:2]
        y0 = y * s - hh / 2
        c0 = int(max(0, top * s + 6 * s - y0))
        c1 = int(min(hh, (top + h) * s - 6 * s - y0))
        if c1 <= c0:
            return
        blit(tex.a, spr[c0:c1], x * s - ww / 2, y0 + c0, alpha)

    # ------------------------------------------------------------------ S5 community
    def draw_comm(self, cv, cam, t, g):
        pl = self.comm
        a = smooth(lin(t, 6.85, 7.1)) * (1 - smooth(lin(t, 9.15, 9.45)))
        if a <= 0:
            return
        v = self.v
        drop = C.HIT["drop"]
        tex = Tex(pl.tw, pl.th, self.s)
        if not v:
            cx, cy, cw, ch = 860, 70, 900, 940
            hx, hy = 150, 330
        else:
            cx, cy, cw, ch = 60, 520, 960, 1260
            hx, hy = 540, 200
        e = back(lin(t, drop, drop + 0.38), 1.6)
        cyy = cy - (1 - e) * 500
        ca = clamp(lin(t, drop - 0.02, drop + 0.12))
        tex.card(cx, cyy, cw, ch, r=50, lip=22, shadow=40, top="deep", bot=(44, 22, 84), border=0.35, alpha=ca)
        # headline
        h1 = smooth(lin(t, drop + 0.20, drop + 0.5))
        h2 = smooth(lin(t, drop + 0.38, drop + 0.68))
        if not v:
            tex.text(C.UI["grow"], hx, hy - 60 + (1 - h1) * 40, 116, 900, alpha=h1)
            tex.text(C.UI["together"], hx, hy + 70 + (1 - h2) * 40, 116, 900, "lav", alpha=h2)
            tex.text(C.UI["real_line"], hx + 4, hy + 240, 40, 700, "mist", alpha=smooth(lin(t, drop + 0.7, drop + 1.0)))
        else:
            tex.text(C.UI["grow_together"], hx, hy + (1 - h1) * 40, 94, 900, anchor="tc", alpha=h1)
            tex.text(C.UI["real_line"], hx, hy + 140, 40, 700, "mist", anchor="tc", alpha=smooth(lin(t, drop + 0.7, drop + 1.0)))
        tex.text(C.UI["group"], cx + 50, cyy + 44, 36, 800, alpha=ca)
        tex.text(C.UI["week"], cx + 50, cyy + 96, 30, 600, "lav", alpha=ca)
        rows = C.COMMUNITY
        rh = 102 if not v else 140
        r0 = cyy + 160
        rank1 = C.HIT["rank1"]
        mv = smooth(lin(t, 7.95, rank1 - 0.05))
        lift = math.sin(math.pi * clamp((t - 7.80) / (rank1 + 0.12 - 7.80))) * 1.0 if 7.80 < t < rank1 + 0.12 else 0.0
        amira_pos = tween(6, 0, mv)
        subs = []
        for i, (name, pts) in enumerate(rows):
            ra = smooth(lin(t, drop + 0.25 + i * 0.05, drop + 0.45 + i * 0.05)) * ca
            if i == 6:
                slot = amira_pos
            else:
                # rows shift down as Amira passes them
                slot = i + clamp((6 - amira_pos) - (6 - 1 - i) + 0.0) if amira_pos < i + 1 else i
                slot = i + smooth(clamp((i + 1) - amira_pos))
            y = r0 + slot * rh
            if i == 6:
                subs.append((y, ra))
                continue
            self._row(tex, cx + 30, y, cw - 60, rh - 14, int(round(slot)) + 1, name, pts, i, ra, False, t)
        draw_quad(cv, cam, tex.a, pl.corners(), alpha=a)
        self.R["to_comm"].draw(cv, cam, grow=g["to_comm"], t=t, alpha=a)
        # Amira's row lifts out in 3D and rises to #1
        y, ra = subs[0]
        rank = 7 if t < rank1 else 1
        pts = int(tween(1120, C.AMIRA_FINAL_POINTS, smooth(lin(t, 7.95, rank1))))
        rw, rhh = cw - 60, rh - 14
        rt = Tex(int((rw + 80) * self.s), int((rhh + 60) * self.s), self.s)
        self._row(rt, 40, 20, rw, rhh, rank, "Amira S.", pts, 6, 1.0, True, t)
        burst = clamp(1 - (t - rank1) / 0.6) if t > rank1 else 0
        self.draw_sub(cv, cam, pl, rt.a, cx + 30 + rw / 2, y + rhh / 2 + 10, 0.02 + lift, 1 + 0.06 * lift + 0.05 * burst, a * ra)
        if t > rank1:
            c = pl.px(cx + 110, y + rhh / 2, 0.6)
            sp, z = cam.project(c[None])
            for k in range(14):
                ang = k / 14 * 6.28 + 0.3
                d = (t - rank1) * 900 * self.s * (0.6 + 0.4 * hash01("b", k))
                glow_dot(cv, sp[0, 0] + math.cos(ang) * d, sp[0, 1] + math.sin(ang) * d * 0.6, 4 * self.s,
                         col("gold") if k % 3 == 0 else col("lav"), 0.9 * burst)

    def _row(self, tex, x, y, w, h, rank, name, pts, i, alpha, hero, t):
        if hero:
            tex.card(x, y, w, h, r=28, lip=12, shadow=24, top=(130, 60, 210), bot="purple", border=0.8, hi=0.4,
                     alpha=alpha)
        else:
            tex.rect(x, y, w, h, (46, 28, 86), 0.85 * alpha, r=26)
        tex.text(str(rank), x + 52, y + h / 2, 42, 900, "gold" if (hero and rank == 1) else "lav", anchor="c", alpha=alpha)
        tex.spr(ui.avatar(name[0], int(h * 0.68 * self.s), i), x + 110, y + h / 2, "cl", alpha=alpha)
        tex.text(name, x + 110 + h * 0.68 + 22, y + h / 2, 40 if not self.v else 44, 800, anchor="cl", alpha=alpha)
        bw = 200 if not self.v else 170
        bx = x + w - bw - (210 if not self.v else 230)
        tex.bar(bx, y + h / 2 - 9, bw, 18, pts / 1600, alpha=alpha, headglow=False)
        tex.text(f"{pts:,}".replace(",", " " if C.LANG == "fr" else ","), x + w - 90, y + h / 2, 38 if not self.v else 42, 900, anchor="cr", alpha=alpha)
        tex.text(C.UI["pts"], x + w - 30, y + h / 2 + 4, 26, 700, "lav", anchor="cr", alpha=alpha)
        if hero and rank == 1:
            tex.spr(ui.icon("star", int(54 * self.s), "gold"), x + 52, y - 4, "c", alpha=alpha)

    # ------------------------------------------------------------------ S6 call
    def call_layout(self):
        if not self.v:
            return dict(win=(130, 80, 1660, 920), bar_h=78, tT=(170, 182, 790, 560), tS=(990, 182, 760, 560),
                        bubT=(170, 768, 790, 104), bubS=(990, 768, 760, 104), ctl_y=930, title_sz=32)
        return dict(win=(40, 130, 1000, 1660), bar_h=96, tT=(80, 250, 920, 560), tS=(80, 830, 920, 560),
                    bubT=(80, 1410, 920, 110), bubS=(80, 1540, 920, 110), ctl_y=1700, title_sz=30)

    def draw_call(self, cv, cam, t, g):
        pl = self.call
        a = smooth(lin(t, 9.05, 9.35)) * (1 - smooth(lin(t, 11.30, 11.44)))
        if a <= 0:
            return
        Ly = self.call_layout()
        tex = Tex(pl.tw, pl.th, self.s)
        x, y, w, h = Ly["win"]
        e = back(lin(t, 9.12, 9.45), 1.3)
        tex.card(x, y + (1 - e) * 60, w, h, r=44, lip=20, shadow=40, top=(30, 24, 62), bot=(22, 18, 46), border=0.35,
                 alpha=clamp(e * 1.4))
        y = y + (1 - e) * 60
        for k, c in enumerate(("lav", "violet", "purple")):
            tex.spr(ui.disc(int(22 * self.s), c, c, lip=0.0), x + 46 + k * 34, y + Ly["bar_h"] / 2, "c")
        tex.text(C.UI["call_title"], x + 160, y + Ly["bar_h"] / 2, Ly["title_sz"], 800, anchor="cl")
        # recording pill (recorded lessons available)
        rl = C.UI["recorded"]
        rw = text_w(rl, int(26 * self.s), 700) / self.s + 90
        rx = x + w - rw - 30
        tex.rect(rx, y + Ly["bar_h"] / 2 - 22, rw, 44, (60, 24, 70), 0.95, r=22)
        blink = 0.6 + 0.4 * math.sin(t * 8)
        tex.spr(ui.icon("rec", int(26 * self.s), (255, 80, 110)), rx + 30, y + Ly["bar_h"] / 2, "c", alpha=blink)
        tex.text(rl, rx + 54, y + Ly["bar_h"] / 2, 26, 700, "mist", anchor="cl")
        # tiles
        tl = [C.TEACHER_LINE, C.STUDENT_LINE]
        t_talk = (9.42, 10.05)
        s_talk = (10.12, 10.95)
        react = 10.98
        for who, box, talk in (("teacher", Ly["tT"], t_talk), ("student", Ly["tS"], s_talk)):
            bx, by_, bw, bh = box
            by_ += (1 - e) * 60
            talking = talk[0] < t < talk[1]
            mouth = (int(t * 14 + (3 if who == "student" else 0)) % 4) if talking else 0
            if talking and mouth == 0:
                mouth = 1
            blinkon = int((t * 60 + (17 if who == "teacher" else 0)) % 170) < 7
            smile = 1 if (who == "teacher" and t > react) or (who == "student" and t > 10.9) else 0
            por = ui.portrait(who, int(bw * self.s), int(bh * self.s), mouth, int(blinkon), smile)
            por = ui.clip_round(por, int(30 * self.s))
            tex.spr(por, bx, by_, alpha=clamp(e * 1.4))
            if talking:
                # active speaker ring
                tex.rect(bx - 5, by_ - 5, bw + 10, 6, "lav", 0.9, r=3)
                tex.rect(bx - 5, by_ + bh - 1, bw + 10, 6, "lav", 0.9, r=3)
                tex.rect(bx - 5, by_ - 5, 6, bh + 10, "lav", 0.9, r=3)
                tex.rect(bx + bw - 1, by_ - 5, 6, bh + 10, "lav", 0.9, r=3)
            name = C.UI["teacher_tag"] if who == "teacher" else "Amira"
            nw = text_w(name, int(28 * self.s), 800) / self.s + 70
            tex.rect(bx + 18, by_ + bh - 64, nw, 46, (20, 14, 40), 0.75, r=23)
            tex.spr(ui.icon("mic", int(26 * self.s), "lav"), bx + 42, by_ + bh - 41, "c")
            tex.text(name, bx + 62, by_ + bh - 41, 28, 800, anchor="cl")
        # captions (what is said)
        for who, box, line, t0 in (("teacher", Ly["bubT"], tl[0], 9.42), ("student", Ly["bubS"], tl[1], 10.12)):
            bx, by_, bw, bh = box
            ap = smooth(lin(t, t0, t0 + 0.22))
            if ap <= 0:
                continue
            yy = by_ + (1 - back(lin(t, t0, t0 + 0.3))) * 30
            top = (88, 40, 150) if who == "teacher" else (120, 56, 196)
            tex.card(bx, yy, bw, bh, r=30, lip=10, shadow=16, top=top, bot="purple", border=0.5, alpha=ap)
            tex.spr(ui.icon("chat", int(44 * self.s), "lav"), bx + 46, yy + bh / 2, "c", alpha=ap)
            # type-on
            n = int(len(line) * clamp((t - t0) / 0.45))
            sz = 34 if not self.v else 38
            tex.text(line[:max(1, n)], bx + 86, yy + bh / 2, sz, 800, anchor="cl", alpha=ap)
        # teacher reaction
        if t > react:
            r = back(lin(t, react, react + 0.3), 2.0)
            bx, by_, bw, bh = Ly["tT"]
            by_ += (1 - e) * 60
            tex.card(bx + bw - 300, by_ + 26, 270, 76, r=38, lip=8, shadow=10, top="gold", bot=(232, 168, 20), border=0.0,
                     alpha=clamp(r))
            tex.text(C.UI["reaction"], bx + bw - 165, by_ + 62, 36, 900, (60, 30, 90), anchor="c", alpha=clamp(r))
            for k in range(3):
                hp = lin(t, react + k * 0.12, react + 0.9 + k * 0.12)
                if 0 < hp < 1:
                    tex.spr(ui.icon("heart", int(40 * self.s), "lav"), bx + bw - 80 - k * 40, by_ + 140 + 200 * (1 - hp),
                            "c", alpha=math.sin(math.pi * hp))
        # control bar
        icons = ["mic", "video", "chat", "hand"]
        cyb = Ly["ctl_y"] + (1 - e) * 60
        for k, ic in enumerate(icons):
            xx = x + w / 2 + (k - 1.5) * 96
            tex.spr(ui.disc(int(70 * self.s), (70, 50, 120), (46, 30, 86), lip=0.08), xx, cyb, "c")
            tex.spr(ui.icon(ic, int(36 * self.s), "white"), xx, cyb - 3, "c")
        draw_quad(cv, cam, tex.a, pl.corners(), alpha=a)
        self.R["to_call"].draw(cv, cam, grow=g["to_call"], t=t, alpha=a)
        # the root becomes the student's voice waveform
        if g["wave"] > 0:
            n = self.wave_N
            xs = np.linspace(0, 1, n)
            env = np.sin(np.pi * xs) ** 0.8
            act = smooth(lin(t, 10.12, 10.25)) * (1 - smooth(lin(t, 10.95, 11.2)))
            amp = (0.15 + 0.85 * act) * (0.55 + 0.45 * np.abs(np.sin(xs * 23 + t * 17)) * np.abs(np.sin(xs * 7.3 - t * 9)))
            disp = np.sin(xs * 60 - t * 26) * amp * env * 0.9 + np.sin(xs * 23 + t * 11) * amp * env * 0.3
            off = np.outer(disp, pl.U)
            self.R["wave"].draw(cv, cam, grow=g["wave"], t=t, alpha=a, offsets=off, glow=1.6, rootlets=False)

    # ------------------------------------------------------------------ S7 languages
    def draw_lang(self, cv, cam, t, g):
        pl = self.lang
        a = smooth(lin(t, 11.35, 11.55)) * (1 - smooth(lin(t, 13.55, 13.85)))
        if a <= 0:
            return
        v = self.v
        tex = Tex(pl.tw, pl.th, self.s)
        names = C.UI["langs"]
        codes = ["uk", "fr", "de"]
        keys = ["en", "fr", "de"]
        native = ["English", "Français", "Deutsch"]
        hdr = smooth(lin(t, 11.5, 11.8))
        if not v:
            tex.text(C.UI["langs_hdr"], 960, 60, 48, 800, "mist", anchor="tc", alpha=hdr)
        else:
            tex.text(C.UI["langs_hdr_v"][0], 540, 120, 60, 900, anchor="tc", alpha=hdr)
            tex.text(C.UI["langs_hdr_v"][1], 540, 200, 60, 900, "lav", anchor="tc", alpha=hdr)
        for k in range(3):
            tk = WT[keys[k]]
            la_ = smooth(lin(t, tk - 0.05, tk + 0.2))
            fp = self.flag_pos[k]
            # label under the flag
            p = fp + pl.U * (self.flag_r() * 1.45)
            u = (np.dot(p - pl.C, pl.R) / (pl.w / 2) + 1) / 2 * self.DW
            vv = (1 - np.dot(p - pl.C, pl.U) / (pl.h / 2)) / 2 * self.DH
            tex.text(names[k], u, vv - 70 + (1 - la_) * 20, 64, 900, anchor="bc", alpha=la_)
        # central learning structure
        hb = smooth(lin(t, 13.05, 13.3))
        draw_quad(cv, cam, tex.a, pl.corners(), alpha=a)
        self.R["to_lang"].draw(cv, cam, grow=g["to_lang"], t=t, alpha=a)
        for k in range(3):
            self.R["br"][k].draw(cv, cam, grow=g["br"][k], t=t, alpha=a, lit=1.0)
        if g["to_lang"] > 0.9:
            draw_puck(cv, cam, self.hub - pl.N * 0.2, -pl.N, 1.2 * (0.8 + 0.2 * back(lin(t, 11.55, 11.8))), 0.5,
                      lit=0.3 + 0.7 * hb, alpha=a, icon=book_icon(int(200 * self.s)),
                      face=mixc(col("purple"), col("gold"), 0.18 * hb))
        # flags + orbiting vocabulary tiles
        for k in range(3):
            tk = WT[keys[k]]
            pop = back(lin(t, tk - 0.06, tk + 0.22), 2.2)
            if pop <= 0:
                continue
            fp = self.flag_pos[k]
            r = self.flag_r()
            tiles = []
            words = C.VOCAB[keys[k]]
            for j, w in enumerate(words):
                ang = t * 1.9 + j * (2 * math.pi / len(words)) + k
                orb = (pl.R * math.cos(ang) * r * 1.75 - pl.N * math.sin(ang) * r * 1.2 + pl.U * math.sin(ang * 1.0 + 0.5) * r * 0.45)
                tp = fp + orb * (0.6 + 0.4 * clamp(pop))
                tiles.append((float(cam.project(tp[None])[1][0]), tp, w))
            zf = float(cam.project(fp[None])[1][0])
            spr_sz = int(38 * self.s)
            for zt, tp, w in sorted(tiles, key=lambda x: -x[0]):
                if zt > zf:
                    self._vocab(cv, cam, pl, tp, w, spr_sz, a * clamp(pop))
            lit = clamp((t - tk) / 0.25)
            glow_dot(cv, *cam.project(fp[None])[0][0], r * cam.fpx / zf * 1.4, col("lav"), 0.25 * lit * a)
            draw_sphere(cv, cam, fp, r, codes[k], a, scale=max(0.01, pop), glow=0.6)
            for zt, tp, w in sorted(tiles, key=lambda x: -x[0]):
                if zt <= zf:
                    self._vocab(cv, cam, pl, tp, w, spr_sz, a * clamp(pop))

    def _vocab(self, cv, cam, pl, p, w, size, alpha):
        spr, ox, oy, tw, th = ui.tile(w, size, top="plum", bot="lip", border=0.6)
        h, ww = spr.shape[:2]
        sc = pl.w / pl.tw
        draw_quad(cv, cam, spr, quad_corners(p, pl.R, pl.U, ww * sc, h * sc), alpha=alpha, dof=True)

    # ------------------------------------------------------------------ S7b skills + S8 message
    def draw_skills(self, cv, cam, t, g):
        pl = self.sk
        a = smooth(lin(t, 13.15, 13.45)) * (1 - smooth(lin(t, 16.40, 16.66)))
        if a <= 0:
            return
        v = self.v
        tex = Tex(pl.tw, pl.th, self.s)
        names = C.UI["skills"]
        icons = ["speakwave", "headphones", "book", "pen"]
        keys = ["speaking", "listening", "reading", "writing"]
        merge = smooth(lin(t, 14.78, 15.15))
        for k in range(4):
            tk = WT[keys[k]]
            la_ = smooth(lin(t, tk - 0.04, tk + 0.16)) * (1 - merge)
            p = self.skill_pos[k] - pl.U * (self.skill_r() * 1.45)
            u = (np.dot(p - pl.C, pl.R) / (pl.w / 2) + 1) / 2 * self.DW
            vv = (1 - np.dot(p - pl.C, pl.U) / (pl.h / 2)) / 2 * self.DH
            tex.text(names[k], u, vv + (1 - la_) * 24, 60, 900, anchor="tc", alpha=la_)
        # tagline (S8)
        ux0, ux1, uy = self.tag_underline()
        t1, t2 = WT["strong_roots_2"], WT["endless"]
        s1 = smooth(lin(t, t1 - 0.08, t1 + 0.22))
        s2 = smooth(lin(t, min(t2, 15.55) - 0.08, min(t2, 15.55) + 0.25))
        if not v:
            tex.text(C.TAG1, 960, uy - 380 + (1 - s1) * 40, 112, 900, anchor="tc", alpha=s1)
            tex.text(C.TAG2, 960, uy - 240 + (1 - s2) * 40, 112, 900, "lav", anchor="tc", alpha=s2)
        else:
            tv = C.UI["tag_v"]
            tex.text(tv[0], 540, uy - 700 + (1 - s1) * 40, 108, 900, anchor="tc", alpha=s1)
            tex.text(tv[1], 540, uy - 560 + (1 - s1) * 40, 108, 900, anchor="tc", alpha=s1)
            tex.text(tv[2], 540, uy - 420 + (1 - s2) * 40, 108, 900, "lav", anchor="tc", alpha=s2)
            s3 = smooth(lin(t, min(t2, 15.55) + 0.12, min(t2, 15.55) + 0.42))
            tex.text(tv[3], 540, uy - 280 + (1 - s3) * 40, 108, 900, "lav", anchor="tc", alpha=s3)
        draw_quad(cv, cam, tex.a, pl.corners(), alpha=a)
        self.R["to_skills"].draw(cv, cam, grow=g["to_skills"], t=t, alpha=a * (1 - merge))
        for k in range(4):
            self.R["sk"][k].draw(cv, cam, grow=g["sk"][k], t=t, g0=merge * 0.98, alpha=a)
        for k in range(4):
            self.R["conv"][k].draw(cv, cam, grow=g["conv"][k], t=t, g0=smooth(lin(t, 15.15, 15.5)), alpha=a)
        self.R["under"].draw(cv, cam, grow=g["under"], t=t, alpha=a, width=1.15)
        if g["to_hero"] > 0 and t <= 16.6:
            self.R["to_hero"].draw(cv, cam, grow=g["to_hero"], t=t, alpha=1.0)
        # skill nodes (upright chunky pucks) - merge into the same purple light
        for k in range(4):
            tk = WT[keys[k]]
            pop = back(lin(t, tk - 0.18, tk + 0.05), 1.8)
            if pop <= 0 or merge >= 1:
                continue
            lit = clamp((t - tk) / 0.15)
            p = self.skill_pos[k] * (1 - merge) + self.conv * merge
            sc = max(0.01, pop) * (1 - 0.85 * merge)
            draw_puck(cv, cam, p, -pl.N, self.skill_r() * sc, 0.55 * sc, lit=lit, alpha=a,
                      icon=ui.icon(icons[k], int(150 * self.s), "white"), glow=1.0 + merge)
            if merge > 0:
                sp, z = cam.project(p[None])
                glow_dot(cv, sp[0, 0], sp[0, 1], 90 * self.s * (1 - merge * 0.5), col("lav"), 0.6 * merge * (1 - merge) * 4 * a)

    # ------------------------------------------------------------------ S9 hero + S10 end card
    def draw_hero(self, cv, cam, t, g):
        land = C.HIT["land"]
        if 16.6 < t < 17.4:
            self.R["to_hero"].draw(cv, cam, grow=g["to_hero"], t=t, alpha=1 - smooth(lin(t, 16.95, 17.35)))
        if t >= land - 0.17:
            st = self.tree_state(t, land, grow=1.0)
            if t >= land:
                st["grow"] = 0.55 + 0.45 * smooth(lin(t, land + 0.02, land + 0.55))
            else:
                st["grow"] = 0.55
            st["happy"] = 0.8 * smooth(lin(t, 18.0, 18.4)) * (1 - 0.6 * smooth(lin(t, 19.6, 20.4)))
            gl = C.HIT["fanfare"]
            if gl - 0.05 < t < gl + 0.6:
                st["glint"] = lin(t, gl, gl + 0.5)
            st["gesture"] = (t - 18.07) if t > 18.07 else None
            self.tree.draw(cv, cam, self.Oh, self.hero_scale, st, roots_key="hero")
        if g["word2"] > 0:
            self.draw_wordmark(cv, cam, self.word2, g["word2"], t, 1.0)
            self.R["word2"].draw(cv, cam, grow=g["word2"], t=t)
        if t > 19.0:
            e = smooth(lin(t, 19.25, 19.75))
            e2 = smooth(lin(t, 19.6, 20.1))
            pl = self.endtag
            tex = Tex(pl.tw, pl.th, self.s)
            if not self.v:
                tex.text(C.UI["end_v"][0], 650, 0 + (1 - e) * 20, 60, 900, anchor="tc", alpha=e)
                tex.text(C.UI["end_v"][1], 650, 76 + (1 - e) * 20, 60, 900, anchor="tc", alpha=e)
                tex.text(C.END_SUB, 650, 176 + (1 - e2) * 20, 40, 700, "lav", anchor="tc", alpha=e2, tracking=0.05)
            else:
                tex.text(C.UI["end_v"][0], 540, 10 + (1 - e) * 20, 70, 900, anchor="tc", alpha=e)
                tex.text(C.UI["end_v"][1], 540, 106 + (1 - e) * 20, 70, 900, anchor="tc", alpha=e)
                tex.text(C.END_SUB, 540, 236 + (1 - e2) * 20, 42, 700, "lav", anchor="tc", alpha=e2, tracking=0.05)
            draw_quad(cv, cam, tex.a, pl.corners(), alpha=1.0, dof=False)


_BI = {}


def book_icon(size):
    if size in _BI:
        return _BI[size]
    from .tree import book_sprite
    b = book_sprite()
    h, w = b.shape[:2]
    sc = size / w
    bb = cv2.resize(b, (size, max(1, int(h * sc))), interpolation=cv2.INTER_AREA)
    out = np.zeros((size, size, 4), np.float32)
    y0 = (size - bb.shape[0]) // 2
    out[y0:y0 + bb.shape[0]] = bb
    _BI[size] = out
    return out


_WM = {}


def wordmark_tex(tw, th, s):
    key = (tw, th)
    if key in _WM:
        return _WM[key]
    a = np.zeros((th, tw, 4), np.float32)
    sz = int(170 * s)
    s1, b1 = text_sprite("Lougha", sz, 900, (255, 255, 255), 0.0, 0.0)
    s2, b2 = text_sprite("Online", sz, 400, (255, 255, 255), 0.0, 0.0)
    gap = int(34 * s)
    w = s1.shape[1] + s2.shape[1] + gap - int(sz * 0.5)
    x = (tw - w) / 2
    y = int(30 * s)
    blit(a, s1, x, y)
    blit(a, s2, x + s1.shape[1] + gap - int(sz * 0.5), y)
    s3, b3 = text_sprite("language roots", int(78 * s), 400, (240, 232, 255), 0.04)
    blit(a, s3, tw / 2, y + int(205 * s), anchor="tc")
    _WM[key] = a
    return a
