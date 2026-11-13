#!/usr/bin/env python3
"""ANSIL / README rumble. Adapted directly from the supplied inspiration.py.

The reference's poses, timing and six-act fight underpin Ansil's profile and a
custom Chopper cameo. Profile copy and word targets are configured below;
repository integration adds portable fonts, stable IDs, validation and previews.

python raid/make_raid_v2.py
python raid/make_raid_v2.py --check
python raid/make_raid_v2.py --preview --export [--browser PATH]
Building requires Pillow. Browser previews also need Playwright; video export
uses ffmpeg or imageio-ffmpeg. No dependencies are loaded by the SVG itself.
"""
import math
import html
import argparse
from bisect import bisect_right
from collections import Counter
import hashlib
import json
import itertools
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from PIL import ImageFont

# ---------------------------------------------------------------- constants
T = 31.0
EPS = 0.002
LEAD_TRIM = 0.25      # the whole loop starts this much sooner (the calm opening is shortened)
W, H, FLOOR = 830, 277, 272
H1_Y, RULE_Y = 32, 50
P_Y = [84, 124, 164, 204]
BODY_Y = -17
def load_fonts():
    """Use the reference's Liberation Sans, or its Windows/macOS Arial counterpart."""
    override = os.environ.get('RAID_FONT_DIR')
    candidates = []
    if override:
        candidates.append((Path(override)/'LiberationSans-Regular.ttf', Path(override)/'LiberationSans-Bold.ttf'))
    candidates.extend([
        (Path('/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'), Path('/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf')),
        (Path('/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf'), Path('/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf')),
        (Path(os.environ.get('WINDIR', 'C:/Windows'))/'Fonts/arial.ttf', Path(os.environ.get('WINDIR', 'C:/Windows'))/'Fonts/arialbd.ttf'),
        (Path('/System/Library/Fonts/Supplemental/Arial.ttf'), Path('/System/Library/Fonts/Supplemental/Arial Bold.ttf')),
    ])
    for regular, bold in candidates:
        if regular.is_file() and bold.is_file():
            return ImageFont.truetype(str(regular), 16), ImageFont.truetype(str(bold), 16)
    raise RuntimeError('Install Liberation Sans, or set RAID_FONT_DIR to a directory containing LiberationSans-Regular.ttf and LiberationSans-Bold.ttf.')


FONT, FONT_B = load_fonts()
FONT_STACK = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"

# Exact profile wording supplied by Ansil. The reference's crossed-out diary
# line is left empty; the three bio lines occupy its three action-bearing rows.
H1_TEXT = "Hi, I'm Ansil."
PARAS = [
    "",
    "B.Tech CSE Undergraduate.",
    "Developer. Experimenter. Builder.",
    "I build, break, and rebuild things.",
]
WORD_TARGETS = dict(kick=(3, "rebuild"), hole=(3, "things."),
                    low=(3, "break,"), middle=(2, "Experimenter."), high=(1, "Undergraduate."))
PALETTES = {
    "light": dict(bg="#ffffff", fg="#1f2328", rule="#d1d9e0", red="#cf222e", spark="#e3b341",
                  blade="#d6dbe0", blade_edge="#6b7580", hamon="#ffffff", tsuba="#8a6d2f", wrap="#2b2b2b",
                  pink="#d6409f", void_fg="#f0f0ff", smoke="#8c959f", flash="#ffffff", crack="#9ea5ad",
                  laser="#6e5cf5", scorch="#4b4f55", wood="#7a5230", wind="#22a9bd", wind_hi="#7fe3f0"),
    "dark":  dict(bg="#0d1117", fg="#e6edf3", rule="#3d444d", red="#f85149", spark="#e3b341",
                  blade="#dfe5ec", blade_edge="#6b7580", hamon="#ffffff", tsuba="#c9a24a", wrap="#2b2b2b",
                  pink="#f778ba", void_fg="#f0f0ff", smoke="#8b949e", flash="#f0f0ff", crack="#8b949e",
                  laser="#9d8dff", scorch="#aeb6bf", wood="#9a6b3f", wind="#5fd8e8", wind_hi="#ffffff"),
}
VOID_RIM = "#8f7cff"
BLOCK_GREEN = ["#5d9b3c", "#6fb04a", "#4e8a32"]
BLOCK_BROWN = ["#8a5a3c", "#9c6b47", "#74492f", "#a97a52"]
CHOPPER_COLORS = dict(fur="#dba86d", muzzle="#f6d9aa", ink="#573b2b",
                     antlers="#b77d48", hat="#e979a6", brim="#c84d80",
                     nose="#238ed0", shorts="#9c4a75", hoof="#634334")
SPLINES = {"lin": "0 0 1 1", "in": "0.55 0 1 1", "out": "0 0 0.45 1", "inout": "0.45 0 0.55 1", "snap": "0 0 0.15 1"}

# the page heals while it is hidden inside the void (see ACT 6 for the window)
FADE = (26.55, 27.05)
RESTORE = (26.65, 27.65)


# Display times include the reference's quarter-second lead trim.
REFERENCE_SHA256 = "beada4909758073238404924e9fae339702c6db2f41c6b00d53b5e80cbdc1737"
ALT = ('Ansil / ClashLex: two stick figures break into a profile README, fight '
       'across its words with a sword, a Chopper cameo, clones, a laser and a collapsing wall, '
       'then disappear into a void as the page rebuilds.')
ACTS = [('01-break-in', 0., 5.53), ('02-challenge', 5.53, 7.91),
        ('03-chase', 7.91, 11.89), ('04-escalation', 11.89, 17.73),
        ('05-counterattack', 17.73, 25.45), ('06-reset', 25.45, T)]
BEATS = [
    (.65, 'Cracks spread through a word', 'page'),
    (1.45, 'The page shatters and a hole opens', 'hole'),
    (2.07, 'Hands catch the rim; the figure climbs out', 'climb'),
    (3.61, 'Both feet reach the page', 'handoff'),
    (4.71, 'A landing, a dust-off, a look around', 'acting'),
    (5.39, 'A jump kick scatters the letters', 'type'),
    (5.73, 'The second figure lands on the heading rule', 'arrival'),
    (6.09, 'A sword is drawn', 'sword'),
    (6.51, 'A teleport turns a slash into a miss', 'teleport'),
    (7.28, 'A shoulder tap, a turn, a leaning dodge', 'double take'),
    (8.59, 'The first word splits under a rising cut', 'first cut'),
    (9.21, 'The blade comes down through the next line', 'second cut'),
    (9.97, 'A third rising cut finishes the chase', 'third cut'),
    (10.87, 'The sword sticks in the floor', 'sword'),
    (11.65, 'A kick interrupts the pulling', 'kick'),
    (12.35, 'Chopper rushes in and grabs a boot', 'Chopper'),
    (13.85, 'Three clones arrive; two collide', 'clones'),
    (15.55, 'A laser meets a wall of wind', 'laser / windwall'),
    (16.93, 'A flying kick tears through the wall', 'sword throw'),
    (17.73, 'A charm heart changes the tempo', 'heart'),
    (19.28, 'The long wind-up makes the page tremble', 'anticipation'),
    (20.35, 'The punch crosses the entire page', 'impact'),
    (22.12, 'Six blocks become a hiding place', 'wall'),
    (22.70, 'A planted foot becomes a sudden dash', 'flash step'),
    (24.19, 'The wall falls on its builder', 'burial'),
    (25.08, 'A pickaxe clears the rubble', 'pickaxe'),
    (26.13, 'A void swallows the fight', 'void'),
    (28.83, 'The page is restored as the void closes', 'loop'),
]


def n(v):
    s = f"{v:.1f}"
    s = s[:-2] if s.endswith(".0") else s
    return "0" if s == "-0" else s


def rnd(i):
    x = math.sin(i * 12.9898 + 78.233) * 43758.5453
    return x - math.floor(x)


# ---------------------------------------------------------------- tracks
class Track:
    def __init__(self, v0):
        self.keys = [[0.0, v0, "lin"]]

    @property
    def t(self):
        return self.keys[-1][0]

    @property
    def v(self):
        return self.keys[-1][1]

    def add(self, t, v, ease="lin"):
        if t <= self.t:
            t = self.t + EPS
        self.keys.append([round(t, 5), v, ease])

    def hold(self, t):
        if t > self.t + 1e-9:
            self.keys.append([round(t, 5), self.v, "lin"])

    def set(self, t, v):
        self.hold(t - EPS)
        self.add(t, v)

    def finished(self):
        ks = [list(k) for k in self.keys]
        assert ks[-1][0] <= T, f"key past loop end {ks[-1]}"
        if ks[-1][0] < T:
            ks.append([T, ks[-1][1], "lin"])
        return ks


def _bisect(keys, t):
    lo, hi = 0, len(keys) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if keys[mid][0] <= t:
            lo = mid
        else:
            hi = mid - 1
    return lo


def eased(s, ease):
    """The same cubic-bezier mapping the browser applies to keySplines, so world-space lookups
    land where the animation actually is mid-tween."""
    if ease == "lin" or s <= 0 or s >= 1:
        return s
    x1, y1, x2, y2 = (float(v) for v in SPLINES[ease].split())
    lo, hi = 0.0, 1.0
    for _ in range(24):
        mid = (lo + hi) / 2
        x = 3 * (1 - mid) ** 2 * mid * x1 + 3 * (1 - mid) * mid ** 2 * x2 + mid ** 3
        if x < s:
            lo = mid
        else:
            hi = mid
    u = (lo + hi) / 2
    return 3 * (1 - u) ** 2 * u * y1 + 3 * (1 - u) * u ** 2 * y2 + u ** 3


def _segment(ks, t):
    i = _bisect(ks, t)
    if i >= len(ks) - 1:
        return ks[-1], ks[-1], 0.0
    t0, v0, _ = ks[i]
    t1, v1, e = ks[i + 1]
    s = 0 if t1 == t0 else (t - t0) / (t1 - t0)
    return ks[i], ks[i + 1], eased(s, e)


def eval_num(track, t):
    k0, k1, s = _segment(track.keys, t)
    v0, v1 = k0[1], k1[1]
    if isinstance(v0, (int, float)):
        return v0 + (v1 - v0) * s
    return tuple(a + (b - a) * s for a, b in zip(v0, v1))


def eval_step(track, t):
    return track.keys[_bisect(track.keys, t)][1]


def window_track(track, t0, t1):
    """A copy of `track` that only carries the keys between t0 and t1 (used for props that are
    invisible outside that window, so their animations stay small)."""
    w = Track(eval_step(track, t0))
    w.hold(t0 - EPS)
    for t, v, e in track.keys:
        if t0 <= t <= t1:
            w.add(t, v, e)
    w.hold(t1)
    return w


def animate(attr, track, fmt):
    keys = track.finished()
    # shift everything earlier by LEAD_TRIM; the loop still ends at T, with the tail hold absorbing it
    keys = [[0.0, keys[0][1], "lin"]] + [[max(EPS, t - LEAD_TRIM), v, e] for t, v, e in keys[1:]]
    for i in range(1, len(keys)):
        if keys[i][0] <= keys[i - 1][0]:
            keys[i][0] = keys[i - 1][0] + EPS / 2
    keys[-1][0] = T
    vals = ";".join(fmt(v) for _, v, _ in keys)
    kt = ";".join(f"{t / T:.6f}" for t, _, _ in keys)
    if any(e != "lin" for _, _, e in keys[1:]):
        ks = ";".join(SPLINES[e] for _, _, e in keys[1:])
        return (f'<animate attributeName="{attr}" values="{vals}" keyTimes="{kt}" keySplines="{ks}" '
                f'calcMode="spline" dur="{T}s" repeatCount="indefinite"/>')
    return f'<animate attributeName="{attr}" values="{vals}" keyTimes="{kt}" dur="{T}s" repeatCount="indefinite"/>'


def animate_tf(kind, track, fmt):
    return animate("transform", track, fmt).replace("<animate ", f'<animateTransform type="{kind}" ')


f_xy = lambda v: f"{n(v[0])} {n(v[1])}"
f_rot = lambda v: f"{n(v[0])} {n(v[1])} {n(v[2])}"
f_s = lambda v: f"{v:.3f}".rstrip("0").rstrip(".")
f_ss = lambda s: f"{f_s(s)} {f_s(s)}"


