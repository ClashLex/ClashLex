#!/usr/bin/env python3
"""
make_raid.py - builds raid-light.svg and raid-dark.svg

The README header is a pure-SMIL animated SVG: no JavaScript, no CSS, no external
files, so GitHub renders it inside <img>. It starts out looking like a normal profile
page. Then a pirate swings in and nails a bounty poster to it, a navy officer shows
up, letters get sliced, a cannon goes off twice, and a tide washes the page back to normal.

How it is built
  Track   keyframes (time, value, easing) -> one <animate> with keyTimes / keySplines
  Piece   anything that can move, rotate, fade, pop in and be cut in half (letters, poster)
  Char    a stick figure. Poses are joint dicts; limbs are <polyline points> that SMIL
          morphs from pose to pose
  Scene   the story. Read Scene.story() top to bottom like a screenplay.

Every element animates against the same T-second timeline, so everything stays in
sync with no scripting. The banner is drawn from plain shapes (one group per letter), so it
looks the same on every OS.

Usage
  python make_raid.py              writes raid-light.svg and raid-dark.svg next to this file
  python make_raid.py --preview    also saves PNG frames + a contact sheet to ./preview
                                   (needs: pip install playwright pillow; playwright install chromium)
"""
import argparse
import html
import math
import os
import sys
from functools import lru_cache

try:
    from PIL import ImageFont
except ImportError:  # widths fall back to a rough estimate
    ImageFont = None

# ------------------------------------------------------------------ copy
# The banner. Paste any block-letter ASCII art (box-drawing style: █ ╗ ╔ ╝ ╚ ═ ║) and list where
# each letter starts/ends (in columns) so the officer can cut them one by one.
ART_RAW = [
    "█████╗ ███╗   ██╗███████╗██╗██╗     ",
    "██╔══██╗████╗  ██║██╔════╝██║██║     ",
    "███████║██╔██╗ ██║███████╗██║██║     ",
    "██╔══██║██║╚██╗██║╚════██║██║██║     ",
    "██║  ██║██║ ╚████║███████║██║███████╗",
    "╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝╚═╝╚══════╝",
]
LETTER_COLS = [(0, 8), (8, 18), (18, 26), (26, 29), (29, 37)]   # A N S I L
ALT = ("ANSIL, drawn in ASCII block letters. A pirate swings in, pins a bounty poster to the page "
       "and a navy officer attacks, slicing the letters. A tide washes the banner clean.")
POSTER_HEAD = "WANTED"
POSTER_NAME = "CLASHLEX"
POSTER_SUB = "for shipping side projects"
POSTER_REWARD = "REWARD: one GitHub star"

# ------------------------------------------------------------------ constants
T = 31.0                      # loop length, seconds
W, H, FLOOR = 830, 310, 300   # canvas and ground line
S = 1.5                       # stick figures are drawn at this scale
PIV = -17.0 * S               # rotation pivot (body centre) above the feet
EPS = 0.002
CW, CH = 12, 22               # size of one ASCII cell in pixels (1:2 like a terminal)
X0, Y0 = 16, 70               # top-left of the banner (letter tops double as a platform)
FONT_STACK = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"

PALETTES = {
    "light": dict(bg="#ffffff", fg="#1f2328", rule="#d1d9e0", pirate="#c2410c", navy="#1d4ed8",
                  steel="#b4bdc6", spark="#d4a017", smoke="#8c959f", flash="#ffffff",
                  paper="#f1e3b8", paper_edge="#8a6d2f", ink="#3b2a14", cannon="#4b5563",
                  water_a="#0b5d7a", water_b="#1aa3c8", foam="#ffffff"),
    "dark":  dict(bg="#0d1117", fg="#e6edf3", rule="#3d444d", pirate="#fb923c", navy="#60a5fa",
                  steel="#dfe5ec", spark="#e3b341", smoke="#8b949e", flash="#f0f0ff",
                  paper="#e9d9a6", paper_edge="#a8884a", ink="#3b2a14", cannon="#8b949e",
                  water_a="#0a3d55", water_b="#1581a3", foam="#e0f2fe"),
}
SPLINES = {"lin": "0 0 1 1", "in": "0.55 0 1 1", "out": "0 0 0.45 1", "inout": "0.45 0 0.55 1", "snap": "0 0 0.15 1"}

# ------------------------------------------------------------------ small helpers
FONT_DIRS = ["/usr/share/fonts/truetype/liberation", "/usr/share/fonts/liberation", "/usr/share/fonts/truetype/dejavu",
             "/Library/Fonts", "/System/Library/Fonts/Supplemental", "C:/Windows/Fonts"]