# ---------------------------------------------------------------- poses
# local coords, feet at (0,0), up is -y, facing +x.  WT = weapon tip (sword or pickaxe head)
P_ = dict
POSES = {
    "stand":  P_(H=(0, -30), N=(0, -25), P=(0, -13), LE=(-3, -18), LH=(-4, -11), RE=(3, -18), RH=(4, -11), LK=(-2, -6), LF=(-3, 0), RK=(2, -6), RF=(3, 0)),
    "guard":  P_(H=(1, -30), N=(0, -25), P=(0, -13), LE=(3, -19), LH=(6, -25), RE=(6, -21), RH=(9, -27), LK=(-4, -7), LF=(-6, 0), RK=(4, -7), RF=(6, 0)),
    # run cycle: contact -> down (absorb) -> passing -> up (push off). Leaning into the run.
    "runA":   P_(H=(5, -29), N=(4, -24), P=(0, -13), LE=(-5, -20), LH=(-10, -16), RE=(8, -21), RH=(13, -26), LK=(-6, -8), LF=(-12, -2), RK=(8, -8), RF=(12, 0)),
    "runD":   P_(H=(5, -27), N=(4, -22), P=(0, -12), LE=(-4, -18), LH=(-8, -13), RE=(7, -20), RH=(11, -24), LK=(-8, -7), LF=(-13, -5), RK=(4, -6), RF=(3, 0)),
    "runB":   P_(H=(5, -31), N=(4, -26), P=(0, -15), LE=(1, -21), LH=(2, -15), RE=(4, -22), RH=(6, -17), LK=(5, -10), LF=(2, -5), RK=(-2, -9), RF=(-4, -1)),
    "punch":  P_(H=(4, -29), N=(3, -24), P=(0, -13), LE=(-3, -20), LH=(1, -24), RE=(10, -25), RH=(18, -26), LK=(-6, -7), LF=(-9, 0), RK=(5, -6), RF=(8, 0)),
    "kick":   P_(H=(-2, -30), N=(-1, -25), P=(0, -13), LE=(-5, -21), LH=(-9, -17), RE=(4, -21), RH=(8, -18), LK=(-2, -6), LF=(-3, 0), RK=(7, -16), RF=(16, -22)),
    "fkick":  P_(H=(-14, -24), N=(-9, -23), P=(0, -20), LE=(-13, -18), LH=(-18, -14), RE=(-10, -28), RH=(-16, -31), LK=(-4, -13), LF=(-8, -10), RK=(7, -20), RF=(16, -19)),
    "crouch": P_(H=(2, -20), N=(1, -16), P=(0, -8), LE=(-4, -11), LH=(-3, -5), RE=(5, -11), RH=(7, -6), LK=(-6, -6), LF=(-7, 0), RK=(6, -6), RF=(7, 0)),
    "hit":    P_(H=(-5, -28), N=(-3, -24), P=(0, -13), LE=(-8, -30), LH=(-10, -36), RE=(2, -31), RH=(0, -37), LK=(2, -8), LF=(5, -2), RK=(-4, -7), RF=(-7, 0)),
    "tuck":   P_(H=(4, -24), N=(2, -20), P=(0, -12), LE=(6, -16), LH=(5, -10), RE=(7, -15), RH=(6, -9), LK=(7, -10), LF=(2, -6), RK=(8, -11), RF=(3, -7)),
    "lying":  P_(H=(-16, -5), N=(-11, -4), P=(0, -3), LE=(-7, -9), LH=(-3, -7), RE=(-10, -1), RH=(-6, 0), LK=(6, -6), LF=(12, -7), RK=(7, -1), RF=(14, 0)),
    "climb":  P_(H=(0, -30), N=(0, -25), P=(0, -13), LE=(-9, -22), LH=(-14, -19), RE=(9, -22), RH=(14, -19), LK=(-1, -6), LF=(-2, 0), RK=(1, -6), RF=(2, 0)),
    "fall":   P_(H=(0, -30), N=(0, -25), P=(0, -13), LE=(-6, -30), LH=(-8, -37), RE=(6, -30), RH=(8, -37), LK=(-3, -7), LF=(-5, -1), RK=(3, -7), RF=(5, -1)),
    "hips":   P_(H=(0, -30), N=(0, -25), P=(0, -13), LE=(-6, -19), LH=(-2, -14), RE=(6, -19), RH=(2, -14), LK=(-2, -6), LF=(-3, 0), RK=(2, -6), RF=(3, 0)),
    "point":  P_(H=(1, -30), N=(0, -25), P=(0, -13), LE=(-4, -19), LH=(-5, -12), RE=(8, -23), RH=(16, -24), LK=(-2, -6), LF=(-3, 0), RK=(2, -6), RF=(3, 0)),
    "dust":   P_(H=(0, -30), N=(0, -25), P=(0, -13), LE=(4, -20), LH=(7, -18), RE=(5, -19), RH=(8, -20), LK=(-2, -6), LF=(-3, 0), RK=(2, -6), RF=(3, 0)),
    "dust2":  P_(H=(0, -30), N=(0, -25), P=(0, -13), LE=(5, -19), LH=(8, -21), RE=(4, -21), RH=(7, -17), LK=(-2, -6), LF=(-3, 0), RK=(2, -6), RF=(3, 0)),
    "wave1":  P_(H=(0, -30), N=(0, -25), P=(0, -13), LE=(-3, -18), LH=(-4, -11), RE=(7, -30), RH=(9, -38), LK=(-2, -6), LF=(-3, 0), RK=(2, -6), RF=(3, 0)),
    "wave2":  P_(H=(0, -30), N=(0, -25), P=(0, -13), LE=(-3, -18), LH=(-4, -11), RE=(7, -30), RH=(13, -36), LK=(-2, -6), LF=(-3, 0), RK=(2, -6), RF=(3, 0)),
    "dizzy":  P_(H=(-2, -29), N=(-1, -24), P=(0, -13), LE=(-6, -20), LH=(-9, -16), RE=(5, -20), RH=(8, -16), LK=(-4, -7), LF=(-7, 0), RK=(5, -7), RF=(8, 0)),
    "lean":   P_(H=(-3, -30), N=(-2, -25), P=(0, -13), LE=(-8, -22), LH=(-12, -18), RE=(3, -22), RH=(7, -18), LK=(-2, -6), LF=(-3, 0), RK=(3, -6), RF=(4, 0)),
    "tap":    P_(H=(1, -30), N=(0, -25), P=(0, -13), LE=(-4, -19), LH=(-5, -12), RE=(8, -24), RH=(15, -24), LK=(-2, -6), LF=(-3, 0), RK=(2, -6), RF=(3, 0)),
    "tap2":   P_(H=(1, -30), N=(0, -25), P=(0, -13), LE=(-4, -19), LH=(-5, -12), RE=(7, -23), RH=(12, -22), LK=(-2, -6), LF=(-3, 0), RK=(2, -6), RF=(3, 0)),
    "scratch": P_(H=(1, -30), N=(0, -25), P=(0, -13), LE=(-3, -18), LH=(-4, -11), RE=(6, -30), RH=(3, -36), LK=(-2, -6), LF=(-3, 0), RK=(2, -6), RF=(3, 0)),
    "shrug":  P_(H=(0, -29), N=(0, -24), P=(0, -13), LE=(-7, -19), LH=(-11, -23), RE=(7, -19), RH=(11, -23), LK=(-2, -6), LF=(-3, 0), RK=(2, -6), RF=(3, 0)),
    "sign":   P_(H=(0, -30), N=(0, -25), P=(0, -13), LE=(4, -20), LH=(5, -27), RE=(5, -19), RH=(5, -28), LK=(-3, -7), LF=(-5, 0), RK=(3, -7), RF=(5, 0)),
    "clap":   P_(H=(1, -30), N=(0, -25), P=(0, -13), LE=(6, -22), LH=(13, -26), RE=(6, -21), RH=(13, -25), LK=(-3, -7), LF=(-5, 0), RK=(3, -7), RF=(5, 0)),
    "windup": P_(H=(-4, -28), N=(-3, -23), P=(0, -13), LE=(3, -20), LH=(7, -23), RE=(-10, -26), RH=(-16, -24), LK=(-6, -7), LF=(-9, 0), RK=(5, -7), RF=(8, 0)),
    "windup2": P_(H=(-7, -27), N=(-6, -22), P=(-1, -13), LE=(4, -20), LH=(9, -24), RE=(-14, -25), RH=(-21, -21), LK=(-8, -6), LF=(-12, 0), RK=(6, -7), RF=(9, 0)),
    "mega":   P_(H=(8, -27), N=(6, -22), P=(0, -13), LE=(-6, -19), LH=(-10, -14), RE=(16, -24), RH=(26, -25), LK=(-8, -6), LF=(-13, 0), RK=(7, -6), RF=(10, 0)),
    "mega2":  P_(H=(10, -26), N=(8, -21), P=(1, -13), LE=(-6, -19), LH=(-10, -14), RE=(18, -23), RH=(28, -23), LK=(-8, -6), LF=(-13, 0), RK=(7, -6), RF=(10, 0)),
    "cover":  P_(H=(2, -19), N=(1, -15), P=(0, -8), LE=(-2, -20), LH=(2, -24), RE=(4, -19), RH=(1, -24), LK=(-6, -6), LF=(-7, 0), RK=(6, -6), RF=(7, 0)),
    "place_lo": P_(H=(2, -29), N=(1, -24), P=(0, -13), LE=(-4, -19), LH=(-5, -12), RE=(8, -20), RH=(15, -13), LK=(-2, -6), LF=(-3, 0), RK=(2, -6), RF=(3, 0)),
    "place_hi": P_(H=(2, -29), N=(1, -24), P=(0, -13), LE=(-4, -19), LH=(-5, -12), RE=(8, -26), RH=(15, -32), LK=(-2, -6), LF=(-3, 0), RK=(2, -6), RF=(3, 0)),
    "whistle": P_(H=(0, -30), N=(0, -25), P=(0, -13), LE=(-3, -18), LH=(-4, -11), RE=(5, -24), RH=(3, -31), LK=(-2, -6), LF=(-3, 0), RK=(2, -6), RF=(3, 0)),
    "kiss2":  P_(H=(1, -30), N=(0, -25), P=(0, -13), LE=(-3, -18), LH=(-4, -11), RE=(8, -25), RH=(16, -28), LK=(-2, -6), LF=(-3, 0), RK=(2, -6), RF=(3, 0)),
    "crack":  P_(H=(1, -30), N=(0, -25), P=(0, -13), LE=(4, -20), LH=(8, -23), RE=(5, -19), RH=(8, -22), LK=(-2, -6), LF=(-3, 0), RK=(2, -6), RF=(3, 0)),
    "crack2": P_(H=(1, -30), N=(0, -25), P=(0, -13), LE=(4, -19), LH=(9, -21), RE=(5, -20), RH=(9, -24), LK=(-2, -6), LF=(-3, 0), RK=(2, -6), RF=(3, 0)),
    # lovestruck: limp, floating on his back (used with face -1 and a +90 degree roll)
    "float":  P_(H=(-2, -31), N=(-1, -26), P=(0, -13), LE=(-6.8, -23.2), LH=(-12.6, -20.4), RE=(-4.8, -22.7), RH=(-9.6, -19.4), LK=(-1.5, -6.5), LF=(4.7, -9.8), RK=(1.0, -6.0), RF=(7.6, -9.5)),
    "push":   P_(H=(6, -27), N=(5, -22), P=(0, -13), LE=(10, -20), LH=(16, -19), RE=(10, -23), RH=(16, -22), LK=(-6, -7), LF=(-10, 0), RK=(5, -7), RF=(8, 0)),
    # flash step: a slow, deliberate stance, front foot planting
    "plant":  P_(H=(2, -29), N=(1, -24), P=(0, -13), LE=(-4, -19), LH=(-6, -13), RE=(4, -20), RH=(7, -14), LK=(-3, -6), LF=(-5, 0), RK=(9, -9), RF=(14, -3)),
    "plant2": P_(H=(3, -28), N=(2, -23), P=(0, -13), LE=(-4, -19), LH=(-6, -13), RE=(4, -20), RH=(7, -14), LK=(-3, -6), LF=(-5, 0), RK=(9, -8), RF=(15, 0)),
    "dash":   P_(H=(14, -24), N=(11, -20), P=(0, -13), LE=(-6, -17), LH=(-14, -14), RE=(0, -16), RH=(-8, -12), LK=(-7, -8), LF=(-14, -3), RK=(8, -9), RF=(16, -3)),
    # hovering for the laser
    "fly":    P_(H=(0, -31), N=(0, -26), P=(0, -14), LE=(-7, -27), LH=(-12, -31), RE=(7, -27), RH=(12, -31), LK=(-3, -8), LF=(-6, -2), RK=(2, -7), RF=(4, 0)),
    # sword poses
    "sw_draw": P_(H=(0, -30), N=(0, -25), P=(0, -13), LE=(-3, -19), LH=(-4, -12), RE=(-4, -28), RH=(-6, -33), LK=(-2, -6), LF=(-3, 0), RK=(2, -6), RF=(3, 0), WT=(-16, -19)),
    "sw_idle": P_(H=(1, -30), N=(0, -25), P=(0, -13), LE=(-4, -20), LH=(-6, -14), RE=(6, -21), RH=(10, -19), LK=(-4, -7), LF=(-6, 0), RK=(4, -7), RF=(6, 0), WT=(26, -36)),
    "sw_wind": P_(H=(-6, -29), N=(-5, -24), P=(-2, -13), LE=(-2, -19), LH=(2, -15), RE=(-12, -27), RH=(-16, -34), LK=(-8, -7), LF=(-11, 0), RK=(3, -7), RF=(6, 0), WT=(-40, -30)),
    "sw_up":   P_(H=(-1, -30), N=(-1, -25), P=(0, -13), LE=(-5, -20), LH=(-3, -14), RE=(2, -31), RH=(4, -39), LK=(-4, -7), LF=(-6, 0), RK=(4, -7), RF=(6, 0), WT=(-13, -58)),
    "sw_down": P_(H=(6, -27), N=(5, -22), P=(1, -13), LE=(-4, -19), LH=(-7, -14), RE=(12, -20), RH=(18, -14), LK=(-7, -7), LF=(-10, 0), RK=(7, -7), RF=(10, 0), WT=(34, 2)),
    "sw_thru": P_(H=(10, -25), N=(8, -20), P=(2, -12), LE=(-2, -18), LH=(-5, -13), RE=(10, -15), RH=(12, -8), LK=(-8, -6), LF=(-12, 0), RK=(9, -6), RF=(13, 0), WT=(4, 12)),
    "sw_rec":  P_(H=(6, -27), N=(5, -22), P=(1, -13), LE=(-3, -19), LH=(-6, -13), RE=(8, -18), RH=(11, -12), LK=(-6, -7), LF=(-9, 0), RK=(6, -7), RF=(9, 0), WT=(20, 8)),
    "sw_stab": P_(H=(-12, -26), N=(-8, -24), P=(0, -19), LE=(-10, -30), LH=(-16, -34), RE=(8, -20), RH=(14, -14), LK=(-6, -14), LF=(-12, -10), RK=(-4, -20), RF=(-10, -24), WT=(25, 3)),
    # rising cut: blade low and back, sweeps up and forward, ends high over the head (= a downswing's wind-up)
    "sw_low":    P_(H=(-3, -29), N=(-2, -24), P=(0, -13), LE=(-5, -20), LH=(-6, -15), RE=(2, -17), RH=(-2, -11), LK=(-5, -7), LF=(-8, 0), RK=(5, -7), RF=(8, 0), WT=(-20, 6)),
    "sw_upcut":  P_(H=(4, -29), N=(3, -24), P=(0, -13), LE=(-4, -20), LH=(-7, -15), RE=(10, -24), RH=(16, -22), LK=(-6, -7), LF=(-9, 0), RK=(6, -7), RF=(9, 0), WT=(40, -38)),
    "sw_upthru": P_(H=(1, -30), N=(0, -25), P=(0, -13), LE=(-4, -20), LH=(-6, -14), RE=(4, -33), RH=(2, -40), LK=(-4, -7), LF=(-6, 0), RK=(4, -7), RF=(6, 0), WT=(-18, -62)),
    # windwall cast: blade thrust out flat in front
    "ww_cast":   P_(H=(3, -30), N=(2, -25), P=(0, -13), LE=(5, -20), LH=(11, -22), RE=(9, -22), RH=(16, -21), LK=(-5, -7), LF=(-8, 0), RK=(5, -7), RF=(8, 0), WT=(46, -20)),
    "tug1":   P_(H=(-6, -28), N=(-4, -24), P=(0, -13), LE=(7, -19), LH=(14, -21), RE=(8, -22), RH=(14, -21), LK=(-6, -7), LF=(-9, 0), RK=(5, -7), RF=(8, 0)),
    "tug2":   P_(H=(-10, -27), N=(-8, -23), P=(-1, -13), LE=(6, -20), LH=(14, -21), RE=(7, -23), RH=(14, -21), LK=(-7, -7), LF=(-10, 0), RK=(5, -7), RF=(8, 0)),
    # crawling out of a hole, rim at local y=0 (feet below the rim, torso above). Facing +x.
    # climbing out of a manhole. Origin = a point on the hole's TOP rim. +y hangs down inside the hole,
    # -y is up above the rim on the page. Facing +x (then mirrored as needed).
    # 1. hanging from the rim by both hands, feet dangling in the dark
    "mh_hang":  P_(H=(0, 10), N=(0, 14), P=(0, 26), LE=(-6, 7), LH=(-8, 0), RE=(6, 7), RH=(8, 0), LK=(-3, 33), LF=(-4, 40), RK=(3, 33), RF=(4, 40)),
    # 2. pull-up: elbows bent, chin at the rim
    "mh_pull":  P_(H=(0, 2), N=(0, 7), P=(0, 19), LE=(-8, 5), LH=(-8, 0), RE=(8, 5), RH=(8, 0), LK=(-4, 27), LF=(-6, 34), RK=(4, 27), RF=(7, 33)),
    # 3. press-up: arms locked straight, chest above the rim, hips at the rim, legs hanging
    "mh_press": P_(H=(1, -17), N=(0, -12), P=(0, 1), LE=(-8, -6), LH=(-9, 0), RE=(8, -6), RH=(9, 0), LK=(-3, 9), LF=(-4, 17), RK=(3, 9), RF=(5, 17)),
    # 4. one knee swung up onto the page, other leg still hanging, leaning forward on the hands
    "mh_knee":  P_(H=(10, -20), N=(8, -15), P=(2, -3), LE=(2, -8), LH=(6, 0), RE=(10, -9), RH=(14, 0), LK=(-2, 6), LF=(-5, 13), RK=(12, -3), RF=(13, 3)),
    # 5. crouched on the page just past the rim, both feet on the page
    "mh_crouch": P_(H=(8, -22), N=(6, -18), P=(2, -9), LE=(-2, -13), LH=(0, -7), RE=(8, -13), RH=(11, -7), LK=(-3, -5), LF=(-4, 0), RK=(8, -5), RF=(10, 0)),
    # climbing out through the hole (older poses, kept). Origin = a point on the hole's bottom rim (the sill).
    # -y is inside the hole (behind the page), +y is outside, in front of the page.
    # squatting inside with both hands on the sill
    "sill":   P_(H=(0, -19), N=(0, -15), P=(0, -8), LE=(-7, -8), LH=(-9, 0), RE=(7, -8), RH=(9, 0), LK=(-6, -5), LF=(-5, 0), RK=(6, -5), RF=(5, 0)),
    # head and shoulders out, hanging down in front of the page, hands pressed on the page, legs kicking inside
    "flop1":  P_(H=(2, 13), N=(1, 8), P=(0, -9), LE=(-8, 10), LH=(-10, 17), RE=(8, 10), RH=(10, 17), LK=(-8, -13), LF=(-15, -15), RK=(8, -12), RF=(15, -14)),
    "flop1b": P_(H=(2, 13), N=(1, 8), P=(0, -9), LE=(-8, 10), LH=(-10, 17), RE=(8, 10), RH=(10, 17), LK=(-7, -15), LF=(-13, -20), RK=(9, -10), RF=(16, -10)),
    # hips over the sill, hands walking down the page, feet dragging over the rim
    "flop2":  P_(H=(2, 24), N=(1, 19), P=(0, 6), LE=(-8, 20), LH=(-10, 27), RE=(8, 20), RH=(10, 27), LK=(-8, 0), LF=(-14, -3), RK=(8, 1), RF=(14, -2)),
    # pickaxe poses (WT = the head end of the handle)
    "dig_hold": P_(H=(0, -30), N=(0, -25), P=(0, -13), LE=(-3, -18), LH=(-4, -11), RE=(5, -21), RH=(8, -27), LK=(-2, -6), LF=(-3, 0), RK=(2, -6), RF=(3, 0), WT=(-8, -44)),
    "dig_up":  P_(H=(-2, -30), N=(-1, -25), P=(0, -13), LE=(-4, -31), LH=(-6, -38), RE=(-3, -31), RH=(-5, -38), LK=(-3, -7), LF=(-5, 0), RK=(3, -7), RF=(5, 0), WT=(-16, -50)),
    "dig_down": P_(H=(4, -28), N=(3, -23), P=(0, -13), LE=(6, -20), LH=(12, -12), RE=(7, -21), RH=(13, -13), LK=(-5, -7), LF=(-8, 0), RK=(5, -7), RF=(8, 0), WT=(29, -1)),
}


def mirror_limbs(p):
    q = dict(p)
    for a, b in (("LE", "RE"), ("LH", "RH"), ("LK", "RK"), ("LF", "RF")):
        q[a], q[b] = p[b], p[a]
    return q


def breathe(p):
    q = dict(p)
    for k in ("H", "N"):
        q[k] = (p[k][0], p[k][1] - 1)
    for k in ("LE", "RE", "LH", "RH"):
        q[k] = (p[k][0], p[k][1] - 0.6)
    return q


for _nm in ("runA", "runD", "runB"):
    POSES[_nm + "2"] = mirror_limbs(POSES[_nm])
for _nm in ("stand", "hips", "guard", "sw_idle", "point", "dizzy", "cover", "fall", "tug1", "sign", "dig_hold", "fly", "float", "ww_cast"):
    POSES[_nm + "_b"] = breathe(POSES[_nm])
LIMBS = [("N", "P"), ("N", "LE", "LH"), ("N", "RE", "RH"), ("P", "LK", "LF"), ("P", "RK", "RF")]
RUN_CYCLE = ["runA", "runD", "runB", "runA2", "runD2", "runB2"]
RUN_BOB = [0, 1.2, -1.2, 0, 1.2, -1.2]       # vertical bob per run frame (down on contact, up on pass)


def pose_pt(P, key):
    if key == "WT":
        return P.get("WT", (P["RH"][0] + 4, P["RH"][1] - 22))
    return P[key]


def interp_pose(a, b, s):
    return {k: (pose_pt(a, k)[0] + (pose_pt(b, k)[0] - pose_pt(a, k)[0]) * s,
                pose_pt(a, k)[1] + (pose_pt(b, k)[1] - pose_pt(a, k)[1]) * s)
            for k in set(a) | set(b) | {"WT"}}


def eval_pose(track, t):
    k0, k1, s = _segment(track.keys, t)
    return interp_pose(POSES[k0[1]], POSES[k1[1]], s)


def limb_str(P, limb):
    return " ".join(f"{n(pose_pt(P, k)[0])},{n(pose_pt(P, k)[1])}" for k in limb)


def poly_str(pts):
    return " ".join(f"{n(x)},{n(y)}" for x, y in pts)


def frame_uv(P):
    """Unit vectors along the weapon (hand -> tip) and perpendicular to it, plus the length."""
    rh, wt = P["RH"], pose_pt(P, "WT")
    dx, dy = wt[0] - rh[0], wt[1] - rh[1]
    L = math.hypot(dx, dy) or 1
    ux, uy = dx / L, dy / L
    return rh, wt, (ux, uy), (-uy, ux), L


def katana_parts(P):
    """A curved single-edged blade, temper line, oval tsuba, wrapped handle, end cap."""
    rh, wt, (ux, uy), (px, py), L = frame_uv(P)
    # the edge sits on the -perp side; the blade bows the other way, toward the spine
    bx, by = rh[0] + ux * 2.6, rh[1] + uy * 2.6
    lb = L - 2.6
    bend = lb * 0.075

    def spine(s):
        c = 4 * bend * s * (1 - s)
        return bx + ux * lb * s + px * c, by + uy * lb * s + py * c

    def off(pt, side, w):
        return pt[0] + px * side * w, pt[1] + py * side * w

    back = [off(spine(s), 1, 1.25 - 0.3 * s) for s in (0, 0.3, 0.6, 0.86)]
    edge = [off(spine(s), -1, 1.9 - 0.4 * s) for s in (0.86, 0.6, 0.3, 0)]
    blade = back + [wt] + edge
    hamon = [off(spine(s), -1, 0.55) for s in (0.06, 0.3, 0.6, 0.86)]
    cx, cy = rh[0] + ux * 1.2, rh[1] + uy * 1.2
    tsuba = [(cx + px * 3.4 * math.cos(a) + ux * 1.7 * math.sin(a), cy + py * 3.4 * math.cos(a) + uy * 1.7 * math.sin(a))
             for a in [i * math.pi / 4 for i in range(8)]]
    h0x, h0y = rh[0] - ux * 0.6, rh[1] - uy * 0.6
    h1x, h1y = rh[0] - ux * 10.5, rh[1] - uy * 10.5
    tsuka = [(h0x + px * 1.4, h0y + py * 1.4), (h1x + px * 1.4, h1y + py * 1.4), (h1x - px * 1.4, h1y - py * 1.4), (h0x - px * 1.4, h0y - py * 1.4)]
    diamonds = []
    for s in (0.22, 0.52, 0.82):
        dx_, dy_ = h0x + (h1x - h0x) * s, h0y + (h1y - h0y) * s
        diamonds.append([(dx_ + ux * 1.3, dy_ + uy * 1.3), (dx_ + px * 1.2, dy_ + py * 1.2), (dx_ - ux * 1.3, dy_ - uy * 1.3), (dx_ - px * 1.2, dy_ - py * 1.2)])
    kx, ky = rh[0] - ux * 11.3, rh[1] - uy * 11.3
    kashira = [(kx + ux * 0.9 + px * 1.6, ky + uy * 0.9 + py * 1.6), (kx - ux * 0.9 + px * 1.6, ky - uy * 0.9 + py * 1.6),
               (kx - ux * 0.9 - px * 1.6, ky - uy * 0.9 - py * 1.6), (kx + ux * 0.9 - px * 1.6, ky + uy * 0.9 - py * 1.6)]
    return dict(blade=blade, hamon=hamon, tsuba=tsuba, tsuka=tsuka, d0=diamonds[0], d1=diamonds[1], d2=diamonds[2], kashira=kashira)


KATANA_STYLE = [
    ("tsuka", "wrap", None, 0),
    ("d0", "red", None, 0), ("d1", "red", None, 0), ("d2", "red", None, 0),
    ("kashira", "tsuba", "fg", 0.5),
    ("blade", "blade", "blade_edge", 0.7),
    ("hamon", None, "hamon", 0.9),
    ("tsuba", "tsuba", "fg", 0.6),
]


def katana_svg(parts, p, animated=None):
    """animated: optional pose-track to animate `points` from; otherwise static."""
    out = []
    for key, fill, stroke, sw in KATANA_STYLE:
        pts = parts[key]
        tag = "polyline" if key == "hamon" else "polygon"
        attrs = f'fill="{p[fill]}"' if fill else 'fill="none"'
        if stroke:
            attrs += f' stroke="{p[stroke]}" stroke-width="{sw}" stroke-linejoin="round"'
        if key == "hamon":
            attrs += ' stroke-linecap="round" opacity="0.75"'
        anim = animate("points", animated, lambda nm, key=key: poly_str(katana_parts(POSES[nm])[key])) if animated else ""
        out.append(f'<{tag} points="{poly_str(pts)}" {attrs}>{anim}</{tag}>')
    return "".join(out)


def pick_parts(P):
    rh, wt, (ux, uy), (px, py), L = frame_uv(P)
    h0x, h0y = rh[0] - ux * 4, rh[1] - uy * 4
    handle = [(h0x + px * 1.1, h0y + py * 1.1), (wt[0] + px * 1.1, wt[1] + py * 1.1), (wt[0] - px * 1.1, wt[1] - py * 1.1), (h0x - px * 1.1, h0y - py * 1.1)]
    head = [(wt[0] + px * 11 - ux * 2.2, wt[1] + py * 11 - uy * 2.2), (wt[0] + px * 6 + ux * 2.2, wt[1] + py * 6 + uy * 2.2),
            (wt[0] + ux * 2.8, wt[1] + uy * 2.8), (wt[0] - px * 6 + ux * 2.2, wt[1] - py * 6 + uy * 2.2),
            (wt[0] - px * 11 - ux * 2.2, wt[1] - py * 11 - uy * 2.2), (wt[0] - px * 6 - ux * 1.2, wt[1] - py * 6 - uy * 1.2),
            (wt[0] - ux * 1.4, wt[1] - uy * 1.4), (wt[0] + px * 6 - ux * 1.2, wt[1] + py * 6 - uy * 1.2)]
    return dict(handle=handle, head=head)


def pick_svg(p, animated):
    out = []
    for key, fill, stroke in (("handle", "wood", "fg"), ("head", "blade", "fg")):
        pts = pick_parts(POSES[animated.keys[0][1]])[key]
        out.append(f'<polygon points="{poly_str(pts)}" fill="{p[fill]}" stroke="{p[stroke]}" stroke-width="0.7" stroke-linejoin="round">'
                   + animate("points", animated, lambda nm, key=key: poly_str(pick_parts(POSES[nm])[key])) + "</polygon>")
    return "".join(out)


def figure_static(P, colour, width=2.6):
    out = [f'<circle r="5" fill="{colour}" cx="{n(P["H"][0])}" cy="{n(P["H"][1])}"/>']
    for limb in LIMBS:
        out.append(f'<polyline fill="none" stroke="{colour}" stroke-width="{width}" stroke-linecap="round" '
                   f'stroke-linejoin="round" points="{limb_str(P, limb)}"/>')
    return "".join(out)


# ---------------------------------------------------------------- characters
class Char:
    def __init__(self, pose0="stand", pos0=(0, 0), face0=1):
        self.pos = Track(tuple(map(float, pos0)))
        self.rot = Track((0.0, 0.0, float(BODY_Y)))
        self.sx = Track(face0)
        self.sq = Track((1.0, 1.0))
        self.op = Track(0)
        self.pz = Track(pose0)
        self.wop = Track(0)
        self.pop = Track(0)
        self.lop = {}            # per-limb opacity tracks (only used by the "outside" copy)

    def limbs_out(self, t, names):
        """From t on, these limbs are in front of the page. names: 'H', 'torso', 'LA', 'RA', 'LL', 'RL'."""
        for nm in names:
            self.lop.setdefault(nm, Track(0)).set(t, 1)

    def at(self, t, x, y, ease="lin"):
        self.pos.add(t, (float(x), float(y)), ease)

    def stay(self, t):
        self.pos.hold(t)

    def put(self, t, x, y):
        self.pos.set(t, (float(x), float(y)))

    def x(self, t=None):
        return self.pos.v[0] if t is None else eval_num(self.pos, t)[0]

    def jump(self, t0, t1, x1, y1, h, step=0.04):
        self.pos.hold(t0)
        x0, y0 = self.pos.v
        k = max(4, int(round((t1 - t0) / step)))
        for i in range(1, k + 1):
            s = i / k
            self.pos.add(t0 + (t1 - t0) * s, (x0 + (x1 - x0) * s, y0 + (y1 - y0) * s - 4 * h * s * (1 - s)))

    def run(self, t0, t1, x1, frame=0.06, ease="lin"):
        self.pos.hold(t0)
        x0, y = self.pos.v
        t, i = t0, 0
        while t < t1 - 1e-6:
            self.pose(t, RUN_CYCLE[i % 6], tween=frame * 0.95, ease="inout")
            t += frame
            i += 1
            tt = min(t, t1)
            sx = eased((tt - t0) / (t1 - t0), ease)
            self.pos.add(tt, (x0 + (float(x1) - x0) * sx, y + RUN_BOB[i % 6]))
        self.pos.add(t1 + EPS, (float(x1), y))

    def jitter(self, t0, t1, amp, hz=24, amp1=None):
        """Shake in place. amp1 lets the shake grow (or shrink) over the interval."""
        self.pos.hold(t0)
        x, y = self.pos.v
        t, i = t0, 0
        while t < t1 - 1 / hz:
            t += 1 / hz
            i += 1
            a = amp if amp1 is None else amp + (amp1 - amp) * (t - t0) / (t1 - t0)
            self.pos.add(t, (x + a * (rnd(i * 3.1) - 0.5) * 2, y + a * 0.5 * (rnd(i * 7.7) - 0.5) * 2))
        self.pos.add(t1, (x, y))

    def pose(self, t, name, tween=0.08, ease="out"):
        assert name in POSES, name
        self.pz.hold(t - tween)
        self.pz.add(t, name, ease)

    def idle(self, t0, t1, base="stand", period=0.5):
        t, i = t0, 0
        while t < t1 - 1e-6:
            self.pose(t, base if i % 2 == 0 else base + "_b", tween=period * 0.9, ease="inout")
            t += period
            i += 1

    def face(self, t, d):
        self.sx.set(t, d)

    def spin(self, t0, t1, deg, ease="lin"):
        self.rot.hold(t0)
        a, px, py = self.rot.v
        end = a + deg
        self.rot.add(t1, (end, px, py), ease)
        self.rot.add(t1 + EPS, (((end + 180) % 360) - 180, px, py))

    def rot_to(self, t0, t1, a, ease="out", pivot=None):
        self.rot.hold(t0)
        _, px, py = self.rot.v
        if pivot is not None:
            px, py = pivot
            self.rot.add(t0 + EPS, (self.rot.v[0], float(px), float(py)))
        self.rot.add(t1, (float(a), px, py), ease)

    def rot_pivot(self, t, px=0.0, py=float(BODY_Y)):
        self.rot.hold(t)
        self.rot.add(t + EPS, (self.rot.v[0], float(px), float(py)))

    def wobble(self, t0, t1, deg, period=0.16, base=None):
        """Rock back and forth around the current (or given) angle."""
        self.rot.hold(t0)
        a0, px, py = self.rot.v
        if base is not None:
            a0 = base
        t, i = t0, 0
        while t < t1 - period / 2:
            t += period / 2
            i += 1
            self.rot.add(t, (a0 + (deg if i % 2 else -deg), px, py), "inout")
        self.rot.add(t1, (a0, px, py), "inout")

    def land(self, t, amount=0.26, pose="crouch"):
        self.sq.set(t, (1 + amount, 1 - amount))
        self.sq.add(t + 0.09, (0.95, 1.05), "out")
        self.sq.add(t + 0.17, (1.0, 1.0), "out")
        if pose:
            self.pose(t, pose, tween=0.03)

    def takeoff(self, t, amount=0.12):
        self.sq.hold(t - 0.05)
        self.sq.add(t, (1 - amount, 1 + amount), "out")
        self.sq.add(t + 0.1, (1.0, 1.0), "out")

    def hitstop(self, t, dur):
        for tr in (self.pos, self.rot, self.pz, self.sq):
            tr.hold(t)
            tr.hold(t + dur)

    def show(self, t):
        self.op.set(t, 1)

    def hide(self, t):
        self.op.set(t, 0)

    def weapon(self, t, on):
        self.wop.set(t, 1 if on else 0)

    def pick(self, t, on):
        self.pop.set(t, 1 if on else 0)

    def world(self, t, key):
        P = eval_pose(self.pz, t)
        x, y = pose_pt(P, key)
        sx = eval_step(self.sx, t)
        sqx, sqy = eval_num(self.sq, t)
        x, y = x * sx * sqx, y * sqy
        a, px, py = eval_num(self.rot, t)
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        dx, dy = x - px, y - py
        x, y = px + dx * ca - dy * sa, py + dx * sa + dy * ca
        X, Y = eval_num(self.pos, t)
        return X + x, Y + y

    def head_mark(self, t):
        hx, hy = self.world(t, "H")
        return hx, hy - 15

    def pose_at(self, t):
        return eval_pose(self.pz, t)

    def svg(self, colour, weapons=None, op_track=None, katana_win=(0, T), pick_win=(0, T), limb_ops=False, halo=None):
        """weapons: the palette dict when this character carries the katana / pickaxe.
        limb_ops: wrap each limb in its own opacity group driven by self.lop.
        halo: a colour; draws a thick knockout outline under the figure so it stays readable over busy linework."""
        op = op_track or self.op
        LIMB_NAMES = {("N", "P"): "torso", ("N", "LE", "LH"): "LA", ("N", "RE", "RH"): "RA", ("P", "LK", "LF"): "LL", ("P", "RK", "RF"): "RL"}

        def wrap(name, inner):
            if not limb_ops:
                return inner
            tr = self.lop.get(name, Track(0))
            return '<g opacity="0">' + animate("opacity", tr, str) + inner + "</g>"
        times = sorted({k[0] for k in self.sx.keys} | {k[0] for k in self.sq.keys})
        sc = Track((float(self.sx.keys[0][1]), 1.0))
        for tt in times:
            if tt == 0:
                continue
            s = eval_step(self.sx, tt)
            qx, qy = eval_num(self.sq, tt)
            sc.add(tt, (s * qx, qy))
        p0 = POSES[self.pz.keys[0][1]]
        out = [f'<g opacity="{op.keys[0][1]}">', animate("opacity", op, str), animate_tf("translate", self.pos, f_xy),
               "<g>", animate_tf("rotate", self.rot, f_rot), "<g>", animate_tf("scale", sc, lambda v: f"{f_s(v[0])} {f_s(v[1])}"),
               ]
        head_anim = animate("cx", self.pz, lambda nm: n(POSES[nm]["H"][0])) + animate("cy", self.pz, lambda nm: n(POSES[nm]["H"][1]))

        def body(col, width, r):
            parts = [wrap("H", f'<circle r="{r}" fill="{col}" cx="{n(p0["H"][0])}" cy="{n(p0["H"][1])}">' + head_anim + "</circle>")]
            for limb in LIMBS:
                parts.append(wrap(LIMB_NAMES[limb], f'<polyline fill="none" stroke="{col}" stroke-width="{width}" stroke-linecap="round" '
                                  f'stroke-linejoin="round" points="{limb_str(p0, limb)}">'
                                  + animate("points", self.pz, lambda nm, limb=limb: limb_str(POSES[nm], limb)) + "</polyline>"))
            return "".join(parts)
        if halo:
            out.append(body(halo, 5.4, 6.4))      # knockout pass, all limbs, under everything
        out.append(body(colour, 2.6, 5))
        if weapons:
            kz, pz = window_track(self.pz, *katana_win), window_track(self.pz, *pick_win)
            out.append('<g opacity="0">' + animate("opacity", self.wop, str) + katana_svg(katana_parts(POSES[kz.keys[0][1]]), weapons, animated=kz) + "</g>")
            out.append('<g opacity="0">' + animate("opacity", self.pop, str) + pick_svg(weapons, pz) + "</g>")
        out.append("</g></g></g>")
        return "".join(out)


# ---------------------------------------------------------------- words
class Word:
    def __init__(self, text, x, y, w, size=16, fixed_width=True, strike=False, bold=False):
        self.text, self.x, self.y, self.w, self.size, self.fixed = text, x, y, w, size, fixed_width
        self.strike, self.bold = strike, bold
        self.cx, self.cy = x + w / 2, y - size * 0.33
        self.tr, self.rot, self.op = Track((0.0, 0.0)), Track(0.0), Track(1)
        self.animated = False
        self.halves = None
        self.clip = None

    def shake(self, t0, t1, amp, hz=28):
        """Shiver in place, around wherever the word currently is."""
        self.animated = True
        self.tr.hold(t0)
        bx, by = self.tr.v
        t, i = t0, 0
        while t < t1 - 1 / hz:
            t += 1 / hz
            i += 1
            self.tr.add(t, (bx + amp * (1 if i % 2 else -1), by + amp * 0.4 * (1 if (i // 2) % 2 else -1)))
        self.tr.add(t1, (bx, by))

    def fly(self, t0, t1, lx, ly, rot, h, bounce=None):
        self.animated = True
        self.tr.hold(t0)
        self.rot.hold(t0)
        dx, dy = self.tr.v
        x0, y0, r0 = self.cx + dx, self.cy + dy, self.rot.v
        k = max(5, int(round((t1 - t0) / 0.04)))
        for i in range(1, k + 1):
            s = i / k
            x, y = x0 + (lx - x0) * s, y0 + (ly - y0) * s - 4 * h * s * (1 - s)
            self.tr.add(t0 + (t1 - t0) * s, (x - self.cx, y - self.cy))
            self.rot.add(t0 + (t1 - t0) * s, r0 + rot * s)
        if bounce:
            bx, bt, bh = bounce
            r0 = self.rot.v
            for i in range(1, 6):
                s = i / 5
                self.tr.add(t1 + bt * s, (lx + bx * s - self.cx, ly - 4 * bh * s * (1 - s) - self.cy))
                self.rot.add(t1 + bt * s, r0 + 12 * s)

    def dip(self, t, d=5):
        self.animated = True
        self.tr.hold(t)
        self.tr.add(t + 0.07, (0.0, d), "out")
        self.tr.add(t + 0.18, (0.0, -2.0), "inout")
        self.tr.add(t + 0.3, (0.0, 0.0), "inout")

    def restore(self, t0, t1):
        self.tr.hold(t0)
        self.rot.hold(t0)
        self.tr.add(t1, (0.0, 0.0), "inout")
        self.rot.add(t1, 0.0, "inout")

    def slice(self, t, angle, fall=((-26, 70), (24, -120)), through=None):
        """Cut along a line at `angle` degrees. `through` is a page point the line passes through
        (where the blade actually crossed the word); defaults to the word's centre."""
        self.animated = True
        self.op.set(t, 0)
        a = math.radians(angle)
        d, nn = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))
        self.halves = []
        c = through if through else (self.cx, self.cy)
        for sgn, (ddx, drot) in zip((1, -1), fall):
            hw = Word(self.text, self.x, self.y, self.w, self.size, self.fixed, bold=self.bold)
            hw.op = Track(0)
            hw.op.set(t, 1)
            L = 120
            hw.clip = [(c[0] + d[0] * L, c[1] + d[1] * L), (c[0] - d[0] * L, c[1] - d[1] * L),
                       (c[0] - d[0] * L + sgn * nn[0] * L, c[1] - d[1] * L + sgn * nn[1] * L),
                       (c[0] + d[0] * L + sgn * nn[0] * L, c[1] + d[1] * L + sgn * nn[1] * L)]
            hw.animated = True
            hw.tr.hold(t)
            hw.tr.add(t + 0.1, (sgn * nn[0] * 5, sgn * nn[1] * 5), "out")
            hw.rot.hold(t + 0.1)
            x0, y0 = self.cx + sgn * nn[0] * 5, self.cy + sgn * nn[1] * 5
            lx, ly = self.cx + ddx, FLOOR - 7
            dur = 0.42 + 0.18 * (1 - self.cy / 300)
            for i in range(1, 11):
                s = i / 10
                hw.tr.add(t + 0.1 + dur * s, (x0 + (lx - x0) * s - self.cx, y0 + (ly - y0) * (s * s) - self.cy))
                hw.rot.add(t + 0.1 + dur * s, drot * s)
            self.halves.append(hw)

    def _text(self, fg):
        tl = f' textLength="{n(self.w)}"' if self.fixed else ""
        st = ' text-decoration="line-through"' if self.strike else ""
        fw = ' font-weight="700"' if self.bold else ""
        return (f'<text x="{n(self.x)}" y="{n(self.y)}" font-size="{self.size}" fill="{fg}"{tl}{st}{fw}>'
                f'{html.escape(self.text)}</text>')

    def svg(self, fg):
        text = self._text(fg)
        if not self.animated:
            return text
        clip = ""
        if self.clip:
            cid = "cut-" + hashlib.sha256(repr((self.text, self.x, self.clip[2])).encode("utf-8")).hexdigest()[:16]
            pts = " ".join(f"{n(x)},{n(y)}" for x, y in self.clip)
            clip = f'<clipPath id="{cid}"><polygon points="{pts}"/></clipPath>'
            text = f'<g clip-path="url(#{cid})">{text}</g>'
        return (f'{clip}<g opacity="{self.op.keys[0][1]}">' + animate("opacity", self.op, str)
                + animate_tf("translate", self.tr, f_xy) + "<g>"
                + animate_tf("rotate", self.rot, lambda a: f"{n(a)} {n(self.cx)} {n(self.cy)}")
                + text + "</g></g>")

    def all_svg(self, fg):
        return self.svg(fg) + ("".join(h.svg(fg) for h in self.halves) if self.halves else "")

    def plain(self, fg):
        return self._text(fg)


def layout(text, y):
    words, x, sp = [], 0.0, FONT.getlength(" ")
    for tok in text.split(" "):
        strike = tok.startswith("~~") and tok.endswith("~~")
        bold = tok.startswith("**") and tok.endswith("**")
        tok = tok.strip("~").strip("*")
        w = (FONT_B if bold else FONT).getlength(tok)
        words.append(Word(tok, x, y, w, strike=strike, bold=bold))
        x += w + sp
    return words


LINES = [layout(p, P_Y[i]) for i, p in enumerate(PARAS)]
ALL_WORDS = [wd for line in LINES for wd in line]


def word(line, text):
    for wd in LINES[line]:
        if wd.text == text:
            return wd
    raise KeyError(text)


_kicked = word(*WORD_TARGETS["kick"])
NL, _x = [], _kicked.x
for ch in _kicked.text:
    cw = FONT.getlength(ch)
    NL.append(Word(ch, _x, _kicked.y, cw, fixed_width=False))
    _x += cw
LINES[3] = [wd for wd in LINES[3] if wd is not _kicked]
RD = word(*WORD_TARGETS["hole"])
LINES[3] = [wd for wd in LINES[3] if wd is not RD]
S1, S2, S3 = (word(*WORD_TARGETS[name]) for name in ("low", "middle", "high"))
IX, IY = RD.cx + 4, RD.cy + 1          # where the first crack starts

# ---------------------------------------------------------------- effect library
LAYERS = {k: [] for k in ("cracks", "debris", "props", "fx_low", "fx_mid", "over_red", "fx_high", "marks", "top")}


def layer(name, fn):
    LAYERS[name].append(fn)


def polyline_len(pts):
    return sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1))


def path_d(pts):
    return "M" + " L".join(f"{n(x)},{n(y)}" for x, y in pts)


def point_along(pts, f):
    total = polyline_len(pts)
    target = total * f
    for i in range(len(pts) - 1):
        seg = math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        if target <= seg or i == len(pts) - 2:
            s = max(0, min(1, target / seg)) if seg else 0
            return (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * s, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * s)
        target -= seg
    return pts[-1]


def grow(d, L, w, t0, dur):
    """A path that draws itself from its start over `dur` seconds (dash-offset trick)."""
    off = Track(L + 2 * w)
    off.hold(t0)
    off.add(t0 + dur, 0.0, "out")
    return (f'<path d="{d}" stroke-width="{n(w)}" stroke-dasharray="{n(L + w)} {n(L + 3 * w)}" stroke-dashoffset="{n(L + 2 * w)}">'
            + animate("stroke-dashoffset", off, n) + "</path>")


def crack_set(cx, cy, R, count, seed, span=(0, 2 * math.pi), yscale=0.72, rings=(), t_show=0.0,
              prop=0.1, width=1.0, colour="fg", alpha=1.0):
    radials = []
    for i in range(count):
        base = span[0] + (span[1] - span[0]) * (i + 0.5) / count + (rnd(seed + i) - 0.5) * 0.25
        L = R * (0.6 + 0.4 * rnd(seed * 3 + i))
        pts, ang = [(cx, cy)], base
        for k in range(1, 6):
            ang += (rnd(seed * 7 + i * 5 + k) - 0.5) * 0.4
            r = L * k / 5
            pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang) * yscale))
        radials.append(pts)
    paths = []
    for i, pts in enumerate(radials):
        L = polyline_len(pts)
        paths.append(grow(path_d(pts), L, width, t_show, prop))
        thick = pts[:3]
        paths.append(grow(path_d(thick), polyline_len(thick), width * 2.1, t_show, prop * 0.5))
        if rnd(seed * 11 + i) < 0.65:
            bx, by = pts[3]
            ang = math.atan2((pts[4][1] - by) / yscale, pts[4][0] - bx) + (0.8 if i % 2 else -0.8)
            fl = L * 0.28
            fork = [(bx, by), (bx + fl * 0.5 * math.cos(ang), by + fl * 0.5 * math.sin(ang) * yscale),
                    (bx + fl * math.cos(ang + 0.3), by + fl * math.sin(ang + 0.3) * yscale)]
            paths.append(grow(path_d(fork), polyline_len(fork), width * 0.8, t_show + prop * 0.6, prop * 0.5))
    ring_paths = []
    full = (span[1] - span[0]) > 6
    for f in rings:
        for i in range(len(radials)):
            if not full and i == len(radials) - 1:
                continue
            if rnd(seed * 13 + i + f * 100) < 0.22:
                continue
            a, b = radials[i], radials[(i + 1) % len(radials)]
            fa = min(0.98, f + (rnd(seed + i * 2) - 0.5) * 0.12)
            fb = min(0.98, f + (rnd(seed + i * 2 + 1) - 0.5) * 0.12)
            pa, pb = point_along(a, fa), point_along(b, fb)
            mx = (pa[0] + pb[0]) / 2 + (rnd(i * 9 + seed) - 0.5) * 6
            my = (pa[1] + pb[1]) / 2 + (rnd(i * 4 + seed) - 0.5) * 4
            ring_paths.append(f'<path d="{path_d([pa, (mx, my), pb])}" stroke-width="{n(width * 0.75)}"/>')

    def svg(p):
        op = Track(alpha)
        op.hold(FADE[0])
        op.add(FADE[1], 0, "in")
        rop = Track(0)
        rop.set(t_show + prop, 0.8 * alpha)
        rop.hold(FADE[0])
        rop.add(FADE[1], 0, "in")
        out = (f'<g fill="none" stroke="{p[colour]}" stroke-linecap="round" stroke-linejoin="round" opacity="{alpha}">'
               + animate("opacity", op, str) + "".join(paths) + "</g>")
        if ring_paths:
            out += (f'<g fill="none" stroke="{p[colour]}" stroke-linecap="round" opacity="0">'
                    + animate("opacity", rop, str) + "".join(ring_paths) + "</g>")
        return out
    return svg, radials