@lru_cache(maxsize=None)
def _font(bold, size):
    if ImageFont is None:
        return None
    names = ["LiberationSans-Bold.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold else \
            ["LiberationSans-Regular.ttf", "arial.ttf", "DejaVuSans.ttf"]
    for d in FONT_DIRS:
        for nm in names:
            path = os.path.join(d, nm)
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
    return None


def text_w(s, size=16, bold=False):
    f = _font(bold, int(size))
    return f.getlength(s) if f else len(s) * size * (0.58 if bold else 0.53)


def n(v):
    s = f"{v:.1f}"
    s = s[:-2] if s.endswith(".0") else s
    return "0" if s == "-0" else s


def f2(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


fxy = lambda v: f"{n(v[0])} {n(v[1])}"
frot = lambda v: f"{n(v[0])} {n(v[1])} {n(v[2])}"
fsc = lambda v: f"{f2(v[0])} {f2(v[1])}"
fsc1 = lambda v: f"{f2(v)} {f2(v)}"
fface = lambda v: f"{f2(v)} 1"


def rnd(i):
    x = math.sin(i * 12.9898 + 78.233) * 43758.5453
    return x - math.floor(x)


# ------------------------------------------------------------------ tracks
def eased(s, ease):
    """The browser's keySpline curve, so Python can ask where something is mid-tween."""
    if ease == "lin" or s <= 0 or s >= 1:
        return s
    x1, y1, x2, y2 = (float(v) for v in SPLINES[ease].split())
    lo, hi = 0.0, 1.0
    for _ in range(24):
        mid = (lo + hi) / 2
        x = 3 * (1 - mid) ** 2 * mid * x1 + 3 * (1 - mid) * mid ** 2 * x2 + mid ** 3
        lo, hi = (mid, hi) if x < s else (lo, mid)
    u = (lo + hi) / 2
    return 3 * (1 - u) ** 2 * u * y1 + 3 * (1 - u) * u ** 2 * y2 + u ** 3


def mix(a, b, s):
    if isinstance(a, (int, float)):
        return a + (b - a) * s
    return tuple(x + (y - x) * s for x, y in zip(a, b))


class Track:
    """A value over time. to() tweens, hold() keeps, snap() jumps."""

    def __init__(self, v0):
        self.k = [[0.0, v0, "lin"]]

    @property
    def t(self):
        return self.k[-1][0]

    @property
    def v(self):
        return self.k[-1][1]

    def to(self, t, v, ease="lin"):
        if t <= self.t:
            t = self.t + EPS
        self.k.append([round(t, 5), v, ease])

    def hold(self, t):
        if t > self.t + 1e-9:
            self.k.append([round(t, 5), self.v, "lin"])

    def snap(self, t, v):
        self.hold(t - EPS)
        self.to(t, v)

    def moves(self):
        return len(self.k) > 1

    def val(self, t):
        k = self.k
        if t <= k[0][0]:
            return k[0][1]
        for i in range(len(k) - 1):
            if t < k[i + 1][0]:
                a, b = k[i], k[i + 1]
                return mix(a[1], b[1], eased((t - a[0]) / (b[0] - a[0]), b[2]))
        return k[-1][1]

    def keys(self):
        ks = [list(x) for x in self.k]
        assert ks[-1][0] <= T + 1e-6, f"key past loop end: {ks[-1]}"
        if ks[-1][0] < T - 1e-6:
            ks.append([T, ks[-1][1], "lin"])
        else:
            ks[-1][0] = T
        return ks


def anim(attr, tr, fmt=n, skip_static=False, tf=None):
    ks = tr.keys()
    vals = [fmt(v) for _, v, _ in ks]
    if skip_static and len(set(vals)) == 1:
        return ""
    kt = ";".join(f"{t / T:.5f}" for t, _, _ in ks)
    spl = ""
    if any(e != "lin" for _, _, e in ks[1:]):
        spl = f' calcMode="spline" keySplines="{";".join(SPLINES[e] for _, _, e in ks[1:])}"'
    head = f'<animateTransform attributeName="transform" type="{tf}"' if tf else f'<animate attributeName="{attr}"'
    return f'{head} values="{";".join(vals)}" keyTimes="{kt}"{spl} dur="{T}s" repeatCount="indefinite"/>'


def tf_open(kind, tr, fmt, attrs=""):
    """Opens a <g> that carries a transform animation (or a plain transform when static)."""
    ks = tr.keys()
    vals = [fmt(v) for _, v, _ in ks]
    if len(set(vals)) == 1:
        return f'<g{attrs} transform="{kind}({vals[0]})">'
    return f"<g{attrs}>" + anim("transform", tr, fmt, tf=kind)


def op_open(tr):
    return f'<g opacity="{f2(tr.k[0][1])}">' + anim("opacity", tr, f2, skip_static=True)


# ------------------------------------------------------------------ poses
# local coords, feet at (0,0), up is -y, facing +x. WT = weapon tip.
def P_(**kw):
    return {k: tuple(v) for k, v in kw.items()}


POSES = {
    "stand":  P_(H=(0, -30), N=(0, -25), P=(0, -13), LE=(-3, -18), LH=(-4, -11), RE=(3, -18), RH=(4, -11), LK=(-2, -6), LF=(-3, 0), RK=(2, -6), RF=(3, 0)),
    "guard":  P_(H=(1, -30), N=(0, -25), P=(-1, -13), LE=(-4, -19), LH=(-7, -14), RE=(5, -21), RH=(10, -26), LK=(-5, -6), LF=(-7, 0), RK=(4, -6), RF=(7, 0), WT=(28, -38)),
    "block":  P_(H=(1, -30), N=(0, -25), P=(-1, -13), LE=(-4, -19), LH=(-7, -14), RE=(5, -22), RH=(9, -28), LK=(-5, -6), LF=(-7, 0), RK=(4, -6), RF=(7, 0), WT=(13, -48)),
    "sw_wind": P_(H=(-1, -30), N=(-1, -25), P=(-2, -13), LE=(-5, -19), LH=(-8, -14), RE=(-1, -28), RH=(-4, -35), LK=(-5, -6), LF=(-7, 0), RK=(3, -6), RF=(5, 0), WT=(-17, -52)),
    "sw_cut": P_(H=(3, -29), N=(2, -24), P=(0, -13), LE=(-3, -19), LH=(-6, -14), RE=(8, -22), RH=(14, -21), LK=(-5, -6), LF=(-8, 0), RK=(5, -7), RF=(9, 0), WT=(33, -13)),
    "sw_thru": P_(H=(4, -27), N=(3, -22), P=(1, -12), LE=(-3, -18), LH=(-6, -13), RE=(8, -17), RH=(13, -14), LK=(-5, -6), LF=(-8, 0), RK=(5, -6), RF=(9, 0), WT=(32, -7)),
    "runA":   P_(H=(2, -29), N=(1, -24), P=(-1, -13), LE=(3, -19), LH=(8, -17), RE=(-3, -19), RH=(-8, -14), LK=(-6, -8), LF=(-10, -3), RK=(5, -8), RF=(9, 0)),
    "runP":   P_(H=(2, -30), N=(1, -25), P=(0, -14), LE=(-1, -18), LH=(2, -13), RE=(1, -18), RH=(-2, -13), LK=(1, -8), LF=(-1, -1), RK=(0, -9), RF=(-4, -5)),
    "crouch": P_(H=(1, -21), N=(0, -17), P=(0, -9), LE=(-3, -13), LH=(-4, -8), RE=(3, -13), RH=(4, -8), LK=(-5, -4), LF=(-4, 0), RK=(5, -4), RF=(6, 0)),
    "tuck":   P_(H=(1, -30), N=(0, -25), P=(0, -14), LE=(-4, -22), LH=(-7, -27), RE=(4, -22), RH=(7, -27), LK=(-3, -12), LF=(-4, -6), RK=(5, -10), RF=(2, -5)),
    "fall":   P_(H=(0, -30), N=(0, -25), P=(0, -13), LE=(-6, -26), LH=(-10, -30), RE=(6, -26), RH=(10, -30), LK=(-3, -6), LF=(-5, 0), RK=(3, -6), RF=(5, 0)),
    "hang":   P_(H=(0, -30), N=(0, -25), P=(0, -13), LE=(-3, -34), LH=(-1, -42), RE=(3, -34), RH=(1, -42), LK=(-2, -7), LF=(-4, 0), RK=(3, -8), RF=(5, -1)),
    "cheer":  P_(H=(0, -30), N=(0, -25), P=(0, -13), LE=(-5, -29), LH=(-8, -37), RE=(5, -29), RH=(7, -36), LK=(-4, -6), LF=(-6, 0), RK=(4, -6), RF=(6, 0), WT=(9, -56)),
    "wind_throw": P_(H=(-1, -30), N=(-1, -25), P=(-1, -13), LE=(2, -21), LH=(6, -23), RE=(-1, -24), RH=(-6, -32), LK=(-5, -6), LF=(-7, 0), RK=(3, -6), RF=(5, 0)),
    "throw":  P_(H=(2, -30), N=(1, -25), P=(0, -13), LE=(-3, -19), LH=(-6, -14), RE=(7, -27), RH=(14, -34), LK=(-4, -6), LF=(-6, 0), RK=(4, -6), RF=(7, 0)),
    "hit":    P_(H=(-3, -28), N=(-1, -24), P=(1, -13), LE=(-6, -22), LH=(-11, -26), RE=(5, -21), RH=(9, -17), LK=(-2, -7), LF=(1, 0), RK=(3, -6), RF=(6, 0)),
    "fly":    P_(H=(2, -30), N=(0, -25), P=(0, -14), LE=(-6, -30), LH=(-9, -37), RE=(6, -30), RH=(9, -37), LK=(-3, -8), LF=(-6, -3), RK=(3, -8), RF=(7, -4)),
    "light":  P_(H=(2, -22), N=(1, -18), P=(0, -9), LE=(-3, -12), LH=(-4, -7), RE=(5, -12), RH=(11, -9), LK=(-5, -4), LF=(-4, 0), RK=(5, -4), RF=(6, 0)),
}


def mirror(p):
    q = {k: v for k, v in p.items() if k != "WT"}
    for a, b in (("LE", "RE"), ("LH", "RH"), ("LK", "RK"), ("LF", "RF")):
        q[a], q[b] = p[b], p[a]
    return q


def breathe(p):
    q = dict(p)
    for k in ("H", "N"):
        q[k] = (p[k][0], p[k][1] - 1)
    for k in ("LE", "RE", "LH", "RH", "WT"):
        if k in p:
            q[k] = (p[k][0], p[k][1] - 0.6)
    return q


def armed(p):
    """The same run frame with the sword held forward in the right hand."""
    q = dict(p)
    q.update(RE=(4, -21), RH=(9, -25), WT=(27, -33))
    return q


POSES.update(
    kick=P_(H=(-2, -28), N=(-1, -23), P=(-3, -12), LE=(-7, -20), LH=(-12, -17), RE=(3, -20), RH=(7, -24), LK=(-6, -5), LF=(-10, -1), RK=(6, -13), RF=(18, -17)),
    chop=P_(H=(4, -27), N=(3, -22), P=(1, -12), LE=(-3, -18), LH=(-6, -13), RE=(8, -19), RH=(13, -17), LK=(-5, -6), LF=(-8, 0), RK=(5, -6), RF=(9, 0), WT=(34, 2)),
    pull=P_(H=(-4, -29), N=(-2, -24), P=(0, -13), LE=(3, -22), LH=(8, -20), RE=(4, -20), RH=(9, -17), LK=(-4, -6), LF=(-9, 0), RK=(4, -6), RF=(8, 0)),
    taunt=P_(H=(1, -30), N=(0, -25), P=(-1, -13), LE=(-4, -19), LH=(-7, -14), RE=(6, -22), RH=(14, -26), LK=(-3, -6), LF=(-5, 0), RK=(4, -6), RF=(6, 0)),
    roll=P_(H=(3, -14), N=(1, -12), P=(-2, -8), LE=(4, -9), LH=(6, -5), RE=(3, -9), RH=(6, -4), LK=(4, -6), LF=(0, -2), RK=(5, -6), RF=(1, -3)),
    lying=P_(H=(15, -4), N=(10, -4), P=(-4, -3), LE=(12, -8), LH=(18, -10), RE=(8, -1), RH=(2, -1), LK=(-10, -6), LF=(-16, -2), RK=(-10, -1), RF=(-17, 0)),
    wind_hi=P_(H=(-1, -28), N=(-1, -23), P=(-2, -12), LE=(-4, -19), LH=(-6, -14), RE=(-2, -30), RH=(-3, -39), LK=(-5, -5), LF=(-8, 0), RK=(4, -5), RF=(7, 0), WT=(-2, -60)),
)


def down(p):
    """The low point of a stride: body dips, knees bend."""
    q = dict(p)
    for k in ("H", "N", "P", "LE", "LH", "RE", "RH"):
        q[k] = (p[k][0], p[k][1] + 2.2)
    q["LK"], q["RK"] = (p["LK"][0], p["LK"][1] + 0.8), (p["RK"][0], p["RK"][1] + 0.8)
    return q


POSES["runD"] = down(POSES["runP"])
for _nm in ("runA", "runP", "runD"):
    POSES[_nm + "2"] = mirror(POSES[_nm])
RUN = ["runA", "runD", "runP", "runA2", "runD2", "runP2"]      # contact, down, passing, then the other leg
RUN_BOB = [0, 1.4, -0.7, 0, 1.4, -0.7]
for _nm in RUN:
    POSES[_nm + "s"] = armed(POSES[_nm])
RUN_S = [nm + "s" for nm in RUN]
for _nm in ("stand", "guard"):
    POSES[_nm + "_b"] = breathe(POSES[_nm])
for _p in POSES.values():
    _p.setdefault("WT", (_p["RH"][0] + 4, _p["RH"][1] - 20))

JOINTS = ("H", "N", "P", "LE", "LH", "RE", "RH", "LK", "LF", "RK", "RF", "WT")
LIMBS = [("N", "P"), ("N", "LE", "LH"), ("N", "RE", "RH"), ("P", "LK", "LF"), ("P", "RK", "RF")]
HATS = {
    "tricorn": [(-8, -3), (-4, -7), (0, -13), (4, -7), (8, -3), (0, -5.5)],
    "bicorne": [(-10, -3), (-6, -8), (0, -10), (6, -8), (10, -3), (6, -5), (0, -7), (-6, -5)],
}
STRAP = [(-5.2, -3.2), (5.2, 1.0)]
PATCH = [(1.2, -1.4), (3.6, 0.1)]


def lerp_pose(a, b, s):
    return {k: (a[k][0] + (b[k][0] - a[k][0]) * s, a[k][1] + (b[k][1] - a[k][1]) * s) for k in JOINTS}


def pose_val(tr, t):
    k = tr.k
    if t <= k[0][0]:
        return POSES[k[0][1]]
    for i in range(len(k) - 1):
        if t < k[i + 1][0]:
            a, b = k[i], k[i + 1]
            return lerp_pose(POSES[a[1]], POSES[b[1]], eased((t - a[0]) / (b[0] - a[0]), b[2]))
    return POSES[k[-1][1]]


def pts(points):
    return " ".join(f"{n(x)},{n(y)}" for x, y in points)


def limb_pts(P, limb):
    return pts([P[j] for j in limb])


def head_rel(P, rel):
    return pts([(P["H"][0] + x, P["H"][1] + y) for x, y in rel])


def blade_parts(P, bend):
    """Blade polygon, cross-guard and grip for a sword held in the right hand."""
    rh, wt = P["RH"], P["WT"]
    dx, dy = wt[0] - rh[0], wt[1] - rh[1]
    L = math.hypot(dx, dy) or 1.0
    ux, uy = dx / L, dy / L
    px, py = -uy, ux

    def spine(s):
        c = 4 * bend * L * s * (1 - s)
        return rh[0] + dx * s + px * c, rh[1] + dy * s + py * c

    def off(pt, side, w):
        return pt[0] + px * side * w, pt[1] + py * side * w

    back = [off(spine(s), 1, 1.3 - 0.9 * s) for s in (0.1, 0.4, 0.7, 0.9)]
    edge = [off(spine(s), -1, 1.3 - 0.9 * s) for s in (0.9, 0.7, 0.4, 0.1)]
    guard = [(rh[0] + ux * 2 + px * 3.6, rh[1] + uy * 2 + py * 3.6), (rh[0] + ux * 2 - px * 3.6, rh[1] + uy * 2 - py * 3.6)]
    grip = [(rh[0] - ux * 4, rh[1] - uy * 4), (rh[0] + ux, rh[1] + uy)]
    return back + [wt] + edge, guard, grip


# ------------------------------------------------------------------ characters
class Char:
    def __init__(self, pose0="stand", pos0=(0, 0), face0=1):
        self.pos = Track((float(pos0[0]), float(pos0[1])))
        self.rot = Track((0.0, 0.0, PIV))
        self.sx = Track(float(face0))
        self.sq = Track((1.0, 1.0))
        self.op = Track(0)
        self.pz = Track(pose0)
        self.wop = Track(0)

    # --- placement and movement
    def at(self, t, x, y, ease="lin"):
        self.pos.to(t, (float(x), float(y)), ease)

    def hold(self, t):
        self.pos.hold(t)

    def jump(self, t0, t1, x1, y1, h, step=0.04):
        self.pos.hold(t0)
        x0, y0 = self.pos.v
        k = max(4, int(round((t1 - t0) / step)))
        for i in range(1, k + 1):
            s = i / k
            self.pos.to(t0 + (t1 - t0) * s, (x0 + (x1 - x0) * s, y0 + (y1 - y0) * s - 4 * h * s * (1 - s)))

    def run(self, t0, t1, x1, armed_=False, frame=0.06):
        cyc = RUN_S if armed_ else RUN
        self.pos.hold(t0)
        x0, y = self.pos.v
        t, i = t0, 0
        while t < t1 - 1e-6:
            self.pose(t, cyc[i % 6], tween=frame * 0.9, ease="inout")
            t += frame
            i += 1
            tt = min(t, t1)
            s = (tt - t0) / (t1 - t0)
            self.pos.to(tt, (x0 + (x1 - x0) * s, y + RUN_BOB[i % 6]))
        self.pos.to(t1 + EPS, (float(x1), y))

    def pose(self, t, name, tween=0.08, ease="out"):
        assert name in POSES, name
        self.pz.hold(t - tween)
        self.pz.to(t, name, ease)

    def idle(self, t0, t1, base="stand", period=0.5):
        t, i = t0, 0
        while t < t1 - 1e-6:
            self.pose(t, base if i % 2 == 0 else base + "_b", tween=period * 0.9, ease="inout")
            t += period
            i += 1

    def face(self, t, d):
        self.sx.snap(t, float(d))

    def land(self, t, amount=0.26, pose="crouch"):
        self.sq.snap(t, (1 + amount, 1 - amount))
        self.sq.to(t + 0.09, (0.95, 1.05), "out")
        self.sq.to(t + 0.17, (1.0, 1.0), "out")
        if pose:
            self.pose(t, pose, tween=0.03)

    def takeoff(self, t, amount=0.12):
        self.sq.hold(t - 0.05)
        self.sq.to(t, (1 - amount, 1 + amount), "out")
        self.sq.to(t + 0.1, (1.0, 1.0), "out")

    def hitstop(self, t, dur):
        for tr in (self.pos, self.rot, self.pz, self.sq):
            tr.hold(t)
            tr.hold(t + dur)

    def jitter(self, t0, t1, amp, hz=26):
        """Strain: the figure trembles in place."""
        self.pos.hold(t0)
        bx, by = self.pos.v
        t, i = t0, 0
        while t < t1 - 1 / hz:
            t += 1 / hz
            i += 1
            self.pos.to(t, (bx + amp * (1 if i % 2 else -1), by))
        self.pos.to(t1, (bx, by))

    def spin(self, t0, t1, deg, ease="inout"):
        """A full turn about the body centre; the figure ends upright again."""
        self.rot.snap(t0, (0.0, 0.0, PIV))
        self.rot.to(t1, (float(deg), 0.0, PIV), ease)
        self.rot.snap(t1 + EPS, (0.0, 0.0, PIV))

    def drop(self, t0, t1, x1, y1, step=0.04):
        """Fall under gravity (slow at first, fast at the end)."""
        self.pos.hold(t0)
        x0, y0 = self.pos.v
        k = max(3, int(round((t1 - t0) / step)))
        for i in range(1, k + 1):
            s = i / k
            self.pos.to(t0 + (t1 - t0) * s, (x0 + (x1 - x0) * s, y0 + (y1 - y0) * s * s))

    def show(self, t):
        self.op.snap(t, 1)

    def hide(self, t):
        self.op.snap(t, 0)

    def weapon(self, t, on):
        self.wop.snap(t, 1 if on else 0)

    def world(self, t, key):
        """Where a joint is on the page at time t (so effects land on the hand, not near it)."""
        x, y = pose_val(self.pz, t)[key]
        sx = self.sx.val(t)
        qx, qy = self.sq.val(t)
        x, y = x * sx * qx * S, y * qy * S
        a, px, py = self.rot.val(t)
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        dx, dy = x - px, y - py
        x, y = px + dx * ca - dy * sa, py + dx * sa + dy * ca
        X, Y = self.pos.val(t)
        return X + x, Y + y

    # --- drawing
    def svg(self, p, body, hat=None, hat_fill=None, patch=False, sword=None):
        p0 = POSES[self.pz.k[0][1]]
        out = [op_open(self.op), tf_open("translate", self.pos, fxy), tf_open("rotate", self.rot, frot),
               tf_open("scale", self.sx, fface), tf_open("scale", self.sq, fsc), f'<g transform="scale({S})">']
        name = lambda f: (lambda nm: f(POSES[nm]))
        out.append(f'<circle r="5" fill="{body}" cx="{n(p0["H"][0])}" cy="{n(p0["H"][1])}">'
                   + anim("cx", self.pz, name(lambda P: n(P["H"][0])), True)
                   + anim("cy", self.pz, name(lambda P: n(P["H"][1])), True) + "</circle>")
        for limb in LIMBS:
            out.append(f'<polyline fill="none" stroke="{body}" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" '
                       f'points="{limb_pts(p0, limb)}">' + anim("points", self.pz, name(lambda P, limb=limb: limb_pts(P, limb)), True) + "</polyline>")
        if hat:
            out.append(f'<polygon fill="{hat_fill}" stroke="{p["fg"]}" stroke-width="0.6" stroke-linejoin="round" points="{head_rel(p0, HATS[hat])}">'
                       + anim("points", self.pz, name(lambda P: head_rel(P, HATS[hat])), True) + "</polygon>")
        if patch:
            for rel, w in ((STRAP, 0.9), (PATCH, 2.6)):
                out.append(f'<polyline fill="none" stroke="{p["fg"]}" stroke-width="{w}" stroke-linecap="round" points="{head_rel(p0, rel)}">'
                           + anim("points", self.pz, name(lambda P, rel=rel: head_rel(P, rel)), True) + "</polyline>")
        if sword is not None:
            bend = sword
            part = lambda i: name(lambda P: (pts(blade_parts(P, bend)[0]), pts(blade_parts(P, bend)[1]), pts(blade_parts(P, bend)[2]))[i])
            out.append(f'<g opacity="0">' + anim("opacity", self.wop, f2) + f'<polyline fill="none" stroke="{p["fg"]}" stroke-width="2" stroke-linecap="round" points="{pts(blade_parts(p0, bend)[2])}">'
                       + anim("points", self.pz, part(2), True) + "</polyline>"
                       + f'<polygon fill="{p["steel"]}" stroke="{p["fg"]}" stroke-width="0.7" stroke-linejoin="round" points="{pts(blade_parts(p0, bend)[0])}">'
                       + anim("points", self.pz, part(0), True) + "</polygon>"
                       + f'<polyline fill="none" stroke="{p["fg"]}" stroke-width="1.6" stroke-linecap="round" points="{pts(blade_parts(p0, bend)[1])}">'
                       + anim("points", self.pz, part(1), True) + "</polyline></g>")
        out.append("</g></g></g></g></g></g>")
        return "".join(out)


# ------------------------------------------------------------------ geometry for breaking things
def clip_poly(poly, a, b, c):
    """Keep the part of a convex polygon where a*x + b*y <= c (one Sutherland-Hodgman step)."""
    out = []
    for i, (x1, y1) in enumerate(poly):
        x2, y2 = poly[(i + 1) % len(poly)]
        d1, d2 = a * x1 + b * y1 - c, a * x2 + b * y2 - c
        if d1 <= 0:
            out.append((x1, y1))
        if (d1 < 0) != (d2 < 0) and d1 != d2:
            t = d1 / (d1 - d2)
            out.append((x1 + (x2 - x1) * t, y1 + (y2 - y1) * t))
    return out


def poly_area_centroid(poly):
    a = cx = cy = 0.0
    for i, (x1, y1) in enumerate(poly):
        x2, y2 = poly[(i + 1) % len(poly)]
        k = x1 * y2 - x2 * y1
        a += k
        cx += (x1 + x2) * k
        cy += (y1 + y2) * k
    if abs(a) < 1e-6:
        return 0.0, poly[0][0], poly[0][1]
    return abs(a) / 2, cx / (3 * a), cy / (3 * a)


def in_poly(poly, x, y):
    inside = False
    for i, (x1, y1) in enumerate(poly):
        x2, y2 = poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


# ------------------------------------------------------------------ pieces: letters, poster
_clip_id = [0]
GRAVITY = 950.0


class Piece:
    """Something that moves, rotates, fades, pops, and can be cut in half or shattered.

    Cut (blade):    slice() makes two clipped copies that fall apart along a line.
    Shatter (blunt): crack() draws cracks that grow from the impact point, and release() breaks
                    the piece into Voronoi fragments. Each fragment within reach of the blow is
                    thrown with a speed that falls off with distance, a direction made of the
                    blow plus "away from the impact point", and a spin from the off-centre push.
                    It then falls under gravity, bounces on the floor and fades. Fragments
                    outside the reach stay where they are, so a letter can lose just a corner."""

    def __init__(self, inner, cx, cy, pivot=None, build=None, bbox=None, ink=None):
        self.inner, self.cx, self.cy = inner, cx, cy
        self.pivot = pivot or (cx, cy)
        self.tr, self.rot, self.op, self.sc = Track((0.0, 0.0)), Track(0.0), Track(1), Track(1.0)
        self.halves, self.clip = [], None
        self.build, self.bbox, self.ink = build, bbox, ink
        self.frags, self.cracks, self.cop, self.crack_col, self.broken_at = [], [], Track(1), "#fff", None

    def shake(self, t0, t1, amp, hz=28):
        self.tr.hold(t0)
        bx, by = self.tr.v
        t, i = t0, 0
        while t < t1 - 1 / hz:
            t += 1 / hz
            i += 1
            self.tr.to(t, (bx + amp * (1 if i % 2 else -1), by + amp * 0.4 * (1 if (i // 2) % 2 else -1)))
        self.tr.to(t1, (bx, by))

    def slice(self, t, angle, fall=((-22, 70), (22, -110)), land_y=None, dur=0.55, reach=170, fade=None, through=None, paper=False):
        """Cut along a line at `angle` degrees; both halves drop to the floor.
        through: the page point the blade crossed (defaults to the centre).
        fade: seconds after landing before the halves fade away (default: they stay).
        paper: the halves flutter down, swaying, instead of dropping like a stone."""
        land_y = FLOOR - 7 if land_y is None else land_y
        self.op.snap(t, 0)
        a = math.radians(angle)
        d, nn = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))
        c = through or (self.cx, self.cy)
        for sgn, (ddx, drot) in zip((1, -1), fall):
            h = Piece(self.inner, self.cx, self.cy)
            h.op = Track(0)
            h.op.snap(t, 1)
            h.clip = [(c[0] + d[0] * reach, c[1] + d[1] * reach), (c[0] - d[0] * reach, c[1] - d[1] * reach),
                      (c[0] - d[0] * reach + sgn * nn[0] * reach, c[1] - d[1] * reach + sgn * nn[1] * reach),
                      (c[0] + d[0] * reach + sgn * nn[0] * reach, c[1] + d[1] * reach + sgn * nn[1] * reach)]
            x0, y0 = sgn * nn[0] * 4, sgn * nn[1] * 4
            h.tr.hold(t)
            h.tr.to(t + 0.08, (x0, y0), "out")
            h.rot.hold(t + 0.08)
            steps = 18 if paper else 10
            for i in range(1, steps + 1):
                s = i / steps
                fall_s = (s * (2 - s)) * 0.55 + s * 0.45 if paper else s * s        # paper drifts, stone accelerates
                sway = (sgn * 14 * math.sin(s * 9) * (1 - s)) if paper else 0
                h.tr.to(t + 0.08 + dur * s, (x0 + (ddx - x0) * s + sway, y0 + (land_y - self.cy - y0) * fall_s))
                h.rot.to(t + 0.08 + dur * s, drot * s + (sgn * 16 * math.sin(s * 7) * (1 - s) if paper else 0))
            if fade is not None:
                h.op.hold(t + 0.08 + dur + fade)
                h.op.to(t + 0.08 + dur + fade + 0.4, 0, "in")
            self.halves.append(h)

    # --- blunt impacts
    def crack(self, t, pt, count, reach, colour, width=1.7, seed=1):
        """Cracks grow outward from the impact point (stroke-dashoffset), with a fork or two."""
        self.crack_col = colour
        for i in range(count):
            base = 2 * math.pi * (i + 0.5) / count + (rnd(seed * 5 + i) - 0.5) * 0.9
            L = reach * (0.55 + 0.45 * rnd(seed * 3 + i))
            pts_, ang = [pt], base
            for k in range(1, 6):
                ang += (rnd(seed * 7 + i * 5 + k) - 0.5) * 0.9
                pts_.append((pt[0] + L * k / 5 * math.cos(ang), pt[1] + L * k / 5 * math.sin(ang)))
            d = "M" + "L".join(f"{n(x)},{n(y)}" for x, y in pts_)
            if rnd(seed * 11 + i) < 0.7:
                bx, by = pts_[3]
                fa = ang + (0.9 if i % 2 else -0.9)
                d += f"M{n(bx)},{n(by)}L{n(bx + L * 0.3 * math.cos(fa))},{n(by + L * 0.3 * math.sin(fa))}"
            dash = Track(1.0)
            dash.hold(t + 0.01 * i)
            dash.to(t + 0.09 + 0.015 * i, 0.0, "out")
            self.cracks.append((d, dash, width))

    def _cracks_svg(self):
        if not self.cracks:
            return ""
        paths = "".join(f'<path d="{d}" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1" stroke-width="{w}">'
                        + anim("stroke-dashoffset", dash, f2) + "</path>" for d, dash, w in self.cracks)
        return op_open(self.cop) + f'<g fill="none" stroke="{self.crack_col}" stroke-linecap="round" stroke-linejoin="round">{paths}</g></g>'

    def make_frags(self, cell=34.0, seed=1):
        """Cut the piece into Voronoi cells (jittered grid of seeds), keeping the ones that hold ink."""
        if self.frags:
            return
        x0, y0, x1, y1 = self.bbox
        nx, ny = max(1, round((x1 - x0) / cell)), max(1, round((y1 - y0) / cell))
        cw, ch = (x1 - x0) / nx, (y1 - y0) / ny
        seeds = [(x0 + (i + 0.5 + 0.75 * (rnd(seed * 31 + i * 7 + j) - 0.5)) * cw,
                  y0 + (j + 0.5 + 0.75 * (rnd(seed * 17 + i + j * 13) - 0.5)) * ch) for j in range(ny) for i in range(nx)]
        for k, (sx, sy) in enumerate(seeds):
            poly = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            for m, (ox, oy) in enumerate(seeds):
                if m != k:
                    poly = clip_poly(poly, 2 * (ox - sx), 2 * (oy - sy), ox * ox + oy * oy - sx * sx - sy * sy)
                    if len(poly) < 3:
                        break
            if len(poly) < 3:
                continue
            xs, ys = [p_[0] for p_ in poly], [p_[1] for p_ in poly]
            hit = any(in_poly(poly, xs_, ys_) and self.ink(xs_, ys_)
                      for xs_ in [min(xs) + (max(xs) - min(xs)) * (a + 0.5) / 6 for a in range(6)]
                      for ys_ in [min(ys) + (max(ys) - min(ys)) * (b + 0.5) / 6 for b in range(6)])
            if not hit:
                continue
            area, fx, fy = poly_area_centroid(poly)
            grown = [(fx + (x - fx) * (1 + 0.7 / max(1.0, math.hypot(x - fx, y - fy))), fy + (y - fy) * (1 + 0.7 / max(1.0, math.hypot(x - fx, y - fy)))) for x, y in poly]
            f = Piece(self.build((min(xs) - 2, min(ys) - 2, max(xs) + 2, max(ys) + 2)), fx, fy)
            f.clip, f.op, f.r, f.gone = grown, Track(0), math.sqrt(area / math.pi) * 0.8, False
            self.frags.append(f)

    def release(self, t, pt, d, force, R, seed=1, linger=1.3):
        """Everything within R of the impact point breaks loose and is thrown (see class docstring)."""
        self.make_frags(seed=seed)
        if self.broken_at is None:
            self.broken_at = t
            self.op.snap(t, 0)
            self.cop.snap(t, 0)
            for f in self.frags:
                f.op.snap(t, 1)
        dl = math.hypot(*d) or 1.0
        ux, uy = d[0] / dl, d[1] / dl
        for k, f in enumerate(self.frags):
            dx, dy = f.cx - pt[0], f.cy - pt[1]
            dist = math.hypot(dx, dy) or 1.0
            if f.gone or dist > R:
                continue
            f.gone = True
            fall = math.exp(-dist / (R * 0.6))
            rx, ry = dx / dist, dy / dist
            vx = force * fall * (0.7 * ux + 0.5 * rx) + (rnd(seed * 3 + k) - 0.5) * 50
            vy = force * fall * (0.7 * uy + 0.5 * ry) - 70 * fall + (rnd(seed * 5 + k) - 0.5) * 50
            w = ((rx * uy - ry * ux) * force * fall * 0.55 + (rnd(seed * 9 + k) - 0.5) * 220)
            td = t + dist / 900.0                              # the shock takes a moment to arrive
            x = y = ang = 0.0
            f.tr.hold(td)
            f.rot.hold(td)
            tt, settled = td, False
            while tt < td + 2.6 and not settled:
                tt += 0.05
                vy += GRAVITY * 0.05
                x += vx * 0.05
                y += vy * 0.05
                ang += w * 0.05
                if f.cy + y + f.r > FLOOR:
                    y -= f.cy + y + f.r - FLOOR
                    if abs(vy) < 110:
                        vy, vx, w = 0.0, vx * 0.5, w * 0.5
                        settled = abs(vx) < 25
                    else:
                        vy, vx, w = -vy * 0.32, vx * 0.62, w * 0.55
                f.tr.to(tt, (x, y))
                f.rot.to(tt, ang)
                if f.cx + x < -40 or f.cx + x > W + 40:
                    break
            f.op.hold(tt + linger)
            f.op.to(tt + linger + 0.5, 0, "in")

    def reset(self, t):
        """Back to the whole, untouched piece (called while a wave hides the page)."""
        self.tr.snap(t, (0.0, 0.0))
        self.rot.snap(t, 0.0)
        self.op.snap(t, 1)
        self.cop.snap(t, 1)
        for h in self.halves:
            h.op.snap(t, 0)
        for f in self.frags:
            f.op.snap(t, 0)
        for _, dash, _ in self.cracks:
            dash.snap(t, 1.0)

    def svg(self):
        return self._body(True) + "".join(h._body() for h in self.halves) + "".join(f._body() for f in self.frags)

    def _body(self, cracks=False):
        inner = self.inner + (self._cracks_svg() if cracks else "")
        pre = ""
        if self.clip:
            _clip_id[0] += 1
            cid = f"cp{_clip_id[0]}"
            pre = f'<clipPath id="{cid}"><polygon points="{pts(self.clip)}"/></clipPath>'
            inner = f'<g clip-path="url(#{cid})">{inner}</g>'
        if not any(tr.moves() for tr in (self.tr, self.rot, self.op, self.sc)):
            return pre + inner
        px, py = self.pivot
        s = op_open(self.op) + tf_open("translate", self.tr, fxy)
        s += tf_open("rotate", self.rot, lambda a: f"{n(a)} {n(px)} {n(py)}")
        closers = 3
        if self.sc.moves():
            s += f'<g transform="translate({n(px)} {n(py)})">' + tf_open("scale", self.sc, fsc1) + f'<g transform="translate({n(-px)} {n(-py)})">'
            closers += 3
        return pre + s + inner + "</g>" * closers


def art_rows():
    rows = list(ART_RAW)
    width = max(len(r) for r in rows)
    if len(rows[0]) == width - 1:      # the top row of an "A" loses its leading space when pasted
        rows[0] = " " + rows[0]
    return [r.ljust(width) for r in rows]


def art_cell(c, ox, oy):
    """Path data for one box-drawing character, drawn as lines so it never depends on a font."""
    cx, cy, g = ox + CW / 2, oy + CH / 2, CW * 0.2
    L, R, T_, B = ox, ox + CW, oy, oy + CH
    a = lambda *v: [n(x) for x in v]
    m = {
        "═": "M{0},{1}H{2}M{0},{3}H{2}".format(*a(L, cy - g, R, cy + g)),
        "║": "M{0},{1}V{2}M{3},{1}V{2}".format(*a(cx - g, T_, B, cx + g)),
        "╔": "M{0},{1}H{2}V{3}M{0},{4}H{5}V{3}".format(*a(R, cy - g, cx - g, B, cy + g, cx + g)),
        "╗": "M{0},{1}H{2}V{3}M{0},{4}H{5}V{3}".format(*a(L, cy - g, cx + g, B, cy + g, cx - g)),
        "╚": "M{0},{1}V{2}H{3}M{4},{1}V{5}H{3}".format(*a(cx - g, T_, cy + g, R, cx + g, cy - g)),
        "╝": "M{0},{1}V{2}H{3}M{4},{1}V{5}H{3}".format(*a(cx + g, T_, cy + g, L, cx - g, cy - g)),
    }
    return m.get(c, "")


def letter_inner(p, rows, c0, c1, bbox=None):
    """Markup for one letter (or, with bbox, only the cells that touch that region)."""
    rects, d = [], ""
    for r, row in enumerate(rows):
        y = Y0 + r * CH
        if bbox and (y + CH < bbox[1] or y > bbox[3]):
            continue
        run = None
        for c in range(c0, c1 + 1):
            full = c < c1 and row[c] == "█"
            x = X0 + c * CW
            if full and run is None:
                run = c
            if not full and run is not None:
                if not bbox or (x >= bbox[0] and X0 + run * CW <= bbox[2]):
                    rects.append(f'<rect x="{n(X0 + run * CW)}" y="{n(y)}" width="{n((c - run) * CW)}" height="{n(CH + 0.4)}"/>')
                run = None
            if c < c1 and (not bbox or (x + CW >= bbox[0] and x <= bbox[2])):
                d += art_cell(row[c], x, y)
    return (f'<path d="{d}" fill="none" stroke="{p["fg"]}" stroke-width="1.8"/>'
            f'<g fill="{p["fg"]}">' + "".join(rects) + "</g>")


def art_letters(p):
    """One Piece per letter, so each can be cut or shattered on its own."""
    rows, pieces = art_rows(), []
    for c0, c1 in LETTER_COLS:
        def ink(x, y, c0=c0, c1=c1):
            col, row = int((x - X0) // CW), int((y - Y0) // CH)
            return c0 <= col < c1 and 0 <= row < len(rows) and rows[row][col] != " "
        bbox = (X0 + c0 * CW, Y0, X0 + c1 * CW, Y0 + len(rows) * CH)
        pieces.append(Piece(letter_inner(p, rows, c0, c1), X0 + (c0 + c1) / 2 * CW, Y0 + len(rows) * CH / 2,
                            build=lambda bb, c0=c0, c1=c1: letter_inner(p, rows, c0, c1, bb), bbox=bbox, ink=ink))
    return pieces


# ------------------------------------------------------------------ scene
class Scene:
    def __init__(self, theme):
        _clip_id[0] = 0
        self.p = PALETTES[theme]
        self.layers = {k: [] for k in ("props", "low", "mid", "high", "top")}
        self.frame = Track((0.0, 0.0))
        self.letters = art_letters(self.p)
        self.pieces = list(self.letters)
        self.pir = self.off = None
        self.crew = []
        self.defs = ""
        self.story()

    # --- effects
    def jolt(self, t, amp):
        self.frame.hold(t - EPS)
        for dt, fx, fy in [(0.03, 1, -0.6), (0.07, -0.7, 0.5), (0.11, 0.4, -0.3), (0.16, 0, 0)]:
            self.frame.to(t + dt, (amp * fx, amp * fy), "out")

    def flash(self, t, dur=0.07, amt=0.6):
        op = Track(0)
        op.snap(t, amt)
        op.to(t + dur, 0, "in")
        self.layers["top"].append(f'<rect width="{W}" height="{H}" fill="{self.p["flash"]}" opacity="0">' + anim("opacity", op, f2) + "</rect>")

    def spark(self, x, y, t, size=10, dur=0.24):
        p = self.p
        op = Track(0)
        op.snap(t, 1)
        op.hold(t + dur * 0.4)
        op.to(t + dur, 0, "in")
        ring = Track(1.0)
        ring.hold(t)
        ring.to(t + dur, size, "out")
        ray = Track(0.4)
        ray.hold(t)
        ray.to(t + dur * 0.7, 1.3, "out")
        d = "".join(f"M{n(math.cos(a) * size * 0.35)},{n(math.sin(a) * size * 0.35)}L{n(math.cos(a) * size * 0.95)},{n(math.sin(a) * size * 0.95)}"
                    for a in [i * math.pi / 4 + 0.2 for i in range(8)])
        self.layers["high"].append(
            f'<g transform="translate({n(x)} {n(y)})">' + op_open(op)
            + f'<circle r="1" fill="none" stroke="{p["spark"]}" stroke-width="1.4">' + anim("r", ring, n) + "</circle>"
            + tf_open("scale", ray, fsc1) + f'<path d="{d}" fill="none" stroke="{p["spark"]}" stroke-width="1.4" stroke-linecap="round"/></g></g></g>')

    def puff(self, layer, x, y, t, dx, dy, r0, r1, dur=0.4, alpha=0.55):
        tr = Track((0.0, 0.0))
        tr.hold(t)
        tr.to(t + dur, (dx, dy), "out")
        op = Track(0)
        op.snap(t, alpha)
        op.to(t + dur, 0, "in")
        r = Track(r0)
        r.hold(t)
        r.to(t + dur, r1, "out")
        self.layers[layer].append(f'<g transform="translate({n(x)} {n(y)})">' + tf_open("translate", tr, fxy) + op_open(op)
                                  + f'<circle r="{n(r0)}" fill="{self.p["smoke"]}">' + anim("r", r, n) + "</circle></g></g></g>")

    def dust(self, x, y, t, big=False):
        k = 5 if big else 3
        for i in range(k):
            d = i - (k - 1) / 2
            self.puff("low", x, y - 2, t, d * (9 if big else 6), -3 - 3 * rnd(i + t), 1.5, 4.5 + 2 * rnd(i), 0.35)

    def smoke(self, x, y, t, count=6):
        for i in range(count):
            self.puff("high", x, y, t + 0.02 * i, -22 - 16 * i - 8 * rnd(i), -6 - 9 * rnd(i + 3), 3, 9 + 3 * i, 0.9, 0.5)

    def mark(self, txt, x, y, t, dur=0.55):
        op = Track(0)
        op.snap(t, 1)
        op.hold(t + dur * 0.7)
        op.to(t + dur, 0, "in")
        tr = Track((0.0, 4.0))
        tr.hold(t)
        tr.to(t + 0.1, (0.0, -3.0), "out")
        self.layers["high"].append(f'<g transform="translate({n(x)} {n(y)})">' + tf_open("translate", tr, fxy) + op_open(op)
                                   + f'<text x="-3" y="0" font-size="17" font-weight="700" fill="{self.p["fg"]}">{html.escape(txt)}</text></g></g></g>')

    def hit(self, t, x, y, size, *chars, dur=0.07, shake=1.5, big=False):
        self.spark(x, y, t, size)
        for c in chars:
            c.hitstop(t, dur)
        self.jolt(t, shake)
        if big:
            self.flash(t, 0.08, 0.55)
            self.spark(x, y, t + 0.03, size * 1.6, 0.3)
        return t + dur

    # --- motion effects
    def swoosh(self, c, t0, t1, colour, a=0.5, k=8):
        """A smear that follows the blade tip between t0 and t1 (call after the pose tracks are set)."""
        tip = [c.world(t0 + (t1 - t0) * i / k, "WT") for i in range(k + 1)]
        mid = []
        for i in range(k + 1):
            tt = t0 + (t1 - t0) * i / k
            hx, hy = c.world(tt, "RH")
            wx, wy = tip[i]
            mid.append((hx + (wx - hx) * 0.35, hy + (wy - hy) * 0.35))
        op = Track(0)
        op.snap(t0 + 0.01, a)
        op.hold(t1)
        op.to(t1 + 0.14, 0, "in")
        self.layers["high"].append(op_open(op) + f'<polygon points="{pts(tip + mid[::-1])}" fill="{colour}"/></g>')

    def ghost(self, c, t, colour, a=0.4, dur=0.28):
        """A fading copy of the figure as it was at time t (afterimage)."""
        P = pose_val(c.pz, t)
        x, y = c.pos.val(t)
        sx, (qx, qy), (ang, px, py) = c.sx.val(t), c.sq.val(t), c.rot.val(t)
        op = Track(0)
        op.snap(t, a)
        op.to(t + dur, 0, "in")
        g = "".join(f'<polyline points="{limb_pts(P, l)}" fill="none" stroke="{colour}" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"/>' for l in LIMBS)
        g += f'<circle cx="{n(P["H"][0])}" cy="{n(P["H"][1])}" r="5" fill="{colour}"/>'
        self.layers["low"].append(op_open(op) + f'<g transform="translate({n(x)} {n(y)}) rotate({n(ang)} {n(px)} {n(py)}) scale({f2(sx * qx)} {f2(qy)}) scale({S})">{g}</g></g>')

    def trail(self, c, t0, t1, colour, count=4, a=0.4):
        for i in range(count):
            self.ghost(c, t0 + (t1 - t0) * i / max(1, count - 1), colour, a * (0.55 + 0.45 * i / max(1, count - 1)))

    def burst(self, x, y, t, size=16, big=False):
        """A comic starburst for one or two frames: the hit frame."""
        pts_ = []
        for i in range(12):
            r = size * (1.0 if i % 2 == 0 else 0.45) * (0.85 + 0.3 * rnd(i + x))
            a = i * math.pi / 6 + 0.2
            pts_.append((r * math.cos(a), r * math.sin(a)))
        sc, op = Track(0.3), Track(0)
        op.snap(t, 1)
        op.hold(t + 0.07)
        op.snap(t + 0.1, 0)
        sc.hold(t)
        sc.to(t + 0.05, 1.2, "out")
        sc.to(t + 0.1, 1.0)
        self.layers["high"].append(f'<g transform="translate({n(x)} {n(y)})">' + op_open(op) + tf_open("scale", sc, fsc1)
                                   + f'<polygon points="{pts(pts_)}" fill="{self.p["spark"]}" stroke="{self.p["fg"]}" stroke-width="1.2" stroke-linejoin="round"/></g></g></g>')
        if big:
            self.shock(x, y + 4, t, 70)

    def shock(self, x, y, t, r=60):
        """A ring of force that spreads along the floor."""
        sc, op = Track(0.1), Track(0)
        op.snap(t, 0.8)
        op.to(t + 0.3, 0, "in")
        sc.hold(t)
        sc.to(t + 0.3, 1.0, "out")
        self.layers["low"].append(f'<g transform="translate({n(x)} {n(y)})">' + op_open(op) + tf_open("scale", sc, fsc1)
                                  + f'<ellipse rx="{r}" ry="{n(r * 0.16)}" fill="none" stroke="{self.p["fg"]}" stroke-width="1.6"/></g></g></g>')

    def speed(self, x, y, d, t, dur=0.22, count=4, length=70):
        """Streaks behind something moving in direction d (+1 right, -1 left)."""
        for i in range(count):
            yy = y - 8 - i * 11 + 4 * rnd(i + t)
            L = length * (0.6 + 0.6 * rnd(i * 3 + t))
            tr, op = Track((0.0, 0.0)), Track(0)
            op.snap(t, 0.6)
            op.to(t + dur, 0, "in")
            tr.hold(t)
            tr.to(t + dur, (-d * 26, 0.0), "out")
            self.layers["low"].append(f'<g transform="translate({n(x)} {n(yy)})">' + op_open(op) + tf_open("translate", tr, fxy)
                                      + f'<path d="M0,0 h{n(-d * L)}" stroke="{self.p["fg"]}" stroke-width="1.5" stroke-linecap="round"/></g></g></g>')

    def dip(self, pc, t, amt=4.0):
        """The letter gives under a footstep, then springs back."""
        pc.tr.hold(t)
        x0, y0 = pc.tr.v
        pc.tr.to(t + 0.05, (x0, y0 + amt), "out")
        pc.tr.to(t + 0.13, (x0, y0 - amt * 0.35), "out")
        pc.tr.to(t + 0.22, (x0, y0), "inout")

    def chips(self, x, y, t, count, d=(0.0, -1.0), speed=130.0):
        """Small bits of ink thrown from an impact: they arc, drop and fade."""
        for i in range(count):
            vx = d[0] * speed * (0.4 + rnd(i + x)) + (rnd(i * 3 + y) - 0.5) * speed
            vy = d[1] * speed * (0.4 + rnd(i * 5 + x)) - 50 + (rnd(i * 7 + y) - 0.5) * speed * 0.6
            tr, op = Track((0.0, 0.0)), Track(0)
            op.snap(t, 1)
            tr.hold(t)
            px_ = py_ = 0.0
            for k in range(1, 10):
                vy += GRAVITY * 0.05
                px_ += vx * 0.05
                py_ = min(py_ + vy * 0.05, FLOOR - y - 2)
                tr.to(t + 0.05 * k, (px_, py_))
            op.hold(t + 0.4)
            op.to(t + 0.55, 0, "in")
            sz = 2.0 + 2.4 * rnd(i * 11 + x)
            self.layers["high"].append(f'<g transform="translate({n(x)} {n(y)})">' + op_open(op) + tf_open("translate", tr, fxy)
                                       + f'<rect x="{n(-sz / 2)}" y="{n(-sz / 2)}" width="{n(sz)}" height="{n(sz * 0.8)}" fill="{self.p["fg"]}"/></g></g></g>')

    def smash(self, pc, t, pt, d, force, R, lead=0.06, seed=1):
        """A blunt blow on a letter: cracks race out for `lead` seconds, then everything within R of
        the impact point breaks loose and is thrown (see Piece.release)."""
        if lead and pc.broken_at is None:
            pc.crack(t - lead, pt, 5, min(64.0, R * 0.9), self.p["bg"], seed=seed)
        pc.release(t, pt, d, force, R, seed=seed)
        self.chips(pt[0], pt[1], t, 8, d, force * 0.3)

    def scuff(self, pc, t, pt, reach, count=3, seed=1):
        """A glancing blow: cracks and a few chips, nothing breaks off."""
        if pc.broken_at is None and reach > 6:
            pc.crack(t, pt, count, reach, self.p["bg"], width=1.4, seed=seed)
            self.chips(pt[0], pt[1], t, 2 + count, (0.0, -1.0), 90.0)

    def kick_letter(self, pc, t, dy=-9.0, rot=5.0):
        """A shock lifts the letter and drops it back, a little crooked then straight."""
        pc.tr.hold(t)
        x0, y0 = pc.tr.v
        pc.rot.hold(t)
        pc.tr.to(t + 0.07, (x0, y0 + dy), "out")
        pc.tr.to(t + 0.2, (x0, y0), "in")
        pc.rot.to(t + 0.07, rot, "out")
        pc.rot.to(t + 0.2, -rot * 0.4, "inout")
        pc.rot.to(t + 0.32, 0.0, "inout")

    def charge(self, x, y, t0, t1, colour):
        """Anticipation: rings that pulse inward while a heavy blow is being wound up."""
        for r, ph in ((16, 0.0), (8, 0.12)):
            sc, op = Track(1.0), Track(0)
            t = t0 + ph
            op.snap(t, 0.7)
            k = 0
            while t < t1:
                sc.to(t, 1.0 if k % 2 == 0 else 0.4, "in")
                t += 0.12
                k += 1
            op.hold(t1)
            op.snap(t1 + 0.02, 0)
            self.layers["high"].append(f'<g transform="translate({n(x)} {n(y)})">' + op_open(op) + tf_open("scale", sc, fsc1)
                                       + f'<circle r="{r}" fill="none" stroke="{colour}" stroke-width="1.8"/></g></g></g>')

    def sword_prop(self, tr, rot, op):
        p = self.p
        body = (f'<g transform="scale({S})"><polygon points="4,-1.6 30,-0.5 34,0 30,0.5 4,1.6" fill="{p["steel"]}" stroke="{p["fg"]}" stroke-width="0.7" stroke-linejoin="round"/>'
                f'<path d="M4,-4.4V4.4M-6,0H4" stroke="{p["fg"]}" stroke-width="1.7" stroke-linecap="round"/></g>')
        return op_open(op) + tf_open("translate", tr, fxy) + tf_open("rotate", rot, lambda a: n(a)) + body + "</g></g></g>"

    # --- props
    def poster_inner(self, cx, top):
        """A bounty poster: torn parchment, framed portrait, name, reward. Sized 140 x 172."""
        p = self.p
        w, h = 140, 172
        x0, x1, ink, edge = cx - w / 2, cx + w / 2, p["ink"], p["paper_edge"]
        # torn outline: slightly wavy sides, a ragged bottom
        outline = [(x0 + 1.5 * (rnd(i) - 0.5), top + h * i / 8) for i in range(9)]
        outline += [(x0 + w * i / 14, top + h + (4 if i % 2 else -2) * (0.5 + rnd(i + 20)) + 2) for i in range(1, 14)]
        outline += [(x1 + 1.5 * (rnd(i + 40) - 0.5), top + h * (8 - i) / 8) for i in range(9)]
        sh = pts([(x + 3, y + 4) for x, y in outline])
        out = [f'<polygon points="{sh}" fill="{p["fg"]}" opacity="0.16"/>',
               f'<polygon points="{pts(outline)}" fill="{p["paper"]}" stroke="{edge}" stroke-width="1.2" stroke-linejoin="round"/>',
               f'<path d="M{n(x0 + 3)},{n(top + h / 2)}H{n(x1 - 3)}M{n(cx)},{n(top + 3)}V{n(top + h - 4)}" stroke="{edge}" stroke-width="0.6" opacity="0.3"/>',
               f'<rect x="{n(x0 + 7)}" y="{n(top + 7)}" width="{w - 14}" height="{h - 17}" fill="none" stroke="{ink}" stroke-width="1.6"/>',
               f'<rect x="{n(x0 + 10)}" y="{n(top + 10)}" width="{w - 20}" height="{h - 23}" fill="none" stroke="{ink}" stroke-width="0.6"/>']

        def text(txt, y, size, bold, width, spacing=False):
            tw = min(text_w(txt, size, bold) + (len(txt) * 1.6 if spacing else 0), width)
            return (f'<text x="{n(cx - tw / 2)}" y="{n(y)}" font-size="{size}" font-weight="{700 if bold else 400}" fill="{ink}" '
                    f'textLength="{n(tw)}" lengthAdjust="spacing">{html.escape(txt)}</text>')

        def star(sx, sy, r):
            return pts([(sx + (r if k % 2 == 0 else r * 0.42) * math.sin(k * math.pi / 5), sy - (r if k % 2 == 0 else r * 0.42) * math.cos(k * math.pi / 5)) for k in range(10)])
        out.append(text("BY ORDER OF THE NAVY", top + 23, 6.5, False, 108, True))
        out.append(text(POSTER_HEAD, top + 46, 25, True, 108))
        out.append(f'<path d="M{n(x0 + 16)},{n(top + 52)}H{n(x1 - 16)}" stroke="{ink}" stroke-width="1.2"/>')
        # portrait: hatched backdrop, framed
        fx0, fy0, fx1, fy1 = cx - 46, top + 58, cx + 46, top + 116
        out.append(f'<rect x="{n(fx0)}" y="{n(fy0)}" width="{n(fx1 - fx0)}" height="{n(fy1 - fy0)}" fill="{edge}" fill-opacity="0.2"/>')
        hatch = ""
        for c_ in range(int(fx0 + fy0 - fy1) , int(fx1 + fy1 - fy0), 7):          # diagonal lines x - y = const, cut to the frame
            xa, ya = max(fx0, c_ + fy0), None
            lo, hi = max(fx0, c_ + fy0), min(fx1, c_ + fy1)
            if lo < hi:
                hatch += f"M{n(lo)},{n(lo - c_)}L{n(hi)},{n(hi - c_)}"
        out.append(f'<path d="{hatch}" stroke="{edge}" stroke-width="0.7" opacity="0.5"/>')
        hx, hy, sc_ = cx, top + 90, 2.3
        rel = lambda r: pts([(hx + x * sc_, hy + y * sc_ - 2) for x, y in r])
        out.append(f'<path d="M{n(hx - 30)},{n(fy1)}Q{n(hx - 28)},{n(hy + 14)} {n(hx)},{n(hy + 14)}Q{n(hx + 28)},{n(hy + 14)} {n(hx + 30)},{n(fy1)}Z" fill="{ink}" opacity="0.88"/>')
        out.append(f'<circle cx="{n(hx)}" cy="{n(hy)}" r="12" fill="{p["paper"]}" stroke="{ink}" stroke-width="1.8"/>')
        out.append(f'<polygon points="{rel(HATS["tricorn"])}" fill="{ink}"/>')
        out.append(f'<polyline points="{rel(STRAP)}" fill="none" stroke="{ink}" stroke-width="1.2"/>')
        out.append(f'<polyline points="{rel(PATCH)}" fill="none" stroke="{ink}" stroke-width="4" stroke-linecap="round"/>')
        out.append(f'<circle cx="{n(hx + 4.5)}" cy="{n(hy - 2)}" r="1.4" fill="{ink}"/>'
                   f'<path d="M{n(hx - 4)},{n(hy + 5)}q5,3.5 9,-1.5" fill="none" stroke="{ink}" stroke-width="1.3" stroke-linecap="round"/>')
        out.append(f'<rect x="{n(fx0)}" y="{n(fy0)}" width="{n(fx1 - fx0)}" height="{n(fy1 - fy0)}" fill="none" stroke="{ink}" stroke-width="1.8"/>')
        # name, line, reward
        out.append(text(POSTER_NAME, top + 138, 19, True, 104, True))
        out.append(f'<path d="M{n(x0 + 16)},{n(top + 143)}H{n(x1 - 16)}M{n(x0 + 16)},{n(top + 145)}H{n(x1 - 16)}" stroke="{ink}" stroke-width="0.7"/>')
        out.append(text(POSTER_SUB, top + 155, 8, False, 108))
        label, _, value = POSTER_REWARD.partition(":")
        out.append(text(label.strip().upper() + ":" + value.upper(), top + 166, 8, True, 100))
        for sx in (x0 + 16, x1 - 16):
            out.append(f'<polygon points="{star(sx, top + 163, 4.5)}" fill="{ink}"/>')
        return "".join(out)

    def cannon_svg(self, cx, op, sc, recoil, glow):
        p = self.p
        c, f = p["cannon"], p["fg"]
        body = (f'<polygon points="-48,-30 -40,-30 24,-27 24,-12 -40,-9 -48,-9" fill="{c}" stroke="{f}" stroke-width="1"/>'
                f'<rect x="-52" y="-32" width="7" height="25" rx="2" fill="{c}" stroke="{f}" stroke-width="1"/>'
                f'<circle cx="0" cy="-9" r="9" fill="none" stroke="{f}" stroke-width="1.8"/>'
                f'<path d="M-9,-9H9M0,-18V0M-6.4,-15.4L6.4,-2.6M6.4,-15.4L-6.4,-2.6" stroke="{f}" stroke-width="0.8"/>'
                f'<path d="M24,-27 q4,-7 11,-9" fill="none" stroke="{f}" stroke-width="1.4" stroke-linecap="round"/>'
                f'<circle cx="35" cy="-36" r="3" fill="{p["spark"]}" opacity="0">' + anim("opacity", glow, f2) + "</circle>")
        return (f'<g transform="translate({n(cx)} {FLOOR}) scale(1.4)">' + op_open(op) + tf_open("translate", recoil, fxy)
                + tf_open("scale", sc, fsc) + body + "</g></g></g></g>")

    def wave(self, t0, v=700.0, body=1500):
        p = self.p
        F0, F1 = -140.0, W + body + 40.0
        t1 = t0 + (F1 - F0) / v
        xs = Track((F0, 0.0))
        xs.hold(t0)
        xs.to(t1, (F1, 0.0))
        bob = Track((0.0, 0.0))
        bob.hold(t0)
        t, i = t0, 0
        while t < t1:
            t += 0.18
            i += 1
            bob.to(t, (0.0, 5 * math.sin(i * 1.7)), "inout")
        bob.to(t1 + 0.2, (0.0, 0.0))
        front = lambda y: 24 * math.sin(y * 0.05 + 0.8) + 8 * math.sin(y * 0.14 + 2)
        ys = list(range(-60, H + 61, 6))
        fpts = [(front(y), y) for y in ys]
        d = f"M{-body},-60 " + " ".join(f"L{n(x)},{y}" for x, y in fpts) + f" L{-body},{H + 60} Z"
        surf = pts(fpts)
        swells = "".join(f'<polyline points="{pts([(x - off, y) for x, y in fpts])}" fill="none" stroke="{p["water_b"]}" stroke-width="{w_}" opacity="{o}"/>'
                         for off, w_, o in ((60, 5, 0.55), (150, 4, 0.4), (290, 6, 0.3)))
        foam = "".join(f'<circle cx="{n(front(y) + 5 * rnd(y))}" cy="{y}" r="{n(3 + 4 * rnd(y + 1))}" fill="{p["foam"]}" opacity="0.9"/>' for y in ys[::2])
        self.defs += (f'<linearGradient id="waterg" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="{p["water_a"]}"/>'
                      f'<stop offset="0.82" stop-color="{p["water_a"]}"/><stop offset="1" stop-color="{p["water_b"]}"/></linearGradient>')
        return (tf_open("translate", xs, fxy) + tf_open("translate", bob, fxy)
                + f'<path d="{d}" fill="url(#waterg)"/>' + swells
                + f'<polyline points="{surf}" fill="none" stroke="{p["foam"]}" stroke-width="7" stroke-linejoin="round" opacity="0.95"/>'
                + foam + "</g></g>"), t0, v, F0

    # --- the story
    def story(self):
        p = self.p
        pir = self.pir = Char("hang", (900, 100), -1)
        off = self.off = Char("stand", (-80, 200), 1)
        PY = Y0                                    # letter tops are the platform
        LA, LN, LS, LI, LL = self.letters
        XA, XN, XS, XI, XL = (pc.cx for pc in self.letters)
        HG = 42 * S                                # hang pose: hands are this far above the feet
        head = lambda c, t: (c.pos.val(t)[0], c.pos.val(t)[1] - 36 * S)

        # ---- 0.7  a distant boom, the banner shivers
        self.jolt(0.7, 1.6)
        for pc in self.letters:
            pc.shake(0.7, 1.05, 0.9)

        # ---- 1.0  the pirate swings in on a rope and flips onto the L
        AX, AY, ROPE, TH0, TH1, TS0, TS1 = 560.0, -8.0, 170.0, -60.0, 35.0, 1.0, 1.95
        hand = lambda th: (AX - ROPE * math.sin(math.radians(th)), AY + ROPE * math.cos(math.radians(th)))
        hx, hy = hand(TH0)
        pir.pos = Track((hx, hy + HG))
        pir.rot = Track((TH0, 0.0, -HG))
        rx, ry, rop = Track(hx), Track(hy), Track(0)
        for tr in (pir.pos, pir.rot, rx, ry):
            tr.hold(TS0)
        rop.snap(TS0, 1)
        pir.show(TS0)
        steps = 36
        for i in range(1, steps + 1):
            s = i / steps
            th = TH0 + (TH1 - TH0) * (0.5 - 0.5 * math.cos(math.pi * s))
            hx, hy = hand(th)
            t = TS0 + (TS1 - TS0) * s
            pir.pos.to(t, (hx, hy + HG))
            pir.rot.to(t, (th, 0.0, -HG))
            rx.to(t, hx)
            ry.to(t, hy)
        for i in range(1, 14):                     # the rope keeps swinging without him
            s = i / 13
            hx, hy = hand(TH1 + 30 * math.sin(s * math.pi / 2))
            rx.to(TS1 + 0.5 * s, hx)
            ry.to(TS1 + 0.5 * s, hy)
        rop.snap(TS1 + 0.55, 0)
        self.layers["props"].append(
            f'<circle cx="{AX}" cy="{AY}" r="5" fill="{p["fg"]}"/>'
            f'<line x1="{n(AX)}" y1="{n(AY)}" x2="{n(rx.k[0][1])}" y2="{n(ry.k[0][1])}" stroke="{p["fg"]}" stroke-width="1.4" opacity="0">'
            + anim("x2", rx, n) + anim("y2", ry, n) + anim("opacity", rop, f2) + "</line>")
        pir.pose(TS1, "tuck", 0.1)
        pir.rot.to(TS1 + 0.1, (0.0, 0.0, -HG), "out")
        pir.jump(TS1, 2.3, XL, PY, 46)
        pir.spin(TS1 + 0.11, 2.2, -360)
        pir.pose(2.2, "fall", 0.08)
        pir.land(2.3, 0.28)
        self.dust(XL, PY, 2.3, big=True)
        self.dip(LL, 2.3, 6)
        self.jolt(2.3, 1.6)
        pir.face(2.4, 1)

        # ---- 2.6  dagger throw pins the bounty poster
        PX, PTOP = 655.0, 58.0
        pir.pose(2.55, "crouch", 0.1)
        pir.pose(2.68, "wind_throw", 0.1)
        pir.pose(2.76, "throw", 0.05, "snap")
        dx0, dy0 = pir.world(2.76, "RH")
        pin = (PX, PTOP + 4)
        ang = math.degrees(math.atan2(pin[1] - dy0, pin[0] - dx0))
        dg_tr, dg_op = Track((dx0, dy0)), Track(0)
        dg_tr.hold(2.76)
        dg_op.snap(2.76, 1)
        dg_tr.to(3.0, pin, "in")
        self.speed(dx0, dy0 + 6, 1, 2.8, 0.2, 3, 90)
        poster = Piece(self.poster_inner(PX, PTOP), PX, PTOP + 86, pivot=(PX, PTOP + 4))
        poster.op = Track(0)
        poster.op.snap(3.0, 1)
        poster.sc = Track(0.25)
        poster.sc.hold(3.0)
        for t, v, e in ((3.08, 1.12, "out"), (3.18, 0.97, "inout"), (3.26, 1.0, "inout")):
            poster.sc.to(t, v, e)
        poster.rot.hold(3.0)
        for t, v in ((3.12, 7), (3.4, -5), (3.7, 3), (4.0, -1.5), (4.3, 0)):
            poster.rot.to(t, float(v), "inout")
        self.pieces.append(poster)
        self.burst(PX, PTOP + 4, 3.0, 14)
        self.jolt(3.0, 1.6)
        pir.pose(3.15, "stand", 0.1)
        pir.pose(3.3, "cheer", 0.08)
        pir.jump(3.4, 3.72, XL, PY, 16)
        pir.land(3.72, 0.2, "cheer")
        self.dip(LL, 3.72, 3)

        # ---- 3.75  the officer leaps in from off the page, flipping, and lands on the A
        off.show(3.7)
        off.pose(3.7, "crouch", 0.01)
        off.takeoff(3.78, 0.2)
        off.jump(3.82, 4.55, XA, PY, 110)
        off.pose(3.88, "tuck", 0.08)
        off.spin(3.9, 4.45, 360)
        off.pose(4.45, "fall", 0.08)
        self.speed(30, 190, 1, 3.9, 0.3, 5, 90)
        off.land(4.55, 0.3)
        self.dust(XA, PY, 4.55, big=True)
        self.dip(LA, 4.55, 6)
        self.jolt(4.55, 1.8)
        self.mark("!", XL, PY - 50, 4.1)
        pir.pose(4.1, "guard", 0.1)
        pir.pose(4.6, "taunt", 0.12)
        off.pose(4.85, "stand", 0.1)
        off.weapon(4.95, True)
        off.pose(4.95, "guard", 0.1)
        self.spark(*off.world(5.0, "WT"), 5.0, 7)

        # ---- 5.1  the officer's low air-slash skims the letters; the pirate hops over it
        off.pose(5.1, "sw_wind", 0.18, "inout")
        off.pose(5.32, "sw_cut", 0.05, "snap")
        off.pose(5.4, "sw_thru", 0.06)
        off.pose(5.85, "guard", 0.25, "inout")
        self.swoosh(off, 5.2, 5.34, p["navy"], 0.5)
        SLY = PY - 12                                       # slash height
        route = [(XA + 48.0, SLY), (480.0, SLY), (PX, PTOP + 86.0)]
        speed_ = 680.0
        t = 5.34
        c_tr, c_rot, c_op, c_sc = Track(route[0]), Track(0.0), Track(0), Track(1.0)
        c_tr.hold(t)
        c_op.snap(t, 1)
        times = []
        for i in range(2):
            (x0_, y0_), (x1_, y1_) = route[i], route[i + 1]
            c_rot.snap(t, math.degrees(math.atan2(y1_ - y0_, x1_ - x0_)))
            t += math.hypot(x1_ - x0_, y1_ - y0_) / speed_
            c_tr.to(t, route[i + 1])
            times.append(t)
        c_op.snap(t, 0)
        self.layers["high"].append(
            op_open(c_op) + tf_open("translate", c_tr, fxy) + tf_open("rotate", c_rot, lambda a: n(a))
            + f'<g transform="scale(1.7)"><path d="M-6,-13 Q11,0 -6,13 Q4,0 -6,-13Z" fill="{p["navy"]}" stroke="{p["bg"]}" stroke-width="0.8" stroke-linejoin="round"/></g></g></g></g>')
        t_cross = 5.34 + (XL - route[0][0]) / speed_          # the slash reaches the pirate
        pir.pose(t_cross - 0.42, "crouch", 0.1)
        pir.jump(t_cross - 0.2, t_cross + 0.2, XL, PY, 44)
        pir.pose(t_cross - 0.12, "tuck", 0.08)
        pir.land(t_cross + 0.2, 0.2, "crouch")
        self.mark("?", XL, PY - 50, t_cross + 0.3)
        t_post = times[1]
        poster.slice(t_post, 62, fall=((-70, 26), (58, -30)), land_y=FLOOR - 4, dur=1.0, fade=0.7, paper=True)
        self.burst(PX, PTOP + 86, t_post, 18)
        self.flash(t_post, 0.06, 0.4)
        self.jolt(t_post, 2)
        dg_tr.snap(t_post, pin)
        dg_tr.to(t_post + 0.4, (PX - 6, FLOOR - 3), "in")

        # ---- 6.2  pirate draws, officer runs the tops of the letters, each one dipping under his foot
        pir.pose(6.1, "stand", 0.1)
        pir.weapon(6.3, True)
        pir.pose(6.3, "guard", 0.1)
        self.spark(*pir.world(6.35, "WT"), 6.35, 7)
        pir.face(6.4, -1)
        off.run(6.1, 7.0, 292, armed_=True)
        t_n = 6.1 + (XN - XA) / (292 - XA) * 0.9
        t_s = 6.1 + (XS - XA) / (292 - XA) * 0.9
        self.dip(LN, t_n, 4)
        self.dip(LS, t_s - 0.05, 4)
        self.speed(XA + 20, PY, 1, 6.12, 0.2, 3, 60)
        pir.run(6.6, 7.0, 358, armed_=True)
        self.dip(LI, 7.0, 4)
        off.pose(7.02, "guard", 0.08)
        pir.pose(7.02, "guard", 0.08)

        # ---- 7.1  three clashes on top of the banner
        for c in (off, pir):
            c.pose(7.12, "sw_wind", 0.1, "inout")
            c.pose(7.27, "sw_cut", 0.05, "snap")
        self.swoosh(off, 7.17, 7.29, p["navy"], 0.5)
        self.swoosh(pir, 7.17, 7.29, p["pirate"], 0.5)
        e1 = self.hit(7.3, 325, PY - 26, 12, pir, off, dur=0.08, shake=2)
        self.burst(325, PY - 26, 7.3, 15)
        off.pose(e1 + 0.15, "guard", 0.15)
        pir.pose(e1 + 0.15, "guard", 0.15)
        off.pose(7.6, "wind_hi", 0.12, "inout")
        pir.pose(7.66, "block", 0.08)
        off.pose(7.72, "chop", 0.05, "snap")
        self.swoosh(off, 7.64, 7.74, p["navy"], 0.5)
        e2 = self.hit(7.75, 325, PY - 40, 12, pir, off, dur=0.07, shake=2)
        self.burst(325, PY - 40, 7.75, 14)
        pir.at(7.9, 364, PY, "out")
        off.at(7.9, 286, PY, "out")
        self.dip(LS, 7.8, 3)
        off.pose(e2 + 0.1, "block", 0.1)
        pir.pose(e2 + 0.1, "sw_wind", 0.12, "inout")
        pir.pose(8.05, "sw_cut", 0.05, "snap")
        self.swoosh(pir, 7.98, 8.07, p["pirate"], 0.5)
        e3 = self.hit(8.08, 326, PY - 30, 11, pir, off, dur=0.07)
        for c in (off, pir):
            c.pose(8.35, "sw_wind", 0.14, "inout")
            c.pose(8.5, "sw_cut", 0.05, "snap")
        self.swoosh(off, 8.4, 8.52, p["navy"], 0.5)
        self.swoosh(pir, 8.4, 8.52, p["pirate"], 0.5)
        e4 = self.hit(8.53, 325, PY - 28, 16, pir, off, dur=0.11, shake=3.5, big=True)
        for k, pc in enumerate(self.letters):                # the shock cracks each letter in proportion to its distance
            dist = abs(pc.cx - 325)
            x0_, _, x1_, _ = pc.bbox
            self.scuff(pc, 8.55 + dist / 900, (min(max(325.0, x0_ + 6), x1_ - 6), PY + 1.0), 70 * math.exp(-dist / 170),
                       4 if dist < 120 else 2, seed=3 + k)

        # ---- 8.8  pirate's low spin; the officer flips over it and lands behind him on the L
        pir.pose(8.85, "crouch", 0.1)
        pir.pose(8.98, "sw_cut", 0.06, "snap")
        pir.spin(8.98, 9.28, 360, "lin")
        off.pose(8.85, "crouch", 0.1)
        off.takeoff(8.98, 0.15)
        off.jump(9.05, 9.55, XL + 6, PY, 62)
        off.pose(9.1, "tuck", 0.08)
        off.spin(9.1, 9.5, 360)
        off.pose(9.5, "fall", 0.06)
        off.face(9.3, -1)
        self.trail(pir, 9.0, 9.24, p["pirate"], 4, 0.35)
        self.trail(off, 9.12, 9.42, p["navy"], 4)
        off.land(9.55, 0.24)
        self.dust(XL, PY, 9.55)
        self.dip(LL, 9.55, 5)
        pir.pose(9.4, "guard", 0.12)
        pir.face(9.5, 1)
        self.mark("?", pir.pos.val(9.6)[0], PY - 50, 9.6)

        # ---- 9.9  wind-up (rings, tremble), then the chop that cuts the I out from under the pirate
        off.pose(9.85, "wind_hi", 0.2, "inout")
        off.at(10.15, 392, PY, "inout")
        self.charge(*off.world(10.3, "WT"), 9.95, 10.5, p["navy"])
        off.jitter(10.2, 10.5, 0.7)
        self.jolt(10.2, 0.8)
        off.pose(10.55, "chop", 0.05, "snap")
        self.swoosh(off, 10.5, 10.6, p["navy"], 0.6)
        T_CUT = 10.6
        LI.slice(T_CUT, 90, fall=((-40, 75), (44, -70)), land_y=FLOOR - 7, dur=0.45, fade=0.5)
        self.burst(XI, PY + 20, T_CUT, 16)
        self.flash(T_CUT, 0.06, 0.4)
        self.jolt(T_CUT, 2.4)
        pir.pose(T_CUT, "fall", 0.05)
        pir.weapon(T_CUT + 0.05, False)
        self.mark("!", pir.pos.val(T_CUT)[0], PY - 50, T_CUT + 0.04)
        pir.drop(T_CUT + 0.1, T_CUT + 0.42, 340, FLOOR)
        pir.rot.snap(T_CUT + 0.1, (0.0, 0.0, PIV))
        pir.rot.to(T_CUT + 0.42, (-200.0, 0.0, PIV), "in")
        pir.rot.snap(T_CUT + 0.43, (0.0, 0.0, PIV))
        pir.land(T_CUT + 0.43, 0.32, "crouch")
        self.dust(340, FLOOR, T_CUT + 0.43, big=True)
        self.shock(340, FLOOR, T_CUT + 0.43, 80)
        self.jolt(T_CUT + 0.43, 2.2)

        # ---- 11.2  the officer drops after him and stabs the floor where he stood; the pirate rolls clear
        T_STAB = 11.2
        off.pose(10.78, "chop", 0.1)
        off.drop(10.8, T_STAB, 392, FLOOR)
        off.land(T_STAB, 0.3, "chop")
        off.weapon(T_STAB, False)
        HILT = (378.5, FLOOR - 26.0)
        sw_tr, sw_rot, sw_op = Track(HILT), Track(138.0), Track(0)
        sw_op.snap(T_STAB, 1)
        self.burst(340, FLOOR - 8, T_STAB, 15, big=True)
        self.dust(345, FLOOR, T_STAB, big=True)
        self.jolt(T_STAB, 3)
        pir.pose(T_CUT + 0.46, "roll", 0.04)
        pir.spin(T_CUT + 0.47, 11.55, 720, "lin")
        pir.pos.hold(T_CUT + 0.47)
        pir.pos.to(11.55, (480.0, float(FLOOR)), "inout")
        self.trail(pir, 11.1, 11.5, p["pirate"], 4)
        self.speed(380, FLOOR, 1, 11.2, 0.2, 3, 60)
        # officer tugs at the stuck sword: he strains, the blade wobbles but will not come
        off.pose(11.5, "pull", 0.12)
        off.jitter(11.6, 12.1, 1.3)
        for i in range(8):
            sw_rot.to(11.6 + 0.07 * i, 138.0 + (4 if i % 2 == 0 else -4), "inout")
        sw_rot.to(12.2, 138.0, "inout")
        self.mark("?", off.pos.val(11.7)[0], FLOOR - 62, 11.8)

        # ---- 12.1  the pirate comes back and kicks him in the back from across the floor
        pir.face(11.7, -1)
        pir.pose(11.75, "taunt", 0.1)
        pir.run(11.95, 12.22, 440, frame=0.055)
        pir.pose(12.24, "crouch", 0.06)
        pir.jump(12.28, 12.58, 404, FLOOR, 24)
        pir.pose(12.32, "kick", 0.08)
        pir.pose(12.7, "kick", 0.02)
        T_KICK = 12.58
        off.pose(T_KICK - 0.01, "hit", 0.02)
        e = self.hit(T_KICK, 378, FLOOR - 32, 17, pir, off, dur=0.12, shake=4, big=True)
        pir.land(e + 0.12, 0.24, "crouch")
        self.dust(404, FLOOR, e + 0.12)
        # launched left, nose first, and into the underside of the A
        off.pose(e + 0.01, "fly", 0.03, "snap")
        off.rot.snap(e + 0.01, (0.0, 0.0, PIV))
        off.rot.to(e + 0.2, (-78.0, 0.0, PIV), "out")
        off.jump(e + 0.01, e + 0.62, 92, 224, 60)
        self.speed(380, FLOOR - 10, -1, e + 0.02, 0.3, 4, 90)
        self.trail(off, e + 0.1, e + 0.5, p["navy"], 4)
        t_a = e + 0.62
        self.burst(92, 214, t_a, 17, big=True)
        self.smash(LA, t_a, (96.0, Y0 + 6 * CH - 4), (-0.7, -0.7), 380.0, 60.0, lead=0.05, seed=4)   # the A takes the officer in the underside
        self.jolt(t_a, 3)
        off.hitstop(t_a, 0.08)
        off.drop(t_a + 0.1, t_a + 0.45, 74, FLOOR)
        off.rot.snap(t_a + 0.1, (-78.0, 0.0, PIV))
        off.rot.to(t_a + 0.45, (-170.0, 0.0, PIV), "in")
        off.rot.snap(t_a + 0.46, (0.0, 0.0, PIV))
        off.land(t_a + 0.46, 0.3, "lying")
        self.dust(74, FLOOR, t_a + 0.46, big=True)
        self.shock(74, FLOOR, t_a + 0.46, 70)
        self.jolt(t_a + 0.46, 2)
        T_DOWN = t_a + 0.46                      # ~13.7

        # pirate gloats and re-draws; the officer lies there
        pir.pose(T_DOWN - 0.5, "cheer", 0.1)
        pir.jump(T_DOWN - 0.3, T_DOWN, 404, FLOOR, 14)
        pir.land(T_DOWN, 0.2, "cheer")
        pir.pose(T_DOWN + 0.5, "taunt", 0.12)
        pir.at(T_DOWN + 1.0, 450.0, FLOOR, "inout")
        pir.weapon(14.9, True)
        pir.pose(14.9, "guard", 0.1)
        self.spark(*pir.world(14.95, "WT"), 14.95, 7)
        off.pose(14.4, "crouch", 0.25, "inout")
        off.face(14.55, 1)
        off.pose(14.6, "stand", 0.1)
        off.pose(14.7, "guard", 0.08)
        off.jitter(14.75, 15.0, 0.9)
        self.mark("!", 74, FLOOR - 62, 14.78)

        # ---- 15.0  he dashes back for the sword and yanks it out
        off.run(15.0, 15.45, 364, frame=0.05)
        self.speed(150, FLOOR, 1, 15.05, 0.3, 5, 100)
        self.dust(110, FLOOR, 15.05)
        off.pose(15.5, "pull", 0.06, "snap")
        off.land(15.5, 0.2, "pull")
        sw_rot.hold(15.5)
        sw_rot.to(15.58, 133.0)
        sw_rot.to(15.66, 143.0)
        sw_rot.to(15.74, 138.0)
        sw_op.snap(15.8, 0)
        off.weapon(15.8, True)
        off.pose(15.8, "guard", 0.1)
        off.at(15.8, 364.0, FLOOR)
        self.burst(*off.world(15.82, "WT"), 15.8, 12)
        self.jolt(15.8, 2)
        self.layers["mid"].append(lambda: self.sword_prop(sw_tr, sw_rot, sw_op))   # built late: the reset below edits sw_op

        # ---- 16.0  second duel: ghosts and smears, ending with the pirate disarmed
        for c in (off, pir):
            c.pose(15.95, "sw_wind", 0.1, "inout")
            c.pose(16.1, "sw_cut", 0.05, "snap")
        self.swoosh(off, 16.0, 16.12, p["navy"], 0.5)
        self.swoosh(pir, 16.0, 16.12, p["pirate"], 0.5)
        self.hit(16.12, 407, FLOOR - 36, 13, pir, off, dur=0.08, shake=2)
        self.burst(407, FLOOR - 36, 16.12, 15)
        off.pose(16.3, "wind_hi", 0.1, "inout")
        pir.pose(16.4, "block", 0.08)
        off.pose(16.46, "chop", 0.05, "snap")
        self.swoosh(off, 16.4, 16.48, p["navy"], 0.5)
        self.hit(16.49, 407, FLOOR - 44, 13, pir, off, dur=0.07, shake=2)
        self.burst(407, FLOOR - 44, 16.49, 15)
        pir.at(16.64, 458.0, FLOOR, "out")
        off.at(16.64, 374.0, FLOOR, "out")
        for c in (off, pir):
            c.pose(16.7, "sw_wind", 0.12, "inout")
            c.pose(16.82, "sw_cut", 0.05, "snap")
        self.swoosh(off, 16.74, 16.84, p["navy"], 0.5)
        self.swoosh(pir, 16.74, 16.84, p["pirate"], 0.5)
        self.trail(off, 16.72, 16.84, p["navy"], 3, 0.3)
        sx0, sy0 = pir.world(16.84, "RH")
        e5 = self.hit(16.85, 416, FLOOR - 40, 17, pir, off, dur=0.11, shake=4, big=True)
        pir.weapon(e5, False)
        pir.pose(e5 + 0.02, "hit", 0.04, "snap")
        off.pose(e5 + 0.04, "sw_thru", 0.06)
        self.mark("!", pir.pos.val(e5)[0], FLOOR - 62, e5 + 0.08)
        # the pirate's sword spins away and sticks in the floor
        f_tr, f_rot, f_op = Track((sx0, sy0)), Track(0.0), Track(0)
        f_op.snap(e5, 1)
        f_tr.hold(e5)
        f_rot.hold(e5)
        FX_, FT = 500.0, 0.7
        for i in range(1, 15):
            s_ = i / 14
            f_tr.to(e5 + FT * s_, (sx0 + (FX_ - sx0) * s_, sy0 + (FLOOR - 40 - sy0) * s_ - 4 * 150 * s_ * (1 - s_)))
            f_rot.to(e5 + FT * s_, 1080.0 * s_ + 80.0 * s_)
        t_stick = e5 + FT
        for i in range(8):
            f_rot.to(t_stick + 0.06 * (i + 1), 1160.0 + (6 if i % 2 == 0 else -6) * (1 - i / 8), "inout")
        f_rot.to(t_stick + 0.6, 1160.0)
        self.layers["mid"].append(lambda: self.sword_prop(f_tr, f_rot, f_op))
        self.burst(FX_, FLOOR - 4, t_stick, 11)
        self.jolt(t_stick, 1.2)

        # ---- 17.2  the pirate runs for it; a cannon pops out of the floor ahead of him
        pir.face(17.15, 1)
        pir.pose(17.1, "stand", 0.08)
        pir.run(17.2, 17.85, 600, frame=0.055)
        self.speed(470, FLOOR, 1, 17.25, 0.3, 4, 90)
        off.pose(17.1, "guard", 0.2)
        off.weapon(17.0, True)
        off.run(17.35, 18.3, 545, armed_=True, frame=0.055)
        self.speed(380, FLOOR, 1, 17.4, 0.3, 4, 90)
        CX = 690.0
        cop, csc, crec, cglow = Track(0), Track((0.1, 0.1)), Track((0.0, 0.0)), Track(0)
        cop.snap(17.5, 1)
        csc.hold(17.5)
        csc.to(17.6, (1.12, 0.9), "out")
        csc.to(17.7, (0.96, 1.04), "inout")
        csc.to(17.8, (1.0, 1.0), "inout")
        self.dust(CX, FLOOR, 17.52, big=True)
        self.shock(CX, FLOOR, 17.52, 70)
        T_BOOM = 19.1
        crec.hold(T_BOOM)
        crec.to(T_BOOM + 0.04, (10.0, 0.0), "out")
        crec.to(T_BOOM + 0.4, (0.0, 0.0), "inout")
        for i in range(10):                        # the fuse sputters
            cglow.snap(18.62 + 0.045 * i, 1 if i % 2 == 0 else 0.3)
        cglow.snap(T_BOOM, 0)
        self.layers["mid"].append(lambda: self.cannon_svg(CX, cop, csc, crec, cglow))
        # the pirate hops over it and turns to light the fuse
        pir.pose(17.9, "crouch", 0.08)
        pir.takeoff(17.96, 0.2)
        pir.jump(18.0, 18.5, 748, FLOOR, 62)
        pir.pose(18.06, "tuck", 0.08)
        pir.spin(18.1, 18.45, -360)
        pir.pose(18.42, "fall", 0.05)
        pir.face(18.45, -1)
        pir.land(18.5, 0.24)
        self.dust(748, FLOOR, 18.5)
        pir.pose(18.62, "light", 0.08)
        for i in range(4):
            self.spark(CX + 49, FLOOR - 50, 18.64 + 0.09 * i, 6, 0.18)
        # the officer sees it
        off.pose(18.32, "stand", 0.06)
        self.dust(545, FLOOR, 18.32)
        self.mark("!", 545, FLOOR - 62, 18.4)
        off.pose(18.8, "block", 0.12)

        # ---- 19.1  BOOM: he is launched across the whole page, through every letter
        self.jolt(T_BOOM, 5)
        self.flash(T_BOOM, 0.09, 0.7)
        self.smoke(CX - 60, FLOOR - 30, T_BOOM)
        self.spark(CX - 64, FLOOR - 30, T_BOOM, 20)
        ball_tr, ball_op = Track((CX - 70.0, FLOOR - 30.0)), Track(0)
        ball_tr.hold(T_BOOM)
        ball_op.snap(T_BOOM, 1)
        ball_tr.to(T_BOOM + 0.07, (550.0, FLOOR - 34.0))
        ball_op.snap(T_BOOM + 0.07, 0)
        self.layers["high"].append(op_open(ball_op) + tf_open("translate", ball_tr, fxy)
                                   + f'<circle r="6" fill="{p["cannon"]}" stroke="{p["fg"]}" stroke-width="1"/></g></g>')
        h_end = self.hit(T_BOOM + 0.07, 550, FLOOR - 34, 18, off, dur=0.1, shake=3.5, big=True)
        off.weapon(h_end, False)
        off.pose(h_end + 0.02, "fly", 0.04, "snap")
        t0_, dur_ = h_end + 0.02, 1.4
        off.jump(t0_, t0_ + dur_, -90, 120, 110)
        off.rot.snap(t0_, (0.0, 0.0, PIV))
        off.rot.to(t0_ + dur_, (-1080.0, 0.0, PIV))
        off.hide(t0_ + dur_ + 0.05)
        self.trail(off, t0_ + 0.1, t0_ + 0.5, p["navy"], 4)
        for pc in (LL, LS, LN, LA):                      # he plows through each letter on the way
            s_ = (545 - pc.cx) / 635
            ty = FLOOR + (120 - FLOOR) * s_ - 4 * 110 * s_ * (1 - s_)
            tt = t0_ + dur_ * s_
            self.smash(pc, tt, (pc.cx + 22, ty), (-1.0, -0.45), 470.0, 70.0 if pc is LA else 56.0, lead=0.05, seed=7 + int(pc.cx))
            self.burst(pc.cx + 22, ty, tt, 16)
            self.jolt(tt, 1.6)
        # the pirate celebrates
        pir.pose(19.45, "cheer", 0.1)
        pir.jump(19.6, 19.9, 748, FLOOR, 18)
        pir.land(19.9, 0.2, "cheer")
        pir.jump(20.15, 20.45, 748, FLOOR, 18)
        pir.land(20.45, 0.2, "cheer")

        # ================================================================ ACT 2: the navy answers
        # ---- 20.7  a horn from off-page. Six sailors pour in from the left.
        pir.pose(20.7, "stand", 0.15)
        self.mark("!", 748, FLOOR - 62, 21.0)
        NS = 6
        XS_ = [330.0 + 34 * i for i in range(NS)]                 # where the line forms
        XF_ = [430.0 + 27 * i for i in range(NS)]                 # where it charges to
        crew = self.crew = [Char("stand", (-70.0, float(FLOOR)), 1) for _ in range(NS)]
        for i, sl in enumerate(crew):
            t0_ = 21.0 + 0.09 * (NS - 1 - i)
            t1_ = t0_ + (XS_[i] + 70) / 430
            sl.show(t0_)
            sl.weapon(t0_, True)
            sl.run(t0_, t1_, XS_[i], armed_=True, frame=0.055)
            sl.pose(t1_ + 0.02, "guard", 0.08)
            self.dust(XS_[i] - 14, FLOOR, t1_)
        self.speed(40, FLOOR, 1, 21.1, 0.4, 5, 110)
        # the pirate shrugs, crouches by the cannon and lights the fuse again
        pir.pose(21.5, "taunt", 0.12)
        pir.pose(21.95, "crouch", 0.1)
        pir.pose(22.45, "light", 0.1)
        T_BOOM2 = 23.2
        for i in range(11):
            cglow.snap(22.5 + 0.055 * i, 1 if i % 2 == 0 else 0.3)
        cglow.snap(T_BOOM2, 0)
        for i in range(4):
            self.spark(CX + 49, FLOOR - 50, 22.55 + 0.12 * i, 6, 0.18)
        # ---- 22.55  they charge as one, see the fuse, and skid
        for i, sl in enumerate(crew):
            sl.run(22.55, 23.05, XF_[i], armed_=True, frame=0.055)
            sl.pose(23.07, "fall", 0.04)
        self.speed(430, FLOOR, 1, 22.6, 0.3, 4, 90)
        self.dust(XF_[-1], FLOOR, 23.05, big=True)
        self.mark("!", XF_[-1], FLOOR - 62, 23.04)
        # ---- 23.2  BOOM again: the ball bowls through the line, then bounces off every letter
        crec.hold(T_BOOM2)
        crec.to(T_BOOM2 + 0.04, (10.0, 0.0), "out")
        crec.to(T_BOOM2 + 0.4, (0.0, 0.0), "inout")
        self.jolt(T_BOOM2, 5)
        self.flash(T_BOOM2, 0.09, 0.6)
        self.smoke(CX - 60, FLOOR - 30, T_BOOM2)
        self.spark(CX - 64, FLOOR - 30, T_BOOM2, 20)
        b_tr, b_op = Track((CX - 70.0, FLOOR - 30.0)), Track(0)
        b_tr.hold(T_BOOM2)
        b_op.snap(T_BOOM2, 1)
        px_, th = CX - 70.0, T_BOOM2 + 0.07
        for k, i in enumerate(range(NS - 1, -1, -1)):
            xi = XF_[i]
            if k:
                b_tr.to(th - 0.05, ((px_ + xi) / 2, FLOOR - 92.0), "out")
            b_tr.to(th, (xi, FLOOR - 34.0), "in" if k else "lin")
            sl = crew[i]
            sl.pose(th, "fly", 0.02, "snap")
            sl.rot.snap(th, (0.0, 0.0, PIV))
            dx = (-150.0 if k % 2 else 130.0) * (1 + 0.15 * k)
            sl.jump(th, th + 0.8, xi + dx, -90.0, 70)
            sl.rot.to(th + 0.8, ((-1 if k % 2 else 1) * (540.0 + 180 * k), 0.0, PIV))
            sl.hide(th + 0.82)
            self.burst(xi, FLOOR - 34, th, 14 if k else 18, big=(k == 0))
            self.jolt(th, 2.0 if k == 0 else 1.2)
            if k < 2:
                self.trail(sl, th + 0.1, th + 0.45, p["navy"], 3, 0.3)
            px_, th = xi, th + 0.1
        for pc, y_ in ((LL, 150.0), (LS, 120.0), (LN, 140.0), (LA, 108.0)):    # then the banner
            b_tr.to(th - 0.05, ((px_ + pc.cx) / 2, y_ - 40.0), "out")
            b_tr.to(th, (pc.cx, y_), "in")
            self.burst(pc.cx, y_, th, 12)
            self.smash(pc, th, (pc.cx + 18, y_), (-1.0, 0.5 if y_ < 130 else -0.5), 400.0, 999.0 if pc is LA else 88.0, lead=0.0, seed=11 + int(pc.cx))
            self.jolt(th, 1.2)
            px_, th = pc.cx, th + 0.13
        b_op.snap(th, 0)
        self.layers["high"].append(op_open(b_op) + tf_open("translate", b_tr, fxy)
                                   + f'<circle r="6" fill="{p["cannon"]}" stroke="{p["fg"]}" stroke-width="1"/></g></g>')
        # the pirate watches it go, then takes a bow
        pir.pose(T_BOOM2 + 0.15, "hit", 0.04, "snap")
        pir.pose(T_BOOM2 + 0.5, "cheer", 0.12)
        pir.jump(24.2, 24.5, 748, FLOOR, 18)
        pir.land(24.5, 0.2, "cheer")
        pir.pose(24.9, "taunt", 0.12)

        # ---- 25.2  the rope from the opening comes back down, and he leaves the way he came
        RX = 748.0
        ry2, rop2 = Track(-80.0), Track(0)
        rop2.snap(25.2, 1)
        ry2.hold(25.2)
        ry2.to(25.7, FLOOR - 115.0, "out")
        ry2.to(25.85, FLOOR - 108.0, "inout")
        ry2.to(26.0, FLOOR - 115.0, "inout")
        ry2.hold(26.15)
        pir.pose(25.75, "crouch", 0.1)
        pir.takeoff(25.88, 0.2)
        pir.jump(25.9, 26.15, RX, FLOOR - 52.0, 22)
        pir.pose(26.0, "hang", 0.1)
        pir.pos.to(27.3, (RX, -10.0), "inout")
        ry2.to(27.3, -73.0, "inout")
        pir.hide(27.35)
        rop2.snap(27.35, 0)
        self.layers["props"].append(
            f'<line x1="{n(RX)}" y1="-80" x2="{n(RX)}" y2="-80" stroke="{p["fg"]}" stroke-width="1.4" opacity="0">'
            + anim("y2", ry2, n) + anim("opacity", rop2, f2) + "</line>")
        self.dust(RX, FLOOR, 25.9)

        # ---- 27.0  the tide comes in and resets the page
        wave_svg, tw0, v, F0 = self.wave(27.0, 860.0)
        t_hide = tw0 + (860 - F0) / v + 0.15
        for pc in self.pieces:
            pc.reset(t_hide)
        for tr_ in (poster.op, dg_op, cop, sw_op, f_op):
            tr_.snap(t_hide, 0)
        self.layers["top"].append(wave_svg)
        self.dagger = (dg_tr, dg_op, ang)

    # --- output
    def svg(self):
        p, L = self.p, self.layers
        dg_tr, dg_op, ang = self.dagger
        dagger = (op_open(dg_op) + tf_open("translate", dg_tr, fxy)
                  + f'<g transform="rotate({n(ang)})"><polygon points="0,-1.4 15,0 0,1.4" fill="{p["steel"]}" stroke="{p["fg"]}" stroke-width="0.6"/>'
                  f'<path d="M-1,-4V4M-1,0H-8" stroke="{p["fg"]}" stroke-width="1.6" stroke-linecap="round"/></g></g></g>')
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT_STACK}">',
               f"<defs>{self.defs}</defs>",
               f'<rect width="{W}" height="{H}" fill="{p["bg"]}"/>',
               "<g>", anim("transform", self.frame, fxy, tf="translate"),
               f'<path d="M0,{FLOOR + 1.5} H{W}" stroke="{p["rule"]}" stroke-width="2"/>']
        out += [pc.svg() for pc in self.pieces]
        out += L["props"]
        out.append(dagger)
        out += [x() if callable(x) else x for x in L["low"] + L["mid"]]
        out.append(self.pir.svg(p, p["pirate"], hat="tricorn", hat_fill=p["fg"], patch=True, sword=0.12))
        out.append(self.off.svg(p, p["navy"], hat="bicorne", hat_fill=p["navy"], sword=0.03))
        out += [c.svg(p, p["navy"], hat="bicorne", hat_fill=p["navy"], sword=0.03) for c in self.crew]
        out += L["high"] + L["top"]
        out.append("</g></svg>")
        return "".join(out)


# ------------------------------------------------------------------ preview
PREVIEW_TIMES = [0.4, 1.5, 2.35, 3.05, 4.3, 5.3, 6.5, 7.3, 8.56, 9.2, 10.4, 10.7, 11.35, 12.6, 14.0, 15.6, 16.87, 17.6, 19.15, 20.2, 21.6, 22.3, 22.9, 23.3, 23.5, 23.8, 24.4, 25.5, 26.4, 27.0, 28.0, 29.5]


def preview(outdir, files):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("preview needs playwright: pip install playwright && playwright install chromium")
        return
    os.makedirs(outdir, exist_ok=True)
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H})
        for theme, path in files.items():
            for t in PREVIEW_TIMES:
                pg.goto("file://" + os.path.abspath(path))
                pg.evaluate(f"(() => {{ const s = document.documentElement; s.pauseAnimations(); s.setCurrentTime({t}); }})()")
                pg.wait_for_timeout(40)
                pg.screenshot(path=os.path.join(outdir, f"{theme}_{t:05.2f}.png"))
        b.close()
    if ImageFont is not None:
        from PIL import Image, ImageDraw
        for theme in files:
            frames = [os.path.join(outdir, f"{theme}_{t:05.2f}.png") for t in PREVIEW_TIMES]
            cols = 2
            rows = (len(frames) + cols - 1) // cols
            sheet = Image.new("RGB", (cols * W, rows * H), "grey")
            for i, f in enumerate(frames):
                im = Image.open(f).convert("RGB")
                dr = ImageDraw.Draw(im)
                dr.rectangle((0, 0, 44, 13), fill=(0, 0, 0))
                dr.text((3, 1), f"{PREVIEW_TIMES[i]:.2f}s", fill=(255, 220, 0))
                sheet.paste(im, ((i % cols) * W, (i // cols) * H))
            sheet.save(os.path.join(outdir, f"sheet_{theme}.png"))
    print("preview frames in", outdir)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preview", action="store_true", help="also render PNG frames with Playwright")
    ap.add_argument("--out", default=os.path.dirname(os.path.abspath(__file__)), help="output directory")
    args = ap.parse_args()
    files = {}
    for theme in PALETTES:
        svg = Scene(theme).svg()
        path = os.path.join(args.out, f"raid-{theme}.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
        files[theme] = path
        print(f"raid-{theme}.svg  {len(svg.encode()) / 1024:.0f} KB")
    if args.preview:
        preview(os.path.join(args.out, "preview"), files)


if __name__ == "__main__":
    main()