def spark(x, y, t, size, kind="spark", dur=0.26, lay="fx_high"):
    """Impact: a thin shockwave ring that expands and fades, and a few sharp lines that shoot
    outward and shrink. Ink only, no fill. kind="white" is a glint (sword, blocks): a small cross."""
    def svg(p):
        col = p["fg"] if kind != "bg" else p["bg"]
        op = Track(0)
        op.set(t, 1)
        op.hold(t + dur * 0.35)
        op.add(t + dur, 0, "in")
        out = [f'<g transform="translate({n(x)},{n(y)})"><g opacity="0">', animate("opacity", op, str)]
        if kind == "white":
            sc = Track(0.2)
            sc.hold(t)
            sc.add(t + dur * 0.35, 1.0, "out")
            sc.add(t + dur, 0.5, "in")
            rot = Track(0.0)
            rot.hold(t)
            rot.add(t + dur, 40.0, "out")
            L = size * 1.6
            out.append("<g>" + animate_tf("rotate", rot, lambda a: f"{n(a)} 0 0") + "<g>" + animate_tf("scale", sc, f_ss)
                       + f'<path d="M{n(-L)},0 H{n(L)} M0,{n(-L)} V{n(L)} M{n(-L * .45)},{n(-L * .45)} L{n(L * .45)},{n(L * .45)} M{n(-L * .45)},{n(L * .45)} L{n(L * .45)},{n(-L * .45)}" '
                       f'stroke="{col}" stroke-width="1.3" stroke-linecap="round"/></g></g>')
        else:
            rr = Track(size * 0.3)
            rr.hold(t)
            rr.add(t + dur, size * 2.6, "out")
            sw = Track(2.4)
            sw.hold(t)
            sw.add(t + dur, 0.3, "out")
            out.append(f'<circle r="{n(size * .3)}" fill="none" stroke="{col}" stroke-width="2.4">' + animate("r", rr, n) + animate("stroke-width", sw, n) + "</circle>")
            cnt = 7
            for i in range(cnt):
                a = i * 2 * math.pi / cnt + rnd(i * 3 + size) * 0.5
                r0, L = size * 0.6, size * (1.0 + 0.9 * rnd(i + size))
                push = size * (2.2 + 1.2 * rnd(i * 7 + size))
                ux, uy = math.cos(a), math.sin(a)
                pts = Track((r0, r0 + L))
                pts.hold(t)
                pts.add(t + dur * 0.9, (r0 + push, r0 + push + L * 0.15), "out")
                out.append(f'<polyline fill="none" stroke="{col}" stroke-width="{n(1.0 + 0.8 * rnd(i + 2))}" stroke-linecap="round" points="{n(r0 * ux)},{n(r0 * uy)} {n((r0 + L) * ux)},{n((r0 + L) * uy)}">'
                           + animate("points", pts, lambda v, ux=ux, uy=uy: f"{n(v[0] * ux)},{n(v[0] * uy)} {n(v[1] * ux)},{n(v[1] * uy)}") + "</polyline>")
        out.append("</g></g>")
        return "".join(out)
    layer(lay, svg)


def dust(x, y, t, big=False, up=False):
    def svg(p):
        out = []
        if up:
            pts = [(-3, -14), (2, -17), (-1, -22)]
        else:
            pts = [(-18, -6), (-10, -13), (-2, -16), (6, -15), (14, -11), (20, -5)] if big else [(-12, -5), (-5, -10), (5, -10), (12, -5)]
        for i, (dx, dy) in enumerate(pts):
            tr = Track((0.0, 0.0))
            tr.set(t, (0.0, 0.0))
            tr.add(t + 0.32, (dx * 1.3, dy * 1.2), "out")
            op = Track(0)
            op.set(t, 0.75)
            op.add(t + 0.32, 0, "in")
            r = 1.8 + 0.6 * rnd(i + t)
            out.append(f'<g transform="translate({n(x)},{n(y)})"><circle r="{n(r)}" fill="{p["smoke"]}" opacity="0">'
                       + animate("opacity", op, str) + animate_tf("translate", tr, f_xy) + "</circle></g>")
        return "".join(out)
    layer("fx_low", svg)


def poof(x, y, t, size=1.0):
    def svg(p):
        out = []
        for i in range(7):
            a = i * 2 * math.pi / 7 + rnd(i + t) * 0.5
            d = (9 + 7 * rnd(i * 3 + t)) * size
            tr = Track((0.0, 0.0))
            tr.set(t, (0.0, 0.0))
            tr.add(t + 0.36, (d * math.cos(a), d * math.sin(a) * 0.7 - 4), "out")
            op = Track(0)
            op.set(t, 0.9)
            op.hold(t + 0.12)
            op.add(t + 0.36, 0, "in")
            sc = Track(0.4)
            sc.hold(t)
            sc.add(t + 0.15, 1.0, "out")
            sc.add(t + 0.36, 1.3)
            r = (4 + 2.5 * rnd(i * 5 + t)) * size
            out.append(f'<g transform="translate({n(x)},{n(y)})"><g opacity="0">' + animate("opacity", op, str)
                       + animate_tf("translate", tr, f_xy) + "<g>" + animate_tf("scale", sc, f_ss)
                       + f'<circle r="{n(r)}" fill="{p["smoke"]}"/></g></g></g>')
        return "".join(out)
    layer("fx_mid", svg)


def speed_lines(x, t0, t1, y0=-6, y1=36, horizontal=False):
    def svg(p):
        op = Track(0)
        op.set(t0, 0.55)
        op.hold(t0 + (t1 - t0) * 0.5)
        op.add(t1, 0, "in")
        if horizontal:
            lines = "".join(f'<path d="M{n(x + dx)},{n(y0 + dy)} h{n(ln)}"/>' for dx, dy, ln in [(0, -24, -40), (-8, -16, -60), (2, -8, -46)])
        else:
            lines = "".join(f'<path d="M{n(x + dx)},{n(a)} V{n(b)}"/>' for dx, a, b in [(-8, y0 + 4, y1 - 10), (0, y0, y1), (8, y0 + 6, y1 - 12)])
        return f'<g opacity="0" stroke="{p["fg"]}" stroke-width="2" stroke-linecap="round">' + animate("opacity", op, str) + lines + "</g>"
    layer("fx_low", svg)


def crescent(cx, cy, r_out, a0, a1, t, dur=0.1):
    r_in = r_out * 0.55

    def svg(p):
        op = Track(0)
        op.set(t, 0.45)
        op.add(t + dur, 0, "in")
        sc = Track(0.8)
        sc.hold(t)
        sc.add(t + dur, 1.1, "out")
        A0, A1 = math.radians(a0), math.radians(a1)
        big = 1 if abs(A1 - A0) > math.pi else 0
        sweep = 1 if A1 > A0 else 0
        d = (f"M{n(r_out * math.cos(A0))},{n(r_out * math.sin(A0))} A{n(r_out)},{n(r_out)} 0 {big} {sweep} "
             f"{n(r_out * math.cos(A1))},{n(r_out * math.sin(A1))} L{n(r_in * math.cos(A1))},{n(r_in * math.sin(A1))} "
             f"A{n(r_in)},{n(r_in)} 0 {big} {1 - sweep} {n(r_in * math.cos(A0))},{n(r_in * math.sin(A0))} Z")
        return (f'<g transform="translate({n(cx)},{n(cy)})"><g opacity="0">' + animate("opacity", op, str)
                + animate_tf("scale", sc, f_ss) + f'<path d="{d}" fill="{p["fg"]}"/></g></g>')
    layer("fx_high", svg)


def smear_line(x0, y0, x1, y1, t, width=5, dur=0.07, colour="fg"):
    def svg(p):
        op = Track(0)
        op.set(t, 0.5)
        op.add(t + dur, 0, "in")
        return (f'<path d="M{n(x0)},{n(y0)} L{n(x1)},{n(y1)}" stroke="{p[colour]}" stroke-width="{width}" stroke-linecap="round" opacity="0">'
                + animate("opacity", op, str) + "</path>")
    layer("fx_high", svg)


def impact_lines(x, y, t, big=True, colour="fg"):
    """The impact frame: thin radial speed lines from the hit point to the edges, for two frames."""
    if not big:
        return

    def svg(p):
        op = Track(0)
        op.set(t, 0.75)
        op.hold(t + 0.04)
        op.add(t + 0.1, 0, "in")
        lines = []
        for i in range(22):
            a = i * 2 * math.pi / 22 + rnd(i + t) * 0.22
            r0 = 34 + 26 * rnd(i * 2 + t)
            r1 = r0 + 90 + 160 * rnd(i * 3 + t)
            lines.append(f'<path d="M{n(x + r0 * math.cos(a))},{n(y + r0 * math.sin(a))} L{n(x + r1 * math.cos(a))},{n(y + r1 * math.sin(a))}" stroke-width="{n(0.6 + 1.0 * rnd(i + 9))}"/>')
        return f'<g opacity="0" stroke="{p[colour]}" stroke-linecap="round">' + animate("opacity", op, str) + "".join(lines) + "</g>"
    layer("fx_high", svg)


def flash(t, dur=0.06, amount=0.7, colour="flash"):
    def svg(p):
        op = Track(0)
        op.set(t, amount)
        op.hold(t + dur * 0.5)
        op.add(t + dur, 0, "in")
        return f'<rect width="{W}" height="{H}" fill="{p[colour]}" opacity="0">' + animate("opacity", op, str) + "</rect>"
    layer("top", svg)


def mark(txt, x, y, t, dur=0.5):
    def svg(p):
        op = Track(0)
        op.set(t, 1)
        op.hold(t + dur * 0.7)
        op.add(t + dur, 0, "in")
        sc = Track(0.3)
        sc.hold(t)
        sc.add(t + 0.1, 1.25, "out")
        sc.add(t + 0.2, 1.0, "inout")
        return (f'<g transform="translate({n(x)},{n(y)})"><g opacity="0">' + animate("opacity", op, str)
                + animate_tf("scale", sc, f_ss)
                + f'<text text-anchor="middle" font-size="15" font-weight="700" fill="{p["fg"]}" y="5">{html.escape(txt)}</text></g></g>')
    layer("marks", svg)


def blink(x, y, t):
    def svg(p):
        op = Track(0)
        op.set(t, 0.9)
        op.add(t + 0.14, 0, "in")
        sc = Track((1.0, 0.2))
        sc.hold(t)
        sc.add(t + 0.06, (1.0, 1.0), "out")
        sc.add(t + 0.14, (0.1, 1.1), "in")
        return (f'<g transform="translate({n(x)},{n(y - 18)})"><g opacity="0">' + animate("opacity", op, str)
                + animate_tf("scale", sc, lambda v: f"{f_s(v[0])} {f_s(v[1])}")
                + f'<ellipse rx="5" ry="26" fill="{p["void_fg"]}" stroke="{p["fg"]}" stroke-width="1.2"/></g></g>')
    layer("fx_high", svg)


def ghost(P, x, y, face, t, colour_key, dur=0.18, drift=(0, 0), alpha=0.45, rot=0.0):
    def svg(p):
        op = Track(0)
        op.set(t, alpha)
        op.add(t + dur, 0, "in")
        tr = Track((0.0, 0.0))
        tr.set(t, (0.0, 0.0))
        tr.add(t + dur, drift, "out")
        return (f'<g transform="translate({n(x)},{n(y)})"><g opacity="0">' + animate("opacity", op, str)
                + animate_tf("translate", tr, f_xy) + f'<g transform="rotate({n(rot)} 0 {BODY_Y}) scale({face},1)">'
                + figure_static(P, p[colour_key]) + "</g></g></g>")
    layer("fx_mid", svg)


def teleport(c, t, x1, y1, face1, colour_key):
    P = c.pose_at(t - 0.01)
    x0, y0 = eval_num(c.pos, t - 0.01)
    face0 = eval_step(c.sx, t - 0.01)
    for k in range(1, 4):
        s = k / 4
        ghost(P, x0 + (x1 - x0) * s, y0 + (y1 - y0) * s, face0, t + 0.025 * k, colour_key,
              drift=((x1 - x0) * 0.06, (y1 - y0) * 0.06), alpha=0.5 - 0.1 * k)
    blink(x0, y0, t)
    c.hide(t)
    blink(x1, y1, t + 0.1)
    c.put(t + 0.12, x1, y1)
    c.face(t + 0.12, face1)
    c.show(t + 0.12)


def trail(c, t0, t1, colour_key, k=4):
    """Afterimages left behind a fast move between t0 and t1."""
    for i in range(k):
        tt = t0 + (t1 - t0) * (i + 1) / (k + 1)
        x, y = eval_num(c.pos, tt)
        P = c.pose_at(tt)
        ghost(P, x, y, eval_step(c.sx, tt), tt, colour_key, dur=0.2, alpha=0.35, rot=eval_num(c.rot, tt)[0])


FRAME = Track((0.0, 0.0))


def jolt(t, amp):
    FRAME.hold(t - EPS)
    for dt, fx, fy in [(0.03, 1, -0.6), (0.07, -0.7, 0.5), (0.11, 0.4, -0.3), (0.16, 0, 0)]:
        FRAME.add(t + dt, (amp * fx, amp * fy), "out")


def rumble(t0, t1, amp0, amp1):
    FRAME.hold(t0)
    t, i = t0, 0
    while t < t1 - 0.04:
        t += 0.04
        i += 1
        a = amp0 + (amp1 - amp0) * (t - t0) / (t1 - t0)
        FRAME.add(t, (a * (rnd(i * 5.3) - 0.5) * 2, a * (rnd(i * 9.1) - 0.5) * 2))
    FRAME.add(t1, (0.0, 0.0))


def hit(t, x, y, size, *chars, big=False, dur=None, shake=None):
    dur = dur or (0.09 if big else 0.06)
    spark(x, y, t, size)
    for c in chars:
        c.hitstop(t, dur)
    if big:
        impact_lines(x, y, t)
        flash(t, 0.07, 0.75)
    jolt(t, shake if shake is not None else (3 if big else 1.5))
    return t + dur


def heavy_slash(c, t_contact, big=True):
    """A committed overhead cut. Wind-up (slow), raise, cut (snap), carry through, slow recovery.
    Returns nothing; the caller places the crescent and the cut at t_contact."""
    c.pose(t_contact - 0.30, "sw_wind", 0.16, "inout")
    c.pose(t_contact - 0.09, "sw_up", 0.13, "in")
    c.pose(t_contact, "sw_down", 0.045, "snap")
    c.pose(t_contact + 0.07, "sw_thru", 0.07, "out")
    c.sq.hold(t_contact - 0.001)
    c.sq.add(t_contact + 0.05, (1.08, 0.94), "out")      # weight drops into the cut
    c.sq.add(t_contact + 0.22, (1.0, 1.0), "inout")
    c.pose(t_contact + 0.3, "sw_rec", 0.2, "inout")
    c.pose(t_contact + 0.55, "sw_idle", 0.22, "inout")
    if big:
        jolt(t_contact, 1.2)


def heavy_upswing(c, t_contact):
    """A rising cut. Blade low and back, then it sweeps up and forward through the target and ends
    high overhead, which is exactly the wind-up of the next overhead cut. Contact lands mid-sweep."""
    c.pose(t_contact - 0.28, "sw_low", 0.16, "inout")
    c.pose(t_contact + 0.04, "sw_upcut", 0.1, "snap")
    c.pose(t_contact + 0.14, "sw_upthru", 0.1, "out")
    c.sq.hold(t_contact - 0.001)
    c.sq.add(t_contact + 0.05, (0.94, 1.08), "out")       # he rises into it
    c.sq.add(t_contact + 0.22, (1.0, 1.0), "inout")
    jolt(t_contact, 1.2)


def blade_cut_point(c, t, wd):
    """Where the blade's line (hand -> tip) crosses the word's centre height at time t."""
    (hx, hy), (tx, ty) = c.world(t, "RH"), c.world(t, "WT")
    if abs(ty - hy) < 1e-6:
        return (tx, wd.cy)
    k = (wd.cy - hy) / (ty - hy)
    return (hx + (tx - hx) * k, wd.cy)


def hop(c, t0, t1, x, y, h=14, land_amt=0.22):
    c.pose(t0 - 0.06, "crouch", 0.06)
    c.takeoff(t0)
    c.jump(t0, t1, x, y, h)
    c.pose(t0 + 0.05, "tuck", 0.05)
    c.pose(t1 - 0.06, "fall", 0.06)
    c.land(t1, land_amt)


# ================================================================ cast
ink = Char("fall", (400, -45))
red = Char("stand", (0, 0))
crawl = Char("stand", (0, 0))     # Red while he is climbing out through the hole
c1, c2, c3 = Char("stand", (0, 0)), Char("stand", (0, 0)), Char("stand", (0, 0))
# ================================================================ ACT 1  break-in  (0.9 - 4.6)
stage1, _ = crack_set(IX, IY, 16, 3, seed=2, t_show=0.9, prop=0.12, width=0.9, alpha=0.8)
stage2, _ = crack_set(IX, IY, 34, 6, seed=5, t_show=1.3, prop=0.14, width=1.0, alpha=0.8)
stage3, RADS = crack_set(IX, IY, 84, 12, seed=9, rings=(0.62, 0.86), t_show=1.7, prop=0.1, width=1.0, alpha=0.8)
for fn in (stage1, stage2, stage3):
    layer("cracks", fn)
RD.shake(0.9, 1.1, 0.8)
RD.shake(1.3, 1.65, 1.4)
for L in NL:
    L.shake(1.35, 1.65, 0.8)
jolt(0.9, 0.6)
jolt(1.3, 1.0)

HOLE_PTS = [point_along(pts, 0.5 + 0.07 * rnd(i + 40)) for i, pts in enumerate(RADS)]
HX = sum(x for x, _ in HOLE_PTS) / len(HOLE_PTS)
HY = sum(y for _, y in HOLE_PTS) / len(HOLE_PTS)
HT, HB, HR = min(y for _, y in HOLE_PTS), max(y for _, y in HOLE_PTS), max(x for x, _ in HOLE_PTS)
HOLE_SCALE = Track(0.0)
HOLE_SCALE.hold(1.7 - EPS)
HOLE_SCALE.add(1.7, 0.5)
HOLE_SCALE.add(1.76, 1.15, "out")
HOLE_SCALE.add(1.84, 0.96)
HOLE_SCALE.add(1.9, 1.0)
HOLE_SCALE.hold(FADE[0] + 0.2)
HOLE_SCALE.add(FADE[1] + 0.25, 0.0, "in")


def hole_svg(p, edge_only=False):
    pts = " ".join(f"{n(x - HX)},{n(y - HY)}" for x, y in HOLE_PTS)
    paint = 'fill="none"' if edge_only else 'fill="url(#holeg)"'
    return (f'<g transform="translate({n(HX)},{n(HY)})"><g>' + animate_tf("scale", HOLE_SCALE, f_ss)
            + f'<polygon points="{pts}" {paint} stroke="{p["fg"]}" stroke-opacity="0.3" stroke-width="0.8" stroke-linejoin="round"/></g></g>')


def shards_svg(p):
    out = []
    for i in range(len(RADS)):
        a, b = RADS[i], RADS[(i + 1) % len(RADS)]
        f0, f1 = 0.5 + 0.07 * rnd(i + 40), 0.5 + 0.07 * rnd(i + 41)
        quad = [point_along(a, f0), point_along(a, min(0.95, f0 + 0.24 + 0.1 * rnd(i))),
                point_along(b, min(0.95, f1 + 0.2 + 0.1 * rnd(i + 3))), point_along(b, f1)]
        cx = sum(x for x, _ in quad) / 4
        cy = sum(y for _, y in quad) / 4
        ang = math.atan2(cy - IY, cx - IX)
        ux, uy = math.cos(ang), math.sin(ang)
        t = 1.7
        tr, rt, op = Track((0.0, 0.0)), Track(0.0), Track(0)
        tr.set(t, (0.0, 0.0))
        rt.set(t, 0.0)
        op.set(t, 1)
        spd = 70 + 60 * rnd(i * 5 + 1)
        vx, vy = ux * spd, uy * spd * 0.8 - 45
        if i in (1, 4, 7, 10):
            g = 260
            s_land = (-vy + math.sqrt(vy * vy + 4 * g * (FLOOR - 5 - cy))) / (2 * g)
            for j in range(1, 11):
                s = s_land * j / 10
                tr.add(t + s, (vx * s, vy * s + g * s * s))
                rt.add(t + s, (250 if i % 2 else -200) * s / s_land * 0.6)
            x_end = vx * s_land
            tr.add(t + s_land + 0.12, (x_end + 6, FLOOR - 5 - cy - 5), "out")
            rt.add(t + s_land + 0.12, rt.v + 25)
            tr.add(t + s_land + 0.24, (x_end + 10, FLOOR - 5 - cy), "in")
            rt.add(t + s_land + 0.24, rt.v + 10)
            op.hold(FADE[0])
            op.add(FADE[1], 0, "in")
        else:
            for j in range(1, 10):
                s = 0.6 * j / 9
                tr.add(t + s, (vx * s * 1.2, vy * s + 200 * s * s))
                rt.add(t + s, (300 if i % 2 else -260) * s)
            op.hold(t + 0.35)
            op.add(t + 0.6, 0, "in")
        pts = " ".join(f"{n(x)},{n(y)}" for x, y in quad)
        out.append('<g opacity="0">' + animate("opacity", op, str) + animate_tf("translate", tr, f_xy) + "<g>"
                   + animate_tf("rotate", rt, lambda a, cx=cx, cy=cy: f"{n(a)} {n(cx)} {n(cy)}")
                   + f'<polygon points="{pts}" fill="{p["bg"]}" stroke="{p["fg"]}" stroke-width="0.9" stroke-linejoin="round" opacity="0.95"/></g></g>')
    return "".join(out)


layer("debris", shards_svg)
jolt(1.7, 3)
flash(1.7, 0.08, 0.5)
RD.fly(1.7, 2.4, 640, FLOOR - 6, 165, 70, bounce=(16, 0.2, 8))

# Red climbs out of the hole. `peek` is clipped to the hole polygon, so he is only ever seen
# THROUGH the opening. He comes up from deep inside (small and low), looks around, crouches, and at
# that instant the unclipped `red` takes over, entirely inside the hole, and leaps out over the rim.
# 1.9  Red rises up out of the dark, seen through the hole, and climbs out of it like a manhole.
#      `crawl` is drawn twice: clipped to the hole (seen THROUGH the opening) and clipped to the page around
#      it, limb by limb as each limb comes up over the top rim. The page really occludes him.
RIM_X, RIM_Y = HX + 4, HT + 1                 # a point on the flat top rim of the hole
crawl.put(0, RIM_X, RIM_Y + 70)
crawl.sq.set(1.9, (0.5, 0.5))
crawl.show(1.9)
crawl.stay(1.9)
# he swims up out of the dark and grabs the rim with both hands
crawl.pose(2.1, "fall", 0.08)
crawl.at(2.32, RIM_X, RIM_Y, "out")
crawl.sq.add(2.32, (1.0, 1.0), "out")
crawl.pose(2.32, "mh_hang", 0.16, "out")
crawl.limbs_out(2.3, ("LA", "RA"))           # hands on the page
crawl.at(2.42, RIM_X, RIM_Y + 3, "out")      # settles under his weight
crawl.at(2.56, RIM_X, RIM_Y, "inout")
# pull-up. Chin to the rim. A beat of effort.
crawl.pose(2.92, "mh_pull", 0.34, "inout")
crawl.jitter(2.9, 3.02, 0.4, 20)
# press-up. Arms lock, chest comes up above the rim onto the page.
crawl.pose(3.24, "mh_press", 0.28, "inout")
crawl.limbs_out(3.0, ("H", "torso"))
jolt(3.24, 0.4)
# a knee swings up onto the page
crawl.pose(3.56, "mh_knee", 0.3, "inout")
crawl.at(3.56, RIM_X + 4, RIM_Y, "inout")
crawl.limbs_out(3.4, ("RL",))
# and the other leg follows. He is crouched on the page past the rim.
crawl.pose(3.86, "mh_crouch", 0.28, "inout")
crawl.at(3.86, RIM_X + 10, RIM_Y, "inout")
crawl.limbs_out(3.72, ("LL",))
# hand-off to the real character at the exact same spot and pose
crawl.hide(3.86)
red.put(0, RIM_X + 10, RIM_Y)
red.pose(3.86, "mh_crouch", EPS)
red.show(3.86)
# stand up slow, a quick look around, then he hops down off the rim to the floor
red.stay(3.86)
red.at(4.1, RIM_X + 14, RIM_Y, "inout")
red.pose(4.1, "stand", 0.24, "inout")
red.face(4.18, -1)
red.face(4.36, 1)
red.face(4.5, -1)
red.pose(4.56, "crouch", 0.08)
red.takeoff(4.62)
red.jump(4.62, 4.96, HX - 60, FLOOR, 30)
red.pose(4.68, "tuck", 0.05)
red.pose(4.86, "fall", 0.06)
red.land(4.96, 0.26)
dust(HX - 60, FLOOR, 4.96)
# dust off, hands on hips, a breath
red.pose(5.08, "stand", 0.1)
red.pose(5.16, "dust", 0.08)
red.pose(5.26, "dust2", 0.06)
red.pose(5.36, "hips", 0.1)
red.idle(5.36, 5.46, "hips")
# Red jump-kicks "rebuild"
REDX1 = NL[0].x - 8
red.pose(5.46, "crouch", 0.05)
red.takeoff(5.5)
red.jump(5.5, 5.76, REDX1, FLOOR, 40)
red.pose(5.54, "tuck", 0.05)
red.pose(5.62, "kick", 0.05)
KX, KY = red.world(5.64, "RF")
spark(KX, KY, 5.64, 9)
impact_lines(KX, KY, 5.64, big=False)
jolt(5.64, 1)
for L, (lx, rot, dur, h, bounce) in zip(NL, itertools.cycle([(110, -200, 0.55, 40, (10, 0.15, 5)), (55, -400, 0.70, 60, (14, 0.20, 8)),
                                               (140, 120, 0.45, 25, None), (85, -90, 0.60, 45, (8, 0.15, 4)),
                                               (170, 60, 0.40, 20, None), (200, 250, 0.50, 50, (6, 0.12, 4))])):
    L.fly(5.64, 5.64 + dur, lx, FLOOR - 6, rot, h, bounce)
red.pose(5.7, "fall", 0.06)
red.land(5.76)
dust(REDX1, FLOOR, 5.76)
red.pose(5.88, "hips", 0.1)
red.idle(5.88, 5.98, "hips")
def stuck_katana(hilt, tip, t_in, t_out, tugs=(), seed=1):
    """A katana buried in the floor from t_in to t_out. Entry cracks grow on impact, a few chips of
    floor spray out, and each tug time makes it wobble without coming loose."""
    (hx, hy), (tx, ty) = hilt, tip
    wob = Track(0.0)
    wob.hold(t_in - EPS)
    wob.add(t_in + 0.05, -5.0, "out")       # it bites and shivers
    wob.add(t_in + 0.13, 3.0, "inout")
    wob.add(t_in + 0.22, 0.0, "inout")
    for tt in tugs:
        wob.hold(tt - EPS)
        wob.add(tt + 0.04, -7.0, "out")
        wob.add(tt + 0.12, 4.0, "inout")
        wob.add(tt + 0.2, 0.0, "inout")
    op = Track(0)
    op.set(t_in, 1)
    op.hold(t_out[0])
    op.add(t_out[1], 0, "in")
    ex, ey = (tx + hx) / 2 + (tx - hx) * 0.42, FLOOR          # where the blade enters the floor
    cracks = []
    for i, (ang, L) in enumerate(((-150, 13), (-118, 9), (-62, 10), (-28, 14), (-95, 6))):
        a = math.radians(ang + (rnd(seed * 3 + i) - 0.5) * 16)
        pts = [(ex, ey), (ex + L * 0.5 * math.cos(a) + (rnd(i + seed) - 0.5) * 2, ey + L * 0.5 * math.sin(a)),
               (ex + L * math.cos(a), ey + L * math.sin(a))]
        cracks.append(grow(path_d(pts), polyline_len(pts), 1.1 if i < 4 else 0.7, t_in, 0.12))

    cid = f"floor{int(hx)}"

    def svg(p):
        return ('<g opacity="0">' + animate("opacity", op, str)
                + f'<clipPath id="{cid}"><rect x="{n(hx - 60)}" y="-20" width="140" height="{n(FLOOR + 20)}"/></clipPath>'
                + f'<g clip-path="url(#{cid})"><g>' + animate_tf("rotate", wob, lambda a: f"{n(a)} {n(ex)} {n(ey)}")
                + katana_svg(katana_parts(dict(RH=(hx, hy), WT=(tx, ty))), p) + "</g></g>"
                # the entry slit, a short dark gash the blade disappears into
                + f'<path d="M{n(ex - 4.5)},{n(ey - 0.6)} L{n(ex + 4.5)},{n(ey + 0.6)}" stroke="{p["fg"]}" stroke-width="2.2" stroke-linecap="round" opacity="0.85"/>'
                + f'<g fill="none" stroke="{p["fg"]}" stroke-linecap="round" stroke-linejoin="round" opacity="0.8">' + "".join(cracks) + "</g>"
                + "</g>")
    layer("props", svg)
    # chips of floor
    def chips(p):
        out = []
        for i in range(5):
            vx, vy = (rnd(i * 7 + seed) - 0.5) * 70, -(30 + 40 * rnd(i * 3 + seed))
            tr = Track((0.0, 0.0))
            tr.set(t_in, (0.0, 0.0))
            for j in range(1, 7):
                s_ = 0.4 * j / 6
                tr.add(t_in + s_, (vx * s_, vy * s_ + 240 * s_ * s_))
            o = Track(0)
            o.set(t_in, 1)
            o.hold(t_in + 0.3)
            o.add(t_in + 0.42, 0, "in")
            out.append(f'<g transform="translate({n(ex)},{n(ey)})"><rect x="-1.2" y="-1.2" width="2.4" height="2.4" fill="{p["fg"]}" opacity="0">'
                       + animate("opacity", o, str) + animate_tf("translate", tr, f_xy) + "</rect></g>")
        return "".join(out)
    layer("fx_low", chips)


# ---------------------------------------------------------------- rule break prop
RULE_GAP_OP = Track(0)


def rule_gap_svg(p):
    """A jagged gap in the heading rule, plus two short splintered ends."""
    left = "148,50 151,48.4 154,50.8 157,48.8 160,50.4"
    right = "186,50 183,48.6 180,50.6 177,48.4 174,50.2"
    return ('<g opacity="0">' + animate("opacity", RULE_GAP_OP, str)
            + f'<rect x="146" y="47.4" width="42" height="5.2" fill="{p["bg"]}"/>'
            + f'<polyline points="{left}" fill="none" stroke="{p["rule"]}" stroke-width="1.1"/>'
            + f'<polyline points="{right}" fill="none" stroke="{p["rule"]}" stroke-width="1.1"/>'
            + "</g>")


layer("fx_low", rule_gap_svg)

# ================================================================ ACT 2  the climb  (5.53 - 7.91)
# Ink owns the heading rule. Red climbs the bio lines like a staircase to reach him.
ink.put(5.90, 270, RULE_Y)
ink.pose(5.90, "stand", EPS)
ink.face(5.90, -1)
ink.show(5.98)
ink.stay(5.98)
dust(270, RULE_Y, 5.98)
jolt(5.98, 1.2)
ink.at(6.12, 240, RULE_Y, "inout")
ink.pose(6.20, "sw_draw", 0.10)
ink.weapon(6.26, True)
ink.pose(6.32, "sw_idle", 0.08, "snap")
spark(*ink.world(6.33, "WT"), 6.28, 6, kind="white")

red.face(6.02, 1)

# The staircase. Each landing uses a word as a ledge.
L1, L2, L3, L4 = 84.0, 124.0, 164.0, 204.0
for t0, t1, x, y, h in ((6.12, 6.28, 120, L4, 26),
                        (6.28, 6.44, 135, L3, 24),
                        (6.44, 6.60, 150, L2, 24),
                        (6.60, 6.76, 165, L1, 24),
                        (6.76, 6.92, 180, RULE_Y, 24)):
    hop(red, t0, t1, x, y, h, 0.10)
for t, x, y in ((6.28, 120, L4), (6.44, 135, L3), (6.60, 150, L2), (6.76, 165, L1), (6.92, 180, RULE_Y)):
    dust(x, y, t)
mark("!", *red.head_mark(6.24), 6.20, 0.40)
S1.dip(6.44)
S2.dip(6.60)
S3.dip(6.76)
jolt(6.92, 1.0)

# First clash on the rule.
red.face(6.92, 1)
red.pose(6.92, "sw_draw", 0.08)
red.weapon(6.98, True)
red.pose(7.00, "sw_idle", 0.06, "snap")
ink.pose(7.00, "sw_wind", 0.08, "inout")
ink.pose(7.06, "sw_down", 0.04, "snap")
red.pose(7.05, "sw_up", 0.03, "snap")
_c = red.world(7.06, "WT")
crescent(_c[0] + 8, _c[1] - 4, 34, -120, 60, 7.05, 0.12)
spark(_c[0], _c[1], 7.06, 9, kind="white")
impact_lines(_c[0], _c[1], 7.06, big=False)
jolt(7.06, 1.4)
flash(7.06, 0.04, 0.25)
red.pose(7.14, "sw_idle", 0.08)
ink.pose(7.14, "sw_rec", 0.08)
ink.at(7.20, 260, RULE_Y, "out")
red.at(7.20, 165, RULE_Y, "out")

# Ink teleports behind him. The tap gag becomes a tightrope taunt.
teleport(ink, 7.30, 120, RULE_Y, 1, "fg")
red.face(7.36, -1)
mark("?", *red.head_mark(7.38), 7.34, 0.40)
ink.pose(7.40, "tap", 0.06)
ink.pose(7.48, "tap2", 0.05)
ink.pose(7.56, "tap", 0.05)
red.pose(7.58, "guard", 0.06)
red.face(7.64, -1)
mark("!", *red.head_mark(7.62), 7.58, 0.40)

# The counter-cut nicks the rule itself.
heavy_upswing(red, 7.78)
ink.pose(7.72, "lean", 0.06)
ink.rot_to(7.72, 7.82, -58, "out", pivot=(0, 0))
ink.rot_to(7.92, 8.06, 0, "out")
ink.rot_pivot(8.06)
spark(168, RULE_Y, 7.84, 10)
jolt(7.84, 2.4)
dust(168, RULE_Y, 7.84)
RULE_GAP_OP.set(7.84, 0)
RULE_GAP_OP.add(7.88, 1, "out")

# The rule gives way; both fall to the word ladder.
red.jump(7.88, 8.05, 200, L1, 10)
red.pose(7.90, "fall", 0.06)
ink.jump(7.88, 8.05, 160, L2, 10)
red.land(8.05, 0.18, pose="crouch")
ink.land(8.05, 0.18, pose="crouch")
dust(200, L1, 8.05)
dust(160, L2, 8.05)

# ================================================================ ACT 3  the word ladder  (7.91 - 11.89)
# They swap levels while cutting the words between them.
# Red: line 1 -> line 2, overhead cut through "Experimenter."
red.pose(8.14, "sw_up", 0.08, "inout")
red.jump(8.16, 8.45, 135, L2, 22)
red.pose(8.29, "sw_down", 0.04, "snap")
_c = red.world(8.29, "N")
crescent(_c[0] + 8, _c[1] + 2, 38, -120, 60, 8.28, 0.13)
S2.slice(8.29, 35, fall=((-26, 70), (24, -120)), through=blade_cut_point(red, 8.29, S2))
jolt(8.29, 1.2)
red.land(8.45, 0.16, pose=None)
red.pose(8.50, "sw_thru", 0.06)

# Ink: line 2 -> line 1, rising cut through "Undergraduate."
ink.pose(8.18, "sw_low", 0.08, "inout")
ink.jump(8.20, 8.45, 160, L1, 22)
ink.pose(8.36, "sw_upcut", 0.08, "snap")
_c = ink.world(8.36, "N")
crescent(_c[0] + 10, _c[1] + 6, 38, 150, 250, 8.35, 0.13)
S3.slice(8.36, -32, fall=((-20, 60), (26, -110)), through=blade_cut_point(ink, 8.36, S3))
jolt(8.36, 1.2)
ink.land(8.45, 0.16, pose=None)
ink.pose(8.50, "sw_upthru", 0.08)

# Red drops to line 3 and cuts "break," on the way down.
red.pose(8.52, "sw_low", 0.10, "inout")
red.jump(8.54, 8.86, 70, L3, 26)
red.pose(8.70, "sw_upcut", 0.08, "snap")
_c = red.world(8.70, "N")
crescent(_c[0] + 10, _c[1] + 6, 40, 150, 250, 8.69, 0.13)
S1.slice(8.70, -32, fall=((-20, 60), (26, -110)), through=blade_cut_point(red, 8.70, S1))
jolt(8.70, 1.2)
red.land(8.86, 0.18, pose=None)
red.pose(8.92, "sw_rec", 0.10)
ink.jump(8.55, 8.90, 220, L3, 24)
ink.pose(8.62, "fall", 0.06)
ink.land(8.90, 0.16, pose="stand")
ink.face(8.95, 1)

# Both abandon the ladder and hit the floor.
red.pose(9.02, "sw_idle", 0.10)
red.jump(9.05, 9.45, 480, FLOOR, 10)
red.pose(9.10, "fall", 0.06)
ink.jump(9.10, 9.45, 620, FLOOR, 18)
ink.pose(9.15, "tuck", 0.06)
ink.land(9.45, 0.20, pose="stand")
dust(620, FLOOR, 9.45)

# Red dives after him and buries the blade in the floor.
red.pose(9.46, "sw_wind", 0.05)
red.jump(9.47, 9.58, 560, FLOOR, 8)
red.pose(9.55, "sw_stab", 0.06, "in")
SWX = 560
STUCK_HILT, STUCK_TIP = (SWX + 12, FLOOR - 24), (SWX + 26, FLOOR + 7)
dust(SWX + 22, FLOOR, 9.58, big=True)
jolt(9.58, 2.2)
impact_lines(SWX + 24, FLOOR, 9.58, big=False)
red.weapon(9.58, False)
red.land(9.58, 0.22, pose="tug1")
stuck_katana(STUCK_HILT, STUCK_TIP, 9.58, (15.00, 15.02), tugs=(9.58, 9.75, 10.05))
red.pose(9.75, "tug2", 0.08, "inout")
red.pose(10.00, "tug1", 0.08, "inout")
red.pose(10.20, "tug2", 0.08, "inout")
red.idle(10.20, 10.45, "tug1", 0.18)
ink.face(9.50, -1)
ink.pose(9.62, "hips", 0.10)
ink.idle(9.62, 10.45, "hips", 0.35)

# Ink ends the tug-of-war with a kick.
ink.pose(10.50, "crouch", 0.06)
ink.run(10.55, 10.76, 520)
ink.pose(10.80, "kick", 0.06, "snap")
_f = ink.world(10.82, "RF")
red.pose(10.82, "hit", EPS)
tt = hit(10.82, _f[0] - 4, _f[1], 11, ink, red)
red.jump(tt, 11.18, 470, FLOOR, 30)
red.spin(tt, 11.18, -360, "out")
red.land(11.18, 0.20, pose="lying")
jolt(11.18, 1.0)
dust(470, FLOOR, 11.18)
ink.pose(10.96, "stand", 0.10)
ink.face(11.00, 1)
ink.pose(11.38, "whistle", 0.10)
ink.idle(11.48, 11.72, "stand", 0.24)


class Chopper:
    """A vector cameo in Chopper's original pink hat; feet sit at local y=0."""
    PIVOT_Y = -12
    GRIP = (10, 0)

    def __init__(self):
        self.pos, self.sx, self.sc, self.op, self.rot = Track((640.0, float(FLOOR))), Track(-1), Track(0.0), Track(0), Track(0.0)

    def hop(self, t0, t1, x, y, h):
        self.pos.hold(t0)
        x0, y0 = self.pos.v
        for i in range(1, 7):
            s = i / 6
            self.pos.add(t0 + (t1 - t0) * s, (x0 + (x - x0) * s, y0 + (y - y0) * s - 4 * h * s * (1 - s)))

    def scurry(self, t0, t1, x1, y1, bounce=3):
        self.pos.hold(t0)
        x0, y0 = self.pos.v
        k = max(12, int((t1 - t0) / 0.02))
        for i in range(1, k + 1):
            s = i / k
            self.pos.add(t0 + (t1 - t0) * s, (x0 + (x1 - x0) * s, y0 + (y1 - y0) * s - abs(math.sin(s * 3 * math.pi)) * bounce))

    def grip_offset(self, t):
        """Apply the same scale then rotation as the SVG, before translation."""
        scale = eval_num(self.sc, t)
        x = self.GRIP[0] * eval_step(self.sx, t) * scale
        y = self.GRIP[1] * scale - self.PIVOT_Y
        angle = math.radians(eval_num(self.rot, t))
        ca, sa = math.cos(angle), math.sin(angle)
        return x * ca - y * sa, self.PIVOT_Y + x * sa + y * ca

    def follow_boot(self, actor, t0, t1):
        # Include facing/pose boundaries so the grip follows even a quick turn.
        times = {round(t0 + (t1 - t0) * i / 84, 5) for i in range(1, 85)}
        for track in (actor.pos, actor.sx, actor.sq, actor.rot, actor.pz, self.rot):
            times.update(t for t, _, _ in track.keys if t0 < t <= t1)
        for t in sorted(times):
            fx, fy = actor.world(t, "RF")
            dx, dy = self.grip_offset(t)
            self.pos.add(t, (fx - dx, fy - dy))

    def svg(self, p):
        times = sorted({k[0] for k in self.sx.keys} | {k[0] for k in self.sc.keys})
        sc = Track((0.0, 0.0))
        for tt in times:
            if tt == 0:
                continue
            s, q = eval_step(self.sx, tt), eval_num(self.sc, tt)
            sc.add(tt, (s * q, q))
        c = CHOPPER_COLORS
        antlers = 'M-6,-19 L-11,-23 L-12,-29 M-11,-24 L-15,-25 L-16,-28 M-12,-27 L-9,-29 M6,-19 L11,-23 L12,-29 M11,-24 L15,-25 L16,-28 M12,-27 L9,-29'
        body = (
            # A paper outline keeps the antlers visible against either theme.
            f'<path d="{antlers}" fill="none" stroke="{p["bg"]}" stroke-width="3.3" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="{antlers}" fill="none" stroke="{c["antlers"]}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<g stroke="{c["ink"]}" stroke-width=".65" stroke-linejoin="round">'
            f'<path d="M-4,-4 L-4.5,-.8 L-1.5,-.8 L-1,-4 M1,-4 L1.5,-.8 L4.5,-.8 L4,-4" fill="{c["fur"]}"/>'
            f'<path d="M-4.7,-1.8 H-1.4 V0 H-4.7 Z M1.4,-1.8 H4.7 V0 H1.4 Z" fill="{c["hoof"]}"/>'
            f'<ellipse cx="0" cy="-6.6" rx="4.5" ry="5" fill="{c["fur"]}"/>'
            f'<path d="M-4.4,-5.5 Q0,-4.3 4.4,-5.5 L4,-2.7 H.5 L0,-4 L-.5,-2.7 H-4 Z" fill="{c["shorts"]}"/>'
            f'<path d="M-4,-9 Q-7,-8 -7,-4 L-5.2,-3.5 L-2.8,-7 M3.8,-9 Q7,-5 10,-1 L8,-.7 L2.7,-6.5" fill="{c["fur"]}"/>'
            f'<path d="M-7,-4 L-5.2,-3.5 L-5.7,-2 L-7.5,-2.6 Z" fill="{c["hoof"]}"/>'
            f'<ellipse id="chopper-grip" cx="{self.GRIP[0]}" cy="{self.GRIP[1]}" rx="1.4" ry="1" fill="{c["hoof"]}"/>'
            f'<path d="M-5,-16 Q-11,-19 -9.5,-14 L-5,-12 M5,-16 Q11,-19 9.5,-14 L5,-12" fill="{c["fur"]}"/>'
            f'<ellipse cx="0" cy="-12.7" rx="6.8" ry="5.6" fill="{c["fur"]}"/>'
            '</g>'
            f'<ellipse cx="0" cy="-10.7" rx="4" ry="2.4" fill="{c["muzzle"]}"/>'
            f'<g fill="{c["ink"]}"><ellipse cx="-2.5" cy="-13.6" rx=".95" ry="1.3"/><ellipse cx="2.5" cy="-13.6" rx=".95" ry="1.3"/></g>'
            '<g fill="#fff"><circle cx="-2.7" cy="-14" r=".32"/><circle cx="2.3" cy="-14" r=".32"/></g>'
            f'<ellipse cx="0" cy="-11.5" rx="1.4" ry=".95" fill="{c["nose"]}"/>'
            f'<path d="M0,-10.5 V-9.6 M-1.5,-9.8 Q0,-8.4 1.5,-9.8" fill="none" stroke="{c["ink"]}" stroke-width=".6" stroke-linecap="round"/>'
            f'<path d="M-8,-18 L-7,-26 Q0,-28 7,-26 L8,-18 Z" fill="{c["hat"]}" stroke="{c["brim"]}" stroke-width=".8"/>'
            f'<path d="M-9,-18.7 Q0,-16.7 9,-18.7 L9,-16.7 Q0,-14.7 -9,-16.7 Z" fill="{c["brim"]}"/>'
            '<path d="M-2.3,-24.7 L2.3,-20.1 M2.3,-24.7 L-2.3,-20.1" fill="none" stroke="#fff" stroke-width="2"/>'
        )
        return ('<g id="chopper" opacity="0">' + animate("opacity", self.op, str) + animate_tf("translate", self.pos, f_xy) + "<g>"
                + animate_tf("rotate", self.rot, lambda a: f"{n(a)} 0 {self.PIVOT_Y}") + "<g>"
                + animate_tf("scale", sc, lambda v: f"{f_s(v[0])} {f_s(v[1])}") + body + "</g></g></g>")


# ================================================================ ACT 4  Chopper, clones, charm  (11.89 - 17.73)
# Red picks himself up after the kick.
red.pose(11.70, "crouch", 0.12, "inout")
red.pose(11.98, "stand", 0.14, "inout")
red.face(12.05, 1)
red.pose(12.28, "fall", 0.08, "inout")

chopper = Chopper()
chopper.pos.set(11.95, (760.0, float(FLOOR)))
chopper.op.set(11.95, 1)
chopper.sc.hold(11.95 - EPS)
chopper.sc.add(11.95, 0.0)
chopper.sc.add(12.05, 1.2, "out")
chopper.sc.add(12.15, 1.0, "inout")
chopper.hop(12.05, 12.20, 720, FLOOR, 14)
chopper.hop(12.20, 12.35, 680, FLOOR, 12)
_boot_x, _boot_y = red.world(12.42, "RF")
_grip_x, _grip_y = chopper.grip_offset(12.42)
chopper.scurry(12.35, 12.42, _boot_x - _grip_x, _boot_y - _grip_y)

# Red tries to shake him off.
for i in range(3):
    red.jump(12.45 + 0.14 * i, 12.59 + 0.14 * i, 470 + (6 if i % 2 else -6), FLOOR, 7)

# Now that the boot's path is authored, glue Chopper to it.
chopper.follow_boot(red, 12.42, 12.87)

chopper.rot.hold(12.86)
for i in range(1, 6):
    chopper.rot.add(12.86 + 0.05 * i, (8 if i % 2 else -8))
chopper.rot.add(13.15, 0.0, "out")
chopper.hop(12.88, 13.12, 650, FLOOR, 50)
dust(650, FLOOR, 13.12)
chopper.hop(13.30, 13.48, 780, FLOOR, 14)
chopper.rot.hold(13.50)
for i in range(1, 7):
    chopper.rot.add(13.50 + 0.05 * i, (5 if i % 2 else -5))
chopper.rot.add(13.82, 0.0, "out")

red.pose(13.10, "crouch", 0.10)
red.pose(13.25, "stand", 0.10)
red.face(13.28, 1)

# Three clones on three levels: the vertical pincer.
red.pose(13.38, "sign", 0.12)
red.jitter(13.38, 13.55, 0.5)
for cl, x, y in ((c1, 300, L1), (c2, 380, L2), (c3, 460, L3)):
    cl.put(0, x, y)
    cl.sx.set(0, 1)
    cl.show(13.52)
    poof(x, y - 14, 13.50, 1.1)
jolt(13.50, 1.0)

c1.pose(13.55, "crouch", 0.05)
c1.jump(13.58, 13.98, 560, 190, 30)
c1.pose(13.70, "fkick", 0.06)
c2.pose(13.55, "crouch", 0.05)
c2.jump(13.62, 13.98, 560, 190, 24)
c2.pose(13.74, "fkick", 0.06)
c3.pose(13.55, "crouch", 0.05)
c3.jump(13.58, 14.02, 700, 230, 28)
c3.pose(13.72, "kick", 0.06)

# Ink refuses to be surrounded.
teleport(ink, 13.78, 700, FLOOR, -1, "fg")
ink.pose(13.95, "sw_upcut", 0.05, "snap")
ink.pose(14.10, "sw_rec", 0.08)

tt = hit(13.98, 560, 190, 12, c1, c2, big=True, shake=2.5)
c1.pose(tt + 0.01, "hit", 0.03)
c2.pose(tt + 0.01, "hit", 0.03)
poof(560, 190, 14.02, 1.1)
c1.hide(14.06)
c2.hide(14.06)

spark(700, 230, 14.00, 9, kind="white")
impact_lines(700, 230, 14.00, big=False)
c3.pose(14.00, "hit", 0.03)
poof(700, 230, 14.02, 1.0)
c3.hide(14.06)
jolt(14.00, 1.0)
red.pose(14.10, "guard", 0.08)

# The charm. Red changes tactics.
red.pose(14.55, "hips", 0.10)
red.face(14.60, 1)
red.pose(14.70, "whistle", 0.10)
red.pose(14.90, "kiss2", 0.06, "snap")
_h0 = red.world(14.92, "RH")
_h1 = (ink.x(14.92), 190.0)
HEART_PATH = "M0,-3.2 C-1.6,-6.4 -6.4,-5.6 -6.4,-1.6 C-6.4,1.6 -2.4,4 0,6.4 C2.4,4 6.4,1.6 6.4,-1.6 C6.4,-5.6 1.6,-6.4 0,-3.2 Z"
HEART = dict(tr=Track(_h0), op=Track(0), sc=Track(0.6))
HEART["op"].set(14.94, 1)
for i in range(1, 17):
    s = i / 16
    HEART["tr"].add(14.94 + 0.42 * s, (_h0[0] + (_h1[0] - _h0[0]) * s,
                                      _h0[1] + (_h1[1] - _h0[1]) * s - math.sin(s * math.pi * 3) * 9 - 10 * math.sin(s * math.pi)))
    HEART["sc"].add(14.94 + 0.42 * s, 1.0 + 0.25 * math.sin(s * 14))
HEART["op"].hold(15.34)
HEART["op"].add(15.40, 0, "in")
HEART["sc"].add(15.40, 2.2, "out")
spark(_h1[0], _h1[1], 15.36, 8, kind="white")


def heart_svg(p):
    return ('<g opacity="0">' + animate("opacity", HEART["op"], str) + animate_tf("translate", HEART["tr"], f_xy) + "<g>"
            + animate_tf("scale", HEART["sc"], f_ss) + f'<path d="{HEART_PATH}" fill="{p["pink"]}"/></g></g>')


layer("fx_high", heart_svg)

ink.pose(15.36, "hit", 0.04)
ink.pose(15.52, "fall", 0.10)
ink.face(15.60, -1)
ink.pose(15.68, "float", 0.22, "inout")
ink.rot_to(15.62, 15.92, 62, "inout", pivot=(0, -13))
ink.at(15.92, 620, 190, "out")
ink.takeoff(15.68, 0.06)
T_DRIFT0, T_DRIFT1 = 15.98, 16.62
for i in range(1, 30):
    s = i / 29
    tt = T_DRIFT0 + (T_DRIFT1 - T_DRIFT0) * s
    ink.pos.add(tt, (620 + (660 - 620) * (0.5 - 0.5 * math.cos(s * math.pi)), 190 - 4 * math.sin(s * 9)))
ink.wobble(15.98, 16.62, 4, 0.5, base=62)
FLOAT_HEARTS = []
for j, (ox, oy, ph) in enumerate(((-10, -12, 0.0), (0, -20, 1.0), (10, -14, 2.0))):
    tr, op, sc = Track((0.0, 0.0)), Track(0), Track(1.0)
    t0 = 15.38 + 0.05 * j
    op.set(t0, 1)
    tr.set(t0, (ink.x(t0) + ox, 190 - 30 + oy))
    t_ = t0
    while t_ < 16.62:
        t_ += 0.05
        ix, iy = eval_num(ink.pos, t_)
        tr.add(t_, (ix + 17 + ox, iy - 20 + oy + 2.5 * math.sin(t_ * 9 + ph)))
    sc.hold(16.62)
    sc.add(16.74, 1.8, "out")
    op.hold(16.62)
    op.add(16.74, 0, "in")
    FLOAT_HEARTS.append((tr, op, sc))


def float_hearts_svg(p):
    return "".join('<g opacity="0">' + animate("opacity", op, str) + animate_tf("translate", tr, f_xy) + "<g>"
                   + animate_tf("scale", sc, lambda s: f_ss(s * 0.8))
                   + f'<path d="{HEART_PATH}" fill="{p["pink"]}"/></g></g>' for tr, op, sc in FLOAT_HEARTS)


layer("fx_high", float_hearts_svg)
DARK_HEART_OP = Track(0)
DARK_HEART_OP.set(16.55, 0)
DARK_HEART_OP.add(16.65, 1, "out")
DARK_HEART_OP.hold(16.92)
DARK_HEART_OP.add(17.02, 0, "in")


def dark_heart_svg(p):
    return ('<g opacity="0">' + animate("opacity", DARK_HEART_OP, str)
            + f'<path d="{HEART_PATH}" fill="#0b0a18" stroke="{p["pink"]}" stroke-width="1.2" '
              'transform="translate(646,168) scale(2.4)"/></g>')


layer("fx_high", dark_heart_svg)

# The charm turns. Ink catches it, crushes it, and the Bankai charge begins.
ink.pose(16.62, "stand", 0.08)
ink.rot_to(16.62, 16.92, 0, "out")
ink.at(16.65, 640, 180, "inout")
ink.face(16.65, 1)
ink.pose(16.90, "guard", 0.10)
HEAD_X, HEAD_Y = ink.world(16.90, "H")
EYE_X, EYE_Y = HEAD_X, HEAD_Y
EYE_X += 3.2
EYE_Y -= 0.8
EYES_OP = Track(0)
EYES_OP.set(16.65, 1)
EYES_OP.hold(17.60)
EYES_OP.add(17.75, 0, "in")
spark(EYE_X, EYE_Y, 16.90, 8, kind="white")
jolt(16.90, 0.8)
red.pose(16.20, "crouch", 0.08)
red.run(16.25, 16.50, 540)
red.pose(16.55, "guard", 0.08)
red.face(16.55, 1)
mark("!", *red.head_mark(16.60), 16.56, 0.40)
chopper.hop(16.35, 16.60, 760, FLOOR, 16)
chopper.op.set(16.80, 0)


# ================================================================ ACT 5  Bankai: Margin Storm  (17.73 - 25.45)
# The charm breaks. Ink's eyes catch the light, the page turns to ink, and the margin itself
# becomes a blade. The Bankai is a dark field, a giant spectral katana, an orbiting blade storm,
# and one vertical cut that breaks the wall Red hides behind.

BANKAI_CX, BANKAI_CY = 600.0, 160.0
BANKAI_RADIUS = 740.0
BANKAI_BLADE_X, BANKAI_BLADE_Y = 716.0, 170.0
BANKAI_CUT_X = 716.0
T_BUBBLE0, T_BUBBLE1 = 17.55, 17.90
T_FIELD0, T_FIELD1 = 17.90, 18.60
T_BLADE0, T_BLADE1 = 18.15, 18.65
T_STORM0, T_STORM1 = 18.40, 24.60
T_CUT = 23.40
T_COLLAPSE0, T_COLLAPSE1 = 24.10, 24.90
BANKAI_TR = Track((0.0, 0.0))

# ---- the announcement
BUBBLE_OP = Track(0)
BUBBLE_OP.set(T_BUBBLE0, 1)
BUBBLE_OP.hold(T_BUBBLE1 - 0.05)
BUBBLE_OP.add(T_BUBBLE1, 0, "in")
BUBBLE_SC = Track(0.3)
BUBBLE_SC.hold(T_BUBBLE0)
BUBBLE_SC.add(T_BUBBLE0 + 0.10, 1.12, "out")
BUBBLE_SC.add(T_BUBBLE0 + 0.20, 1.0, "inout")
BUBBLE_SC.hold(T_BUBBLE1 - 0.05)
BUBBLE_SC.add(T_BUBBLE1, 1.35, "in")


def bubble_svg(p):
    bx, by, w, h = 16, -54, 150, 38
    body = (f'<rect x="{bx}" y="{by}" width="{w}" height="{h}" rx="7" fill="{p["bg"]}" stroke="{p["fg"]}" stroke-width="1.4"/>'
            f'<polygon points="{bx + 10},{by + h - 1} {bx + 28},{by + h - 1} {bx - 4},{by + h + 12}" fill="{p["bg"]}" stroke="{p["fg"]}" stroke-width="1.4" stroke-linejoin="round"/>'
            f'<rect x="{bx + 11}" y="{by + h - 3}" width="16" height="4" fill="{p["bg"]}"/>')
    text = (f'<text x="{bx + w / 2}" y="{by + 16}" text-anchor="middle" font-size="12.48" font-weight="700" fill="{p["fg"]}">Bankai.</text>'
            f'<text x="{bx + w / 2}" y="{by + 30}" text-anchor="middle" font-size="12.48" font-weight="700" fill="{VOID_RIM}">Margin Storm.</text>')
    return (f'<g transform="translate({n(HEAD_X)},{n(HEAD_Y)})"><g opacity="0">' + animate("opacity", BUBBLE_OP, str)
            + animate_tf("scale", BUBBLE_SC, f_ss) + body + text + "</g></g>")


layer("fx_high", bubble_svg)
jolt(T_BUBBLE0 + 0.10, 0.8)

# ---- the ink field
BANKAI_R = Track(0.0)
BANKAI_R.hold(T_FIELD0)
BANKAI_R.add(T_FIELD1, BANKAI_RADIUS, "in")
BANKAI_R.hold(T_COLLAPSE0)
BANKAI_R.add(T_COLLAPSE1, 0.0, "out")
BANKAI_RING_OP = Track(0)
BANKAI_RING_OP.set(T_FIELD0, 0.9)
BANKAI_RING_OP.hold(T_COLLAPSE0)
BANKAI_RING_OP.add(T_COLLAPSE0 + 0.05, 0)
BANKAI_SHOCK = Track(0.0)
BANKAI_SHOCK.hold(T_FIELD0)
BANKAI_SHOCK.add(T_FIELD0 + 0.30, 180.0, "out")
BANKAI_SHOCK_OP = Track(0)
BANKAI_SHOCK_OP.set(T_FIELD0, 0.9)
BANKAI_SHOCK_OP.add(T_FIELD0 + 0.30, 0, "in")
BANKAI_GHOST_OP = Track(0)
BANKAI_GHOST_OP.hold(T_FIELD0 + 0.15)
BANKAI_GHOST_OP.add(T_FIELD1, 0.22, "out")
BANKAI_GHOST_OP.hold(T_COLLAPSE0 - 0.1)
BANKAI_GHOST_OP.add(T_COLLAPSE0 + 0.1, 0, "in")
BANKAI_INK_WIN = Track(0)
BANKAI_INK_WIN.set(T_FIELD0 + 0.05, 1)
BANKAI_INK_WIN.hold(T_COLLAPSE0)
BANKAI_INK_WIN.add(T_COLLAPSE1, 0, "in")


def bankai_ghost_svg(p):
    out = ['<g opacity="0">', animate("opacity", BANKAI_GHOST_OP, str),
           f'<text x="0" y="{H1_Y}" font-size="32" font-weight="600" fill="#ffffff">{html.escape(H1_TEXT)}</text>',
           f'<path d="M0,{RULE_Y} H{W}" stroke="#ffffff" stroke-width="1"/>']
    for wd in ALL_WORDS:
        out.append(wd.plain("#ffffff"))
    out.append("</g>")
    return "".join(out)


# ---- the giant spectral katana
BANKAI_BLADE_OP = Track(0)
BANKAI_BLADE_OP.hold(T_BLADE0)
BANKAI_BLADE_OP.add(T_BLADE1, 0.9, "out")
BANKAI_BLADE_OP.hold(T_CUT - 0.05)
BANKAI_BLADE_OP.add(T_CUT, 1.0, "out")
BANKAI_BLADE_OP.hold(T_CUT + 0.35)
BANKAI_BLADE_OP.add(24.35, 0, "in")
BANKAI_BLADE_SC = Track(0.18)
BANKAI_BLADE_SC.hold(T_BLADE0)
BANKAI_BLADE_SC.add(T_BLADE1, 1.0, "out")
BANKAI_BLADE_SC.hold(T_CUT - 0.05)
BANKAI_BLADE_SC.add(T_CUT, 1.06, "snap")
BANKAI_BLADE_SC.add(T_CUT + 0.18, 1.0, "out")
BANKAI_BLADE_SC.hold(24.05)
BANKAI_BLADE_SC.add(24.30, 0.2, "in")
BANKAI_BLADE_TR = Track((0.0, 0.0))
BANKAI_BLADE_TR.hold(T_CUT - 0.05)
BANKAI_BLADE_TR.add(T_CUT, (0.0, 24.0), "snap")
BANKAI_BLADE_TR.add(T_CUT + 0.22, (0.0, 0.0), "out")
BANKAI_BLADE_ROT = Track(0.0)
BANKAI_BLADE_ROT.hold(T_BLADE0)
BANKAI_BLADE_ROT.add(T_BLADE1, -4.0, "inout")
BANKAI_BLADE_ROT.hold(T_CUT)
BANKAI_BLADE_ROT.add(T_CUT + 0.20, 0.0, "out")


def bankai_blade_svg(p):
    blade = "M0,-150 L7,-132 L10,34 L6,58 L0,66 L-6,58 L-10,34 L-7,-132 Z"
    wrap = "".join(f'<path d="M-4,{n(70 + 5 * i)} Q0,{n(73 + 5 * i)} 4,{n(70 + 5 * i)}" fill="none" '
                   f'stroke="#ffffff" stroke-width="0.7" opacity="0.55"/>' for i in range(5))
    return ('<g opacity="0">' + animate("opacity", BANKAI_BLADE_OP, str)
            + f'<g transform="translate({n(BANKAI_BLADE_X)},{n(BANKAI_BLADE_Y)})">'
            + '<g>' + animate_tf("translate", BANKAI_BLADE_TR, f_xy)
            + '<g>' + animate_tf("rotate", BANKAI_BLADE_ROT, lambda a: f"{n(a)} 0 0")
            + '<g>' + animate_tf("scale", BANKAI_BLADE_SC, f_ss)
            + '<ellipse cx="0" cy="-38" rx="72" ry="196" fill="url(#bladeglow)"/>'
            + f'<path d="{blade}" fill="none" stroke="#ffffff" stroke-width="12" opacity="0.10"/>'
            + f'<path d="{blade}" fill="none" stroke="#ffffff" stroke-width="5" opacity="0.22"/>'
            + f'<path d="{blade}" fill="{p["void_fg"]}" stroke="#ffffff" stroke-width="1.3" opacity="0.95"/>'
            + '<path d="M0,-146 V58" stroke="#ffffff" stroke-width="1.1" opacity="0.75"/>'
            + '<path d="M-7,-120 Q0,-110 7,-120" fill="none" stroke="#ffffff" stroke-width="0.9" opacity="0.65"/>'
            + f'<ellipse cx="0" cy="64" rx="18" ry="4.2" fill="{p["tsuba"]}" stroke="#ffffff" stroke-width="0.8"/>'
            + '<rect x="-4" y="64" width="8" height="32" rx="1.5" fill="#2b2b2b" stroke="#ffffff" stroke-width="0.7"/>'
            + wrap
            + "</g></g></g></g></g>")


# ---- the Margin Storm
STORM_OP = Track(0)
STORM_OP.hold(T_STORM0)
STORM_OP.add(T_STORM0 + 0.5, 1.0, "out")
STORM_OP.hold(T_STORM1 - 0.2)
STORM_OP.add(T_STORM1 + 0.2, 0, "in")
STORM_BLADES = []
STORM_SQUASH = 0.72
for i in range(12):
    a0 = i * 30.0 + 6.0
    r = 150.0 + 10.0 * i
    spin = 360.0 if i % 2 == 0 else -360.0
    ang = Track(a0)
    ang.hold(T_STORM0)
    for k in range(1, 17):
        ang.add(T_STORM0 + 0.4 * k, a0 + spin * k / 16.0)
    ang.hold(T_STORM1 + 0.2)
    sc = Track(0.9 + 0.18 * (i % 3))
    sc.hold(T_STORM0)
    for k in range(1, 13):
        sc.add(T_STORM0 + 0.5 * k, 0.9 + 0.25 * (i % 3) + (0.12 if k % 2 else -0.08))
    sc.hold(T_STORM1 + 0.2)
    op = Track(0)
    op.set(T_STORM0 + 0.03 * i, 0.9)
    op.hold(T_STORM1)
    op.add(T_STORM1 + 0.2, 0, "in")
    fall = Track((0.0, 0.0))
    if i in (2, 5, 8, 11):
        fall.hold(T_STORM0 + 0.2)
        fall.add(T_STORM1, (0.0, 150.0 + 10.0 * i), "in")
    STORM_BLADES.append((ang, r, sc, op, fall, i))


def bankai_storm_svg(p):
    out = ['<g opacity="0">' + animate("opacity", STORM_OP, str)
           + f'<g transform="translate({n(BANKAI_CX)},{n(BANKAI_CY)}) scale(1,{n(STORM_SQUASH)})">']
    for ang, r, sc, op, fall, i in STORM_BLADES:
        out.append("<g>" + animate_tf("rotate", ang, lambda a: f"{n(a)} 0 0")
                   + "<g>" + animate_tf("translate", fall, f_xy)
                   + f'<g transform="translate({n(r)},0) rotate({n(90 + 18 * (i % 3))})">'
                   + '<g opacity="0">' + animate("opacity", op, str)
                   + animate_tf("scale", sc, f_ss)
                   + f'<path d="M-40,0 Q-20,-8 0,0 Q-20,4 -40,0 Z" fill="{p["void_fg"]}" opacity="0.35"/>'
                   + f'<path d="M0,0 Q24,-16 52,0 Q26,-2 0,0 Z" fill="{p["void_fg"]}" stroke="#ffffff" stroke-width="0.9"/>'
                   + '<path d="M5,0 Q26,-9 46,0" fill="none" stroke="#ffffff" stroke-width="0.6" opacity="0.75"/>'
                   + "</g></g></g></g>")
    out.append("</g></g>")
    return "".join(out)


# ---- the final vertical cut
BANKAI_CUT_OP = Track(0)
BANKAI_CUT_OP.set(T_CUT - 0.10, 0)
BANKAI_CUT_OP.add(T_CUT, 1, "out")
BANKAI_CUT_OP.hold(T_CUT + 0.45)
BANKAI_CUT_OP.add(T_CUT + 0.85, 0, "in")


def bankai_cut_svg(p):
    return ('<g opacity="0">' + animate("opacity", BANKAI_CUT_OP, str)
            + f'<path d="M{n(BANKAI_CUT_X)},-10 V{H + 10}" stroke="#ffffff" stroke-width="12" opacity="0.22"/>'
            + f'<path d="M{n(BANKAI_CUT_X)},-10 V{H + 10}" stroke="#ffffff" stroke-width="2.6"/>'
            + f'<path d="M{n(BANKAI_CUT_X - 3)},-10 V{H + 10}" stroke="{p["void_fg"]}" stroke-width="0.9" opacity="0.7"/>'
            + "</g>")


layer("top", bankai_cut_svg)
cut_crack, _ = crack_set(BANKAI_CUT_X, FLOOR - 6, 72, 9, seed=77, span=(-math.pi * 0.82, -math.pi * 0.18),
                         t_show=T_CUT, prop=0.10, width=1.1, colour="crack")
layer("fx_high", cut_crack)


def void_svg(p):
    return ('<g>'
            + '<defs><radialGradient id="bankaig" cx="0.5" cy="0.5" r="0.5">'
              '<stop offset="0" stop-color="#05050e"/><stop offset="0.78" stop-color="#0a0920"/>'
              '<stop offset="1" stop-color="#241f52"/></radialGradient>'
              '<radialGradient id="bladeglow" cx="0.5" cy="0.5" r="0.5">'
              '<stop offset="0" stop-color="#ffffff" stop-opacity="0.22"/>'
              '<stop offset="0.55" stop-color="#ffffff" stop-opacity="0.09"/>'
              '<stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient></defs>'
            + '<g>' + animate_tf("translate", BANKAI_TR, f_xy)
            + f'<circle cx="{n(BANKAI_CX)}" cy="{n(BANKAI_CY)}" r="0" fill="url(#bankaig)">' + animate("r", BANKAI_R, n) + "</circle>"
            + f'<circle cx="{n(BANKAI_CX)}" cy="{n(BANKAI_CY)}" r="0" fill="none" stroke="{VOID_RIM}" stroke-width="2.5" opacity="0">'
            + animate("r", BANKAI_R, n) + animate("opacity", BANKAI_RING_OP, str) + "</circle>"
            + f'<circle cx="{n(BANKAI_CX)}" cy="{n(BANKAI_CY)}" r="0" fill="none" stroke="{VOID_RIM}" stroke-width="3" opacity="0">'
            + animate("r", BANKAI_SHOCK, n) + animate("opacity", BANKAI_SHOCK_OP, str) + "</circle>"
            + "</g>"
            + bankai_ghost_svg(p) + bankai_storm_svg(p)
            + "</g>")


# ---- charge glow at the hand
SIGN_X, SIGN_Y = BANKAI_CX, BANKAI_CY
GLOW = Track(0)
GLOW.set(17.30, 0)
GLOW.add(17.50, 1.0, "out")
GLOW.hold(17.75)
GLOW.add(17.95, 0, "in")


def glow_svg(p):
    return (f'<g transform="translate({n(SIGN_X)},{n(SIGN_Y)})"><circle r="6" fill="{VOID_RIM}" opacity="0">'
            + animate("opacity", GLOW, str) + "</circle></g>")


# ---- Ink announces it, then settles onto the floor
ink.pose(17.10, "sign", 0.14, "inout")
ink.idle(17.10, 17.50, "sign", 0.35)
jolt(17.30, 0.6)
ink.pose(17.62, "sign", 0.20, "inout")
ink.at(18.55, 640, FLOOR, "inout")
ink.pose(18.52, "fall", 0.10)
ink.land(18.62, 0.20)
ink.pose(18.78, "stand", 0.12)
ink.face(18.80, 1)

# Red feels the page change.
red.pose(17.62, "guard", 0.08)
mark("!", *red.head_mark(17.68), 17.64, 0.40)
red.pose(17.78, "fall", 0.08)
red.at(18.02, 500, FLOOR, "out")
red.pose(18.10, "guard", 0.08)
red.face(18.10, 1)
red.pose(18.35, "cover", 0.10, "inout")
red.idle(18.45, 18.70, "cover", 0.35)

# The blade comes out.
red.pose(18.72, "sw_draw", 0.10)
red.weapon(18.80, True)
red.pose(18.88, "sw_idle", 0.08, "snap")
spark(*red.world(18.86, "WT"), 18.82, 6, kind="white")

# Ink draws too, and the storm answers.
ink.pose(19.18, "sw_draw", 0.10)
ink.weapon(19.28, True)
ink.pose(19.38, "sw_idle", 0.08, "snap")
spark(*ink.world(19.36, "WT"), 19.32, 6, kind="white")

# First falling blade: Red cuts it out of the air.
red.pose(19.02, "sw_up", 0.08, "inout")
red.pose(19.14, "sw_down", 0.04, "snap")
_c = red.world(19.14, "WT")
crescent(_c[0] + 10, _c[1] - 4, 36, -120, 60, 19.13, 0.12)
spark(_c[0], _c[1], 19.14, 10, kind="white")
impact_lines(_c[0], _c[1], 19.14, big=False)
jolt(19.14, 1.6)
red.pose(19.24, "sw_thru", 0.07)
red.pose(19.40, "sw_idle", 0.10)

# Second blade: a rising cut.
red.pose(19.48, "sw_low", 0.08, "inout")
red.pose(19.60, "sw_upcut", 0.05, "snap")
_c = red.world(19.60, "WT")
crescent(_c[0] + 12, _c[1] + 4, 38, 150, 250, 19.59, 0.12)
spark(_c[0], _c[1], 19.60, 10, kind="white")
jolt(19.60, 1.4)
red.pose(19.72, "sw_upthru", 0.08)

# Third blade: Red jumps into it.
red.pose(19.82, "sw_wind", 0.08, "inout")
red.jump(19.86, 20.10, 620, 238, 18)
red.pose(19.98, "sw_down", 0.04, "snap")
_c = red.world(19.98, "WT")
crescent(_c[0] + 8, _c[1] + 4, 40, -120, 60, 19.97, 0.12)
spark(_c[0], _c[1], 19.98, 10, kind="white")
jolt(19.98, 1.4)
red.land(20.10, 0.16)
red.pose(20.16, "sw_thru", 0.06)

# The storm lands one. Red is thrown across the page.
red.pose(20.24, "hit", EPS)
tt = hit(20.24, red.x(20.24) + 8, 205, 15, red, big=True, shake=3)
red.jump(tt, 20.70, 700, FLOOR, 26)
red.spin(tt, 20.70, -300, "out")
red.land(20.70, 0.22, pose="lying")
dust(700, FLOOR, 20.70)
jolt(20.70, 1.2)

ink.pose(19.78, "point", 0.10)
ink.pose(20.10, "sw_idle", 0.10)
ink.pose(20.62, "hips", 0.10)
ink.idle(20.62, 22.20, "hips", 0.40)

# Red gets up and builds the wall.
red.pose(20.84, "crouch", 0.12, "inout")
red.pose(21.04, "stand", 0.10)
red.pose(21.10, "guard", 0.08)
red.run(21.14, 21.38, 760, frame=0.06)
red.pose(21.44, "crouch", 0.08)
red.pose(21.56, "stand", 0.08)
red.run(21.60, 21.78, 742, frame=0.06)
red.face(21.82, -1)
red.pose(21.86, "place_lo", 0.08)

BLOCKS = [(700 + col * 16, FLOOR - 8 - row * 16, 21.95 + 0.1 * i)
          for i, (col, row) in enumerate(((0, 0), (1, 0), (0, 1), (1, 1), (0, 2), (1, 2)))]
for bx, by, bt in BLOCKS:
    red.pose(bt - 0.02, "place_hi" if by < FLOOR - 24 else "place_lo", 0.07, "snap")
red.pose(22.55, "cover", 0.12, "inout")
red.idle(22.55, 23.30, "cover", 0.45)
WALL_ROT = Track((0.0, 716.0, float(FLOOR)))
WALL_OP = Track(0)
WALL_OP.set(21.90, 1)


def block_svg(p, seed):
    out = []
    for r in range(8):
        for c in range(8):
            if r < 2:
                col = BLOCK_GREEN[int(rnd(seed * 17 + r * 8 + c) * 3)]
            elif r == 2 and rnd(seed * 5 + c) < 0.45:
                col = BLOCK_GREEN[2]
            else:
                col = BLOCK_BROWN[int(rnd(seed * 23 + r * 8 + c) * 4)]
            out.append(f'<rect x="{-8 + c * 2}" y="{-8 + r * 2}" width="2" height="2" fill="{col}"/>')
    out.append('<rect x="-8" y="-8" width="16" height="16" fill="none" stroke="#3b2414" stroke-width="0.8" opacity="0.6"/>')
    return "".join(out)


def wall_svg(p):
    out = ['<g opacity="1">' + animate("opacity", WALL_OP, str) + "<g>" + animate_tf("rotate", WALL_ROT, f_rot)]
    for i, (bx, by, bt) in enumerate(BLOCKS):
        sc = Track(0.0)
        sc.hold(bt - EPS)
        sc.add(bt, 0.2)
        sc.add(bt + 0.07, 1.18, "out")
        sc.add(bt + 0.14, 1.0, "inout")
        out.append(f'<g transform="translate({n(bx)},{n(by)})"><g>' + animate_tf("scale", sc, f_ss) + block_svg(p, i + 1) + "</g></g>")
    out.append("</g></g>")
    return "".join(out)


layer("over_red", wall_svg)
for bx, by, bt in BLOCKS:
    spark(bx, by, bt, 5, kind="white", dur=0.16)

# Ink lifts the sword. The page rumbles. The blade falls.
ink.pose(22.30, "sw_wind", 0.20, "inout")
ink.pose(22.60, "sw_wind", 0.40, "inout")
ink.jitter(22.40, 23.20, 0.35, 24)
rumble(22.40, 23.30, 0.30, 1.0)
heavy_slash(ink, T_CUT, big=False)
flash(T_CUT, 0.05, 0.45, colour="void_fg")
jolt(T_CUT, 2.8)
dust(750, FLOOR, T_CUT, big=True)

# The wall takes the cut and falls on Red.
WALL_ROT.hold(23.20)
for i, a in enumerate((-1.0, 1.2, -0.8, 1.0, -0.5, 0)):
    WALL_ROT.add(23.24 + 0.05 * i, (a, 716.0, float(FLOOR)))
WALL_ROT.hold(23.40)
WALL_ROT.add(23.48, (3.0, 716.0, float(FLOOR)), "out")
WALL_ROT.add(23.62, (90.0, 716.0, float(FLOOR)), "in")
T_BURY = 23.62
WALL_OP.set(T_BURY, 0)
jolt(T_BURY, 2.4)
dust(750, FLOOR, T_BURY, big=True)
impact_lines(750, FLOOR - 8, T_BURY, big=False)
red.pose(T_BURY, "lying", 0.04)
red.face(T_BURY, 1)

PILE_TR = Track((0.0, 0.0))
PILE_TR.hold(24.10)
for i in range(1, 9):
    PILE_TR.add(24.10 + 0.03 * i, (1.6 * (rnd(i * 2.3) - 0.5) * 2, 1.2 * (rnd(i * 4.1) - 0.5) * 2))
PILE_TR.add(24.36, (0.0, 0.0))
LOOSE = []
for i, (bx, by, bt) in enumerate(BLOCKS):
    dx, dy = bx - 716, by - FLOOR
    lx, ly = 716 - dy, FLOOR + dx
    tr, rt, op = Track((lx, ly)), Track(90.0), Track(0)
    op.set(T_BURY, 1)
    LOOSE.append([tr, rt, op, i, lx, ly])


def throw_block(i, t, x1, y1, h, drot, dur=0.3):
    tr, rt, op, _, lx, ly = LOOSE[i]
    tr.hold(t)
    rt.hold(t)
    x0, y0 = tr.v
    r0 = rt.v
    for j in range(1, 8):
        s = j / 7
        tr.add(t + dur * s, (x0 + (x1 - x0) * s, y0 + (y1 - y0) * s - 4 * h * s * (1 - s)))
        rt.add(t + dur * s, r0 + drot * s)
    tr.add(t + dur + 0.1, (x1 + 4, y1 - 3), "out")
    rt.add(t + dur + 0.1, rt.v + 8, "out")
    tr.add(t + dur + 0.18, (x1 + 6, y1), "in")


# The pile shakes; the top block pops off; Red stands up out of it with a pickaxe.
throw_block(2, 24.52, 700, FLOOR - 8, 34, -140, 0.32)
red.pose(24.48, "crouch", 0.10)
red.pose(24.62, "dig_hold", 0.12)
red.pick(24.58, True)
red.weapon(24.58, False)
red.face(24.55, -1)
red.pose(24.76, "dig_up", 0.10)
red.pose(24.88, "dig_down", 0.05, "snap")
_pk = red.world(24.89, "WT")
spark(_pk[0], _pk[1], 24.89, 7)
dust(_pk[0], FLOOR - 6, 24.89)
jolt(24.89, 1)
throw_block(0, 24.89, 684, FLOOR - 8, 40, -220, 0.34)
throw_block(1, 24.90, 660, FLOOR - 8, 26, 160, 0.30)
red.pose(25.02, "dig_up", 0.10)
red.pose(25.14, "dig_down", 0.05, "snap")
_pk = red.world(25.15, "WT")
spark(_pk[0], _pk[1], 25.15, 7)
dust(_pk[0], FLOOR - 6, 25.15)
jolt(25.15, 1)
throw_block(3, 25.15, 826, FLOOR - 8, 30, 200, 0.30)
throw_block(4, 25.16, 760, FLOOR - 8, 44, -260, 0.36)
for i in range(6):
    LOOSE[i][2].hold(FADE[0] + 0.2)
    LOOSE[i][2].add(FADE[1] + 0.2, 0, "in")


def loose_svg(p):
    return ('<g>' + animate_tf("translate", PILE_TR, f_xy)
            + "".join('<g opacity="0">' + animate("opacity", op, str) + animate_tf("translate", tr, f_xy) + "<g>"
                      + animate_tf("rotate", rt, lambda a: f"{n(a)} 0 0") + block_svg(p, i + 1) + "</g></g>"
                      for tr, rt, op, i, _, _ in LOOSE) + "</g>")


layer("over_red", loose_svg)
layer("over_red", bankai_blade_svg)

# Red clears the last of it and stands on the rubble.
red.pose(25.22, "dig_hold", 0.10)
red.run(25.26, 25.42, 744, frame=0.065)
red.pose(25.42, "dig_hold", 0.08)
red.pose(25.52, "dust", 0.10)
red.pick(25.52, False)
red.pose(25.64, "dust2", 0.06)
red.pose(25.76, "stand", 0.10)
red.face(25.80, -1)

# The Bankai collapses back into Ink's sword.
ink.pose(24.92, "sw_rec", 0.12)
ink.pose(25.10, "stand", 0.12)
ink.face(25.10, 1)

# The field retracts into the blade rather than shrinking around a fixed point. The sword is
# still being sheathed at T_COLLAPSE1, so aim for its rest position once the sheath completes.
BANKAI_TR_TARGET = ink.world(25.10, "WT")
BANKAI_TR.hold(T_COLLAPSE0)
BANKAI_TR.add(T_COLLAPSE1, (BANKAI_TR_TARGET[0] - BANKAI_CX,
                            BANKAI_TR_TARGET[1] - BANKAI_CY), "out")


# ================================================================ ACT 6  reset  (25.45 - 31.00)
# Ink sheathes. Red steps down. The page heals, the words return, and the two fighters salute
# before the margin goes quiet again.

ink.pose(25.82, "sw_rec", 0.10)
ink.weapon(25.98, False)
ink.pose(26.10, "stand", 0.12)
ink.face(26.15, -1)

# Red drops off the rubble and runs to the center-left; Ink gives him room.
red.pose(25.86, "crouch", 0.10)
red.jump(25.90, 26.24, 690, FLOOR, 10)
red.land(26.24, 0.20)
red.pose(26.30, "crouch", 0.08)
red.run(26.34, 26.74, 540, frame=0.06)
red.pose(26.82, "dust", 0.10)
red.pose(26.94, "dust2", 0.06)
red.pose(27.08, "stand", 0.10)
red.face(27.16, -1)

ink.run(26.80, 27.15, 600, frame=0.06)
ink.pose(27.22, "stand", 0.10)
ink.face(27.30, -1)

# A quiet beat. The page heals under them.
ink.pose(27.36, "hips", 0.10)
ink.idle(27.36, 27.70, "hips", 0.35)
red.pose(27.36, "hips", 0.10)
red.idle(27.36, 27.70, "hips", 0.35)

# The rule closes its cut.
RULE_GAP_OP.hold(26.75)
RULE_GAP_OP.add(27.35, 0, "in")

# Words and letters return while the hole and debris fade (see FADE / RESTORE in the engine).
for i, wd in enumerate([RD] + NL):
    wd.restore(RESTORE[0] + 0.03 * i, RESTORE[1] - 0.3 + 0.03 * i)
for wd in (S1, S2, S3):
    for hw in wd.halves:
        hw.restore(RESTORE[0], RESTORE[1] - 0.3)
        hw.op.set(RESTORE[1] - 0.25, 0)
    wd.op.set(RESTORE[1] - 0.25, 1)

# They look at the restored page, then at each other.
red.pose(27.70, "stand", 0.12)
ink.pose(27.70, "stand", 0.12)
red.face(27.85, -1)
ink.face(27.85, -1)
red.face(28.10, 1)
ink.face(28.10, -1)

# Salute and bow.
red.pose(28.28, "wave1", 0.12)
red.pose(28.48, "wave2", 0.10)
red.pose(28.68, "wave1", 0.10)
red.pose(28.88, "stand", 0.12)
ink.pose(28.32, "clap", 0.12)
ink.rot_to(28.42, 28.78, -12, "inout", pivot=(0, 0))
ink.rot_to(28.94, 29.24, 0, "inout")
ink.pose(28.96, "stand", 0.12)

# Chopper peeks back in from the right to wave.
chopper.pos.set(29.05, (826.0, float(FLOOR)))
chopper.op.set(29.05, 1)
chopper.sx.set(29.05, -1)
chopper.sc.hold(29.05 - EPS)
chopper.sc.add(29.05, 1.0)
chopper.hop(29.05, 29.30, 780, FLOOR, 18)
chopper.hop(29.30, 29.45, 760, FLOOR, 10)
chopper.rot.hold(29.45)
for i in range(1, 7):
    chopper.rot.add(29.45 + 0.06 * i, (10 if i % 2 else -10))
chopper.rot.add(29.85, 0.0, "out")
chopper.op.hold(30.00)
chopper.op.add(30.30, 0, "in")

# The page goes quiet. Everyone leaves before the loop point.
red.op.hold(30.05)
red.op.add(30.50, 0, "in")
ink.op.hold(30.15)
ink.op.add(30.60, 0, "in")

# ---- metadata for the player and the preview sheets
ACTS = [('01-break-in', 0., 5.53), ('02-the-climb', 5.53, 7.91),
        ('03-word-ladder', 7.91, 11.89), ('04-chopper-clones-charm', 11.89, 17.73),
        ('05-bankai', 17.73, 25.45), ('06-reset', 25.45, T)]
BEATS = [
    (.65, 'Cracks spread through a word', 'page'),
    (1.45, 'The page shatters and a hole opens', 'hole'),
    (2.07, 'Hands catch the rim; the figure climbs out', 'climb'),
    (3.61, 'Both feet reach the page', 'handoff'),
    (4.71, 'A landing, a dust-off, a look around', 'acting'),
    (5.39, 'A jump kick scatters the letters', 'type'),
    (5.73, 'Ink waits on the heading rule', 'arrival'),
    (6.05, 'Red climbs the bio lines like a staircase', 'climb'),
    (6.81, 'The first clash rings out on the rule', 'clash'),
    (7.09, 'A teleport turns a slash into a miss', 'teleport'),
    (7.59, 'The counter-cut nicks the rule', 'rule break'),
    (8.04, 'A cut splits Experimenter.', 'first cut'),
    (8.11, 'A rising cut splits Undergraduate.', 'second cut'),
    (8.45, 'A third cut splits break,', 'third cut'),
    (9.33, 'The katana sticks in the floor', 'sword'),
    (10.57, 'A kick interrupts the pulling', 'kick'),
    (12.10, 'Chopper grabs a boot', 'Chopper'),
    (13.27, 'Three clones dive from three levels', 'clones'),
    (14.69, 'A charm heart finds its mark', 'heart'),
    (16.30, 'The charm turns dark', 'reversal'),
    (17.30, 'Bankai: Margin Storm', 'Bankai'),
    (18.15, 'The ink field and the spectral blade rise', 'field'),
    (18.90, 'The blade storm begins', 'storm'),
    (21.70, 'Six blocks become a wall', 'wall'),
    (23.15, 'The final cut breaks the wall', 'impact'),
    (24.20, 'A pickaxe clears the rubble', 'pickaxe'),
    (24.65, 'The Bankai collapses into the sword', 'collapse'),
    (27.00, 'The page heals', 'reset'),
    (28.10, 'Words and rule return', 'restore'),
    (28.80, 'A salute, a bow', 'salute'),
    (29.35, 'Chopper peeks in to wave', 'cameo'),
    (30.35, 'The page is quiet again', 'loop'),
]
ALT = ('Ansil / ClashLex: a margin duel. A figure climbs out of a broken word and ascends the '
       'bio lines to meet a swordsman on the heading rule. Their duel cuts the rule and the words, '
       'a Chopper cameo interrupts the tug-of-war, a vertical clone pincer is broken, and a love '
       'charm turns into the trigger for Bankai: Margin Storm. The ink field, spectral katana and '
       'blade storm bury the challenger, who digs out with a pickaxe as the page rebuilds.')


def render(theme):
    p = PALETTES[theme]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT_STACK}" role="img" aria-labelledby="title desc">',
           '<defs><radialGradient id="holeg"><stop offset="0" stop-color="#000000"/><stop offset="0.72" stop-color="#07061a"/>'
           '<stop offset="1" stop-color="#2a2654"/></radialGradient>'
           '<radialGradient id="voidg"><stop offset="0" stop-color="#05050e"/><stop offset="0.82" stop-color="#0c0b24"/>'
           '<stop offset="1" stop-color="#2b2466"/></radialGradient>'
           f'<clipPath id="holeclip"><polygon points="{" ".join(f"{n(x)},{n(y)}" for x, y in HOLE_PTS)}"/></clipPath>'
           f'<clipPath id="pageclip"><path clip-rule="evenodd" d="M-20,-20 H{W + 20} V{H + 20} H-20 Z M{" L".join(f"{n(x)},{n(y)}" for x, y in HOLE_PTS)} Z"/></clipPath></defs>',
           f'<rect width="{W}" height="{H}" fill="{p["bg"]}"/>',
           "<g>", animate_tf("translate", FRAME, f_xy),
           f'<text x="0" y="{H1_Y}" font-size="32" font-weight="600" fill="{p["fg"]}">{html.escape(H1_TEXT)}</text>',
           f'<path d="M0,{RULE_Y} H{W}" stroke="{p["rule"]}" stroke-width="1"/>']
    for line in LINES:
        for wd in line:
            out.append(wd.all_svg(p["fg"]))
    for L in NL:
        out.append(L.svg(p["fg"]))
    out.append(hole_svg(p))
    out.extend(fn(p) for fn in LAYERS["cracks"])
    out.append('<g clip-path="url(#holeclip)">' + crawl.svg(p["red"]) + "</g>")
    out.append(RD.svg(p["fg"]))
    for name in ("debris", "props", "fx_low"):
        out.extend(fn(p) for fn in LAYERS[name])
    out.append(glow_svg(p))
    for cl in (c1, c2, c3):
        out.append(cl.svg(p["red"]))
    out.append(ink.svg(p["fg"], weapons=p, katana_win=(6.0, 26.0)))
    out.extend(fn(p) for fn in LAYERS["fx_mid"])
    out.append(void_svg(p))
    out.append('<g clip-path="url(#pageclip)">' + crawl.svg(p["red"], limb_ops=True, halo=p["bg"]) + "</g>")
    out.append(hole_svg(p, edge_only=True))
    out.append(chopper.svg(p))
    out.append(red.svg(p["red"], weapons=p, katana_win=(6.0, 24.4), pick_win=(24.3, 25.6)))
    out.extend(fn(p) for fn in LAYERS["over_red"])
    out.append(ink.svg(p["void_fg"], weapons=p, op_track=BANKAI_INK_WIN, katana_win=(18.8, 25.0)))
    for name in ("fx_high", "marks", "top"):
        out.extend(fn(p) for fn in LAYERS[name])
    out.append("</g></svg>")
    timeline = html.escape(json.dumps(dict(duration=T, acts=ACTS, beats=BEATS), separators=(',', ':')))
    out.insert(1, '<title id="title">ANSIL - README rumble</title><desc id="desc">'+html.escape(ALT)+'</desc><metadata id="film-timeline">'+timeline+'</metadata>')
    return "".join(out)



def static_svg(svg):
    root = ET.fromstring(svg)
    for parent in list(root.iter()):
        for child in list(parent):
            if child.tag.rsplit('}', 1)[-1] in ('animate', 'animateTransform'):
                parent.remove(child)
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    return ET.tostring(root, encoding='unicode')


def lint_svg(svg):
    """Validate reference output and report its actual animation cost."""
    root = ET.fromstring(svg)
    nodes = list(root.iter())
    parents = {child: parent for parent in nodes for child in parent}
    ids = [node.get('id') for node in nodes if node.get('id')]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate SVG IDs')
    for ref in re.findall(r'(?:url\(#|href="#)([^)" ]+)', svg):
        if ref not in ids:
            raise ValueError(f'Missing SVG reference: {ref}')
    events, opacity_tracks, instances, animations = [], {}, {}, []
    for node in nodes:
        tag = node.tag.rsplit('}', 1)[-1]
        if tag in ('script', 'foreignObject', 'image', 'filter', 'style'):
            raise ValueError(f'Unsupported SVG element: {tag}')
        for attr, value in node.attrib.items():
            if attr.startswith('on') or attr.endswith('href') and not value.startswith('#'):
                raise ValueError('Executable or external SVG content')
        if tag == 'use':
            instances.setdefault(node.get('href', '')[1:], []).append(node)
        if tag not in ('animate', 'animateTransform'):
            continue
        animations.append(node)
        times = [float(t)*T for t in node.get('keyTimes', '').split(';')]
        vals = node.get('values', '').split(';')
        if len(times) != len(vals) or times[0] != 0 or times[-1] != T or any(a >= b for a, b in zip(times, times[1:])):
            raise ValueError('Invalid animation timing')
        if node.get('calcMode') == 'spline' and len(node.get('keySplines', '').split(';')) != len(vals)-1:
            raise ValueError('Invalid spline count')
        if node.get('attributeName') == 'd':
            signatures = {re.sub(r'[-+]?(?:\d*\.)?\d+', '#', value) for value in vals}
            if len(signatures) != 1:
                raise ValueError('Incompatible morph topology')
        target = parents[node]
        if node.get('attributeName') == 'opacity':
            opacity_tracks[target] = (times, list(map(float, vals)))
        for i, (a, b) in enumerate(zip(times, times[1:])):
            if vals[i] != vals[i+1]:
                events.extend(((a, 1, target), (b, -1, target)))
    def shown(node, t):
        while node is not None:
            alpha = float(node.get('opacity', '1'))
            if node in opacity_tracks:
                ts, vs = opacity_tracks[node]
                i = min(len(ts)-2, max(0, bisect_right(ts, t)-1))
                u = (t-ts[i])/(ts[i+1]-ts[i])
                alpha = vs[i]+(vs[i+1]-vs[i])*u
            if alpha <= 0:
                return False
            node = parents.get(node)
        return True
    events.sort(key=lambda event: (event[0], event[1]))
    active = Counter()
    peak, when = 0, 0.
    for i, (t, delta, target) in enumerate(events):
        active[target] += delta
        if not active[target]:
            del active[target]
        if i+1 < len(events) and events[i+1][0] > t:
            at = (t+events[i+1][0])/2
            targets = {use for node in active for use in instances.get(node.get('id'), [node])}
            count = sum(shown(node, at) for node in targets)
            if count > peak:
                peak, when = count, at
    return dict(bytes=len(svg.encode('utf-8')), elements=len(nodes), animation_tracks=len(animations),
                peak_changing_elements=peak, peak_time=round(when, 3), poses=len(POSES), duration=T,
                reference_sha256=REFERENCE_SHA256, engine='supplied-reference')


def preview(outdir,files,fps=12,export=False,browser=None):
    try:
        from playwright.sync_api import sync_playwright
        from PIL import Image,ImageChops,ImageDraw
    except ImportError as exc:
        raise RuntimeError('Preview needs pillow and playwright. Install them, then run playwright install chromium.') from exc
    ffmpeg=None
    if export:
        ffmpeg=shutil.which('ffmpeg')
        if not ffmpeg:
            try:
                import imageio_ffmpeg
                ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
            except ImportError as exc:
                raise RuntimeError('--export needs ffmpeg or imageio-ffmpeg') from exc
    outdir.mkdir(parents=True,exist_ok=True)
    qa={}
    with sync_playwright() as pw:
        options={'headless':True}
        if browser:
            options['executable_path']=browser
        b=pw.chromium.launch(**options)
        pg=b.new_page(viewport={'width':W,'height':H},device_scale_factor=1)
        for theme,path in files.items():
            folder=outdir/theme; folder.mkdir(exist_ok=True)
            pg.goto(path.resolve().as_uri())
            pg.evaluate('document.documentElement.pauseAnimations()')
            def frame(t,dest):
                pg.evaluate('(t)=>document.documentElement.setCurrentTime(t)',t)
                pg.screenshot(path=str(dest),animations='allow')
            for label,t in (('start',0),('end',T-.001),('repeat',T+.001)):
                frame(t,folder/f'{label}.png')
            with Image.open(folder/'start.png') as initial,Image.open(folder/'end.png') as last,Image.open(folder/'repeat.png') as repeat:
                seam=ImageChops.difference(initial.convert('RGB'),last.convert('RGB')).getbbox() is None
                loop=ImageChops.difference(initial.convert('RGB'),repeat.convert('RGB')).getbbox() is None
            if not seam or not loop:
                raise ValueError(f'{theme}: visible loop seam')
            frame_count=round(T*fps)
            for i in range(frame_count):
                frame(i/fps,folder/f'frame-{i:04d}.png')
                if i%120==0:
                    print(f'{theme}: frame {i}/{frame_count}',flush=True)
            # Every frame appears on its act sheet, with readable time labels.
            for name,start,end in ACTS:
                indices=[i for i in range(frame_count) if start<=i/fps<end]
                cols,tw,th=6,332,round(H*332/W)
                sheet=Image.new('RGB',(cols*tw,math.ceil(len(indices)/cols)*(th+18)),PALETTES[theme]['bg'])
                draw=ImageDraw.Draw(sheet)
                for j,i in enumerate(indices):
                    with Image.open(folder/f'frame-{i:04d}.png') as im:
                        sheet.paste(im.resize((tw,th)),((j%cols)*tw,(j//cols)*(th+18)))
                    draw.text(((j%cols)*tw+6,(j//cols)*(th+18)+th+2),f'{i/fps:05.2f}s',fill=PALETTES[theme]['fg'])
                sheet.save(outdir/f'{theme}-{name}.jpg',quality=88)
            # A compact overview supplements the full act sheets.
            thumb_h=round(H*415/W); row_h=thumb_h+18
            sheet=Image.new('RGB',(3*415,math.ceil(len(BEATS)/3)*row_h),PALETTES[theme]['bg']); draw=ImageDraw.Draw(sheet)
            for i,(t,_,_) in enumerate(BEATS):
                fi=min(frame_count-1,round((t+.28)*fps))
                with Image.open(folder/f'frame-{fi:04d}.png') as im:
                    sheet.paste(im.resize((415,thumb_h)),((i%3)*415,(i//3)*row_h))
                draw.text(((i%3)*415+7,(i//3)*row_h+thumb_h+1),f'{fi/fps:05.2f}s',fill=PALETTES[theme]['fg'])
            sheet.save(outdir/f'{theme}-storyboard.jpg',quality=92)
            if export:
                source=str(folder/'frame-%04d.png')
                subprocess.run([ffmpeg,'-y','-loglevel','error','-framerate',str(fps),'-i',source,'-vf','pad=ceil(iw/2)*2:ceil(ih/2)*2','-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(outdir/f'raid-{theme}.mp4')],check=True)
                subprocess.run([ffmpeg,'-y','-loglevel','error','-framerate',str(fps),'-i',source,'-filter_complex','[0:v]split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer','-loop','0',str(outdir/f'raid-{theme}.gif')],check=True)
            # Exercise the actual image embedding mode in both desktop and mobile widths.
            embed=outdir/f'{theme}-embed.html'
            embed.write_text(f'<!doctype html><meta charset="utf-8"><style>body{{margin:0}}img{{display:block;width:100%}}</style><img src="{path.resolve().as_uri()}" alt="raid">',encoding='utf-8')
            pg.goto(embed.resolve().as_uri())
            pg.wait_for_function('document.querySelector("img").complete && document.querySelector("img").naturalWidth > 0')
            before=outdir/f'{theme}-embed-before.png'
            after=outdir/f'{theme}-embed-after.png'
            pg.screenshot(path=str(before),animations='allow')
            pg.wait_for_timeout(1800)
            pg.screenshot(path=str(after),animations='allow')
            with Image.open(before) as first,Image.open(after) as later:
                moving=ImageChops.difference(first.convert('RGB'),later.convert('RGB')).getbbox() is not None
            if not moving:
                raise ValueError(f'{theme}: embedded SVG is static instead of animating')
            for width in (830,390):
                pg.set_viewport_size({'width':width,'height':max(1,round(width*H/W))})
                pg.screenshot(path=str(outdir/f'{theme}-embed-{width}.png'))
            pg.set_viewport_size({'width':W,'height':H})
            qa[theme]=dict(seam_pixels_equal=seam,repeat_pixels_equal=loop,img_embedding=True,img_animation_pixels_changed=moving,frames=frame_count,fps=fps)
        b.close()
    (outdir/'render-report.json').write_text(json.dumps(qa,indent=2)+'\n',encoding='utf-8')
    return qa


def bundle(outdir,files):
    destination=outdir/'ansil-raid.zip'
    source=Path(__file__).resolve().parent
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
        source_files = (
            'make_raid_v2.py', 'assemble_v2.py',
            '_v2_acts_2_3.py', '_v2_act4.py', '_v2_act5.py', '_v2_act6.py',
            'test_raid_v2.py', 'V2_DESIGN.md', 'preview.html',
        )
        for name in source_files:
            path = source/name
            if path.exists():
                archive.write(path,'raid/'+name)
        for name in ('validation.json','raid-light-static.svg','raid-dark-static.svg'):
            archive.write(outdir/name,'raid/'+name)
        for path in files.values():
            archive.write(path,'raid/'+path.name)
        preview_names = ['render-report.json', 'controls-report.json', 'readme-embedding-report.json', 'chopper-report.json', 'chopper-contact-sheet.png', 'player-desktop.png', 'player-mobile.png']
        for theme in PALETTES:
            preview_names.extend(f'{theme}-{name}.jpg' for name, _, _ in ACTS)
            preview_names.extend([f'{theme}-storyboard.jpg', f'raid-{theme}.gif', f'raid-{theme}.mp4'])
            preview_names.extend(f'{theme}-embed-{width}.png' for width in (830, 390))
        for name in preview_names:
            path = outdir/'preview'/name
            if path.is_file():
                archive.write(path, 'raid/preview/'+name)
    print(f'Bundle: {destination}',flush=True)





def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--export', action='store_true')
    parser.add_argument('--fps', type=int, default=12)
    parser.add_argument('--browser')
    args = parser.parse_args()
    if args.export and not args.preview:
        parser.error('--export requires --preview')
    if args.check and (args.preview or args.export):
        parser.error('--check cannot render previews')
    if not 1 <= args.fps <= 60:
        parser.error('--fps must be between 1 and 60')
    outputs, reports, files = {}, {}, {}
    for theme in PALETTES:
        svg = render(theme)
        if svg != render(theme):
            raise ValueError('Nondeterministic build')
        report = lint_svg(svg)
        report['sha256'] = hashlib.sha256(svg.encode('utf-8')).hexdigest()
        reports[theme] = report
        files[theme] = args.out/f'raid-{theme}.svg'
        outputs[files[theme]] = svg
        outputs[args.out/f'raid-{theme}-static.svg'] = static_svg(svg)
        print(f'{theme}: {report["bytes"]:,} bytes, {report["peak_changing_elements"]} changing elements, {report["poses"]} poses', flush=True)
    outputs[args.out/'validation.json'] = json.dumps(reports, indent=2)+'\n'
    if args.check:
        for path, content in outputs.items():
            if not path.exists() or path.read_text(encoding='utf-8') != content:
                raise ValueError(f'Stale generated asset: {path}')
        print('Generated assets are current.')
        return
    args.out.mkdir(parents=True, exist_ok=True)
    for path, content in outputs.items():
        path.write_text(content, encoding='utf-8')
    if args.preview:
        preview(args.out/'preview', files, args.fps, args.export, args.browser)
    if args.export:
        bundle(args.out, files)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError) as exc:
        print(f'raid: {exc}', file=sys.stderr)
        sys.exit(1)
