#!/usr/bin/env python3
"""ANSIL / below deck. Deterministic, self-contained SMIL, in two palettes.

python make_raid.py                         build and lint
python make_raid.py --preview               12 fps frames, act sheets, loop QA
python make_raid.py --preview --export      also GIF, MP4 and a release zip
python make_raid.py --check                 verify committed assets are current
Optional preview dependencies: pillow playwright; export: imageio-ffmpeg.
"""
import argparse
from collections import Counter
import hashlib
import html
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

T, W, H = 34.0, 830, 360
CW, CH, X0, Y0 = 16, 25, 119, 104
FLOOR, DECK, S = 310, 650, 1.35
SIZE_LIMIT, ACTIVE_LIMIT = 750_000, 60
EPS = 0.002
ALT = ('ANSIL in vector ASCII letters. A pirate raises a flag on the I; a navy '
       'officer chases him down the S. The I falls through the deck. Below, a fuse '
       'ignites barrels and launches them back through the letters. The fragments '
       'rebuild ANSIL; a white flag waves from the L before the pirate climbs away.')
POSTER_HEAD, POSTER_NAME = 'WANTED', 'CLASHLEX'
POSTER_REWARD = 'REWARD: ONE STAR'
PALETTES = {
    'light': dict(bg='#faf8f3', fg='#252b30', rule='#cbc8be', pirate='#b64b31', navy='#335f94'),
    'dark': dict(bg='#11171d', fg='#e0e2dc', rule='#3b454d', pirate='#eb967b', navy='#8eafda'),
}
SPLINES = {'lin': '0 0 1 1', 'out': '0 0 0.35 1', 'in': '0.55 0 1 1',
           'smooth': '0.42 0 0.58 1', 'snap': '0 0 0.12 1'}
ACTS = [('01-arrival', 0, 6.6), ('02-chase', 6.6, 13.2),
        ('03-below-deck', 13.2, 22.0), ('04-return', 22.0, 34.0)]
BEATS = [
    (0.6, 'A ripple travels A to L', 'footfalls'),
    (1.0, 'Rope swing, A apex kick, L ledge landing', 'rope / A / L'),
    (2.6, 'Climb the I and tie a flag', 'I / flag'),
    (3.8, 'Dagger pins a wanted notice to the S', 'dagger / poster'),
    (4.8, 'Officer descends onto the N staircase', 'N / rope'),
    (5.8, 'Poster, pirate, poster: the spyglass confirms it', 'poster'),
    (6.6, 'A whistle; the pirate drops down the S', 'S shelves'),
    (7.4, 'Three blade contacts separate the S shelves', 'S / sword'),
    (8.5, 'Flag rope swing; a slash drops the flag on the officer', 'flag / rope'),
    (9.6, 'Blinded swing cuts the I at its foot', 'flag / I'),
    (10.7, 'The I falls like a mast; both try to stop it', 'I'),
    (12.0, 'The mast hits the deck; cracks race out', 'I / hole'),
    (13.2, 'The letters lean in; both fall through', 'hole'),
    (14.4, 'Below deck: a lantern reveals the barrel room', 'hole / lantern'),
    (15.4, 'The officer sticks his sword into a barrel', 'sword'),
    (16.4, 'Pirate balances on a rolling barrel; officer pulls', 'barrel / sword'),
    (17.8, 'The dagger strikes a spark on the fuse', 'dagger / fuse'),
    (18.8, 'Officer chases the spark; the pirate ducks', 'fuse'),
    (20.0, 'Three barrels burst in sequence', 'barrels / fuse'),
    (22.0, 'Blast through the hole; ANSIL shatters from below', 'hole / letters'),
    (23.4, 'Officer wedges into the L while rubble falls', 'L'),
    (25.0, 'Fragments reverse their fall and lock A to L', 'letters / heal'),
    (28.2, 'Pirate tips his hat; a surrender flag emerges from L', 'flag / L'),
    (31.0, 'Opening rope returns; the pirate leaves; the deck heals', 'rope / hole'),
]

ART_RAW = [
    "█████╗ ███╗   ██╗███████╗██╗██╗     ",
    "██╔══██╗████╗  ██║██╔════╝██║██║     ",
    "███████║██╔██╗ ██║███████╗██║██║     ",
    "██╔══██║██║╚██╗██║╚════██║██║██║     ",
    "██║  ██║██║ ╚████║███████║██║███████╗",
    "╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝╚═╝╚══════╝",
]
LETTER_COLS = [(0, 8), (8, 18), (18, 26), (26, 29), (29, 37)]   # A N S I L



def n(value):
    result = f'{value:.3f}'.rstrip('0').rstrip('.')
    return '0' if result in ('', '-0') else result


def nums(value):
    return ' '.join(n(v) for v in value) if isinstance(value, (tuple, list)) else n(value)


def pts(values):
    return ' '.join(f'{n(x)},{n(y)}' for x, y in values)


def rnd(i):
    value = math.sin(i * 12.9898 + 78.233) * 43758.5453
    return value - math.floor(value)


def mix(a, b, s):
    if isinstance(a, dict):
        return {k: mix(a[k], b[k], s) for k in a}
    if isinstance(a, (tuple, list)):
        return tuple(mix(x, y, s) for x, y in zip(a, b))
    return a + (b - a) * s


def eased(s, mode):
    if mode == 'lin' or s <= 0 or s >= 1:
        return s
    x1, y1, x2, y2 = map(float, SPLINES[mode].split())
    lo, hi = 0., 1.
    for _ in range(22):
        u = (lo + hi) / 2
        x = 3 * (1-u)**2 * u * x1 + 3 * (1-u) * u*u * x2 + u**3
        if x < s:
            lo = u
        else:
            hi = u
    u = (lo + hi) / 2
    return 3 * (1-u)**2 * u * y1 + 3 * (1-u) * u*u * y2 + u**3


class Track:
    """Ordered keyframes. Conflicting writes fail instead of moving the story."""
    def __init__(self, value):
        self.k = [(0., value, 'lin')]

    @property
    def end(self):
        return self.k[-1][0]

    @property
    def value(self):
        return self.k[-1][1]

    def to(self, t, value, ease='lin'):
        t = round(t, 6)
        if not 0 <= t <= T or t < self.end - 0.000001:
            raise ValueError(f'Out-of-order key {t:g}; previous key {self.end:g}')
        if abs(t - self.end) < 0.000001:
            if value != self.value:
                raise ValueError(f'Conflicting values at {t:g}: {self.value} / {value}')
            return self
        if ease not in SPLINES:
            raise ValueError(ease)
        self.k.append((t, value, ease))
        return self

    def hold(self, t):
        if t > self.end:
            self.to(t, self.value)
        return self

    def snap(self, t, value):
        self.hold(t - EPS)
        return self.to(t, value)

    def at(self, t):
        for a, b in zip(self.k, self.k[1:]):
            if t <= b[0]:
                return mix(a[1], b[1], eased(max(0, (t-a[0])/(b[0]-a[0])), b[2]))
        return self.value

    def keys(self):
        return self.k + ([(T, self.value, 'lin')] if self.end < T else [])


def anim(attr, track, fmt=nums, transform=None):
    keys = track.keys()
    values = [fmt(v) for _, v, _ in keys]
    if len(set(values)) == 1:
        return ''
    times = ';'.join(f'{t/T:.8f}' for t, _, _ in keys)
    tag = 'animateTransform' if transform else 'animate'
    kind = f' type="{transform}"' if transform else ''
    splines = ';'.join(SPLINES[e] for _, _, e in keys[1:])
    return (f'<{tag} attributeName="{attr}"{kind} values="{";".join(values)}" '
            f'keyTimes="{times}" calcMode="spline" keySplines="{splines}" '
            f'dur="{n(T)}s" repeatCount="indefinite"/>')


def group(inner, track, kind='translate'):
    return (f'<g transform="{kind}({nums(track.k[0][1])})">'
            + anim('transform', track, transform=kind) + inner + '</g>')


def opacity(inner, track):
    return f'<g opacity="{n(track.k[0][1])}">' + anim('opacity', track) + inner + '</g>'


def visible(start, end):
    return Track(0).snap(start, 1).snap(end, 0)


def follow(track, lag=0.07, gain=0.32):
    """Delayed response to movement: hats, cloth and rope settle after a stop."""
    result = Track(0.)
    for a, b in zip(track.k, track.k[1:]):
        if isinstance(a[1], tuple):
            delta = b[1][0] - a[1][0]
        else:
            delta = b[1] - a[1]
        t = min(T - 0.3, b[0] + lag)
        if t > result.end:
            result.to(t, max(-9, min(9, -delta * gain)), 'smooth')
    result.to(T, 0., 'smooth')
    return result


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



def pose_variant(name, base, **changes):
    POSES[name] = dict(POSES[base], **{k: tuple(v) for k, v in changes.items()})


# Acting poses, with deliberate differences in gaze, weight and hand placement.
pose_variant('look_left', 'stand', H=(-3,-30), RE=(3,-20), RH=(1,-16))
pose_variant('look_right', 'stand', H=(4,-30), LE=(-4,-20), LH=(-2,-16))
pose_variant('double_take', 'stand', H=(-4,-32), N=(-2,-26), RE=(6,-23), RH=(11,-27))
pose_variant('spyglass', 'guard', H=(2,-30), RE=(6,-26), RH=(7,-30), LE=(4,-24), LH=(15,-30), WT=(24,-30))
pose_variant('spyglass_lower', 'stand', RE=(6,-22), RH=(10,-23))
pose_variant('whistle', 'stand', RE=(5,-24), RH=(4,-29), LE=(-5,-18), LH=(-6,-12))
pose_variant('shrug', 'stand', LE=(-7,-24), LH=(-12,-27), RE=(7,-24), RH=(12,-27))
pose_variant('climb_left', 'hang', LE=(-5,-28), LH=(-7,-31), RE=(3,-36), RH=(2,-42), LK=(-7,-15), LF=(-8,-9), RK=(4,-6), RF=(4,0))
pose_variant('climb_right', 'hang', LE=(-3,-36), LH=(-2,-42), RE=(5,-28), RH=(7,-31), LK=(-4,-6), LF=(-4,0), RK=(7,-15), RF=(8,-9))
pose_variant('tie_flag', 'stand', LE=(2,-28), LH=(9,-32), RE=(7,-27), RH=(11,-32))
pose_variant('tighten_knot', 'tie_flag', LH=(3,-30), RH=(17,-32), H=(4,-29))
pose_variant('rope_slide', 'hang', LK=(-6,-11), LF=(-3,-5), RK=(5,-12), RF=(4,-6))
pose_variant('brake', 'hit', LK=(-7,-6), LF=(-13,0), RK=(7,-7), RF=(14,0))
pose_variant('peek', 'crouch', H=(6,-24), N=(2,-18), RH=(8,-24))
pose_variant('blind', 'stand', LE=(-6,-27), LH=(-6,-34), RE=(6,-27), RH=(6,-34))
pose_variant('blind_swing', 'sw_cut', H=(-3,-28), LE=(-5,-27), LH=(-7,-34))
pose_variant('push', 'guard', H=(4,-27), N=(3,-23), RE=(12,-22), RH=(18,-25), LE=(11,-25), LH=(18,-28))
pose_variant('push_low', 'push', H=(6,-24), P=(-3,-12), LF=(-12,0), RF=(9,0))
pose_variant('teeter_left', 'stand', H=(-5,-30), N=(-3,-25), LE=(-9,-27), LH=(-17,-25), RE=(8,-25), RH=(15,-29), RF=(5,-5))
pose_variant('teeter_right', 'stand', H=(5,-30), N=(3,-25), LE=(-8,-25), LH=(-15,-29), RE=(9,-27), RH=(17,-25), LF=(-5,-5))
pose_variant('balance', 'stand', LE=(-9,-25), LH=(-18,-25), RE=(9,-25), RH=(18,-25), LF=(-6,0), RF=(6,0))
pose_variant('balance_low', 'crouch', LE=(-9,-17), LH=(-18,-19), RE=(9,-17), RH=(18,-19))
pose_variant('pull_hard', 'pull', H=(-7,-29), N=(-5,-24), LH=(9,-23), RH=(11,-20), LF=(-12,0))
pose_variant('pull_release', 'fly', H=(-4,-28), RH=(9,-30), LH=(-8,-30))
pose_variant('strike_flint', 'light', RE=(8,-16), RH=(15,-15), LE=(5,-11), LH=(11,-10))
pose_variant('chase_spark', 'crouch', H=(7,-20), RE=(10,-10), RH=(18,-4))
pose_variant('shield', 'crouch', LE=(-5,-25), LH=(2,-28), RE=(5,-25), RH=(-2,-28))
pose_variant('hat_tip', 'stand', RE=(6,-28), RH=(3,-38), H=(3,-28))
pose_variant('bow', 'stand', H=(12,-23), N=(8,-20), LE=(4,-17), LH=(5,-12), RE=(12,-20), RH=(16,-23))
pose_variant('reach_rope', 'stand', LE=(-4,-28), LH=(-2,-38), RE=(3,-34), RH=(2,-44))
pose_variant('surrender', 'lying', RE=(6,-14), RH=(7,-27))


def body_path(p):
    h = p['H']
    d = f'M{n(h[0]-4.6)},{n(h[1])}a4.6,4.6 0 1 0 9.2,0a4.6,4.6 0 1 0 -9.2,0'
    for limb in LIMBS:
        d += 'M' + 'L'.join(f'{n(p[j][0])},{n(p[j][1])}' for j in limb)
    return d


class Char:
    def __init__(self, scene, role, start):
        self.scene, self.role = scene, role
        self.pos, self.pose = Track(start), Track(POSES['stand'])
        self.rot, self.face, self.squash = Track(0.), Track((1.,1.)), Track((1.,1.))
        self.op, self.sword = Track(0), Track(0)

    def act(self, t, name, duration=0.12):
        self.pose.hold(max(self.pose.end, t-duration)).to(t, POSES[name], 'smooth')

    def move(self, t0, t1, dest, ease='smooth'):
        dx=dest[0]-self.pos.value[0]
        facing=(1. if dx>=0 else -1.,1.)
        if abs(dx)>1 and facing!=self.face.value:
            self.face.snap(t0,facing)
        self.pos.hold(t0).to(t1, tuple(dest), ease)

    def jump(self, t0, t1, dest, height=30):
        self.pos.hold(t0)
        start = self.pos.value
        facing=(1. if dest[0]>=start[0] else -1.,1.)
        if abs(dest[0]-start[0])>1 and facing!=self.face.value:
            self.face.snap(t0,facing)
        for i in range(1, 13):
            s = i/12
            x, y = mix(start, dest, s)
            self.pos.to(t0+(t1-t0)*s, (x, y-4*height*s*(1-s)))

    def run(self, t0, t1, dest, armed=False):
        self.move(t0, t1, dest, 'lin')
        cycle = RUN_S if armed else RUN
        for i in range(max(1, int((t1-t0)/0.10))):
            self.act(t0+i*.10, cycle[i % 6], .08)

    def land(self, t, letter=None):
        self.squash.hold(t-EPS).to(t, (1.16,.84)).to(t+.10, (.96,1.04), 'out').to(t+.20, (1.,1.), 'smooth')
        if letter:
            self.scene.dip(letter, t)
        self.scene.ring(*self.pos.at(t), t, 18)

    def hitstop(self,t,duration=.05):
        for track in (self.pos,self.pose,self.rot,self.squash):
            track.hold(t).hold(t+duration)

    def world(self, t, joint):
        p = self.pose.at(t)[joint]
        sx, _ = self.face.at(t)
        qx, qy = self.squash.at(t)
        x, y = p[0]*S*sx*qx, p[1]*S*qy
        a = math.radians(self.rot.at(t))
        return (self.pos.at(t)[0]+x*math.cos(a)-y*math.sin(a),
                self.pos.at(t)[1]+x*math.sin(a)+y*math.cos(a))

    def svg(self):
        ink, color = self.scene.p['fg'], self.scene.p[self.role]
        base = self.pose.k[0][1]
        # A paper-colored under-stroke keeps the figure readable over solid glyphs.
        # Both uses share one animated path, so the outline adds no morph track.
        body_id=f'body-{self.role}'
        body=(f'<defs><path id="{body_id}" d="{body_path(base)}">'+anim('d',self.pose,body_path)+'</path></defs>'
              f'<g fill="none" stroke-linecap="round" stroke-linejoin="round"><use href="#{body_id}" stroke="{self.scene.p["bg"]}" stroke-width="5.4"/>'
              f'<use href="#{body_id}" stroke="{color}" stroke-width="2.4"/></g>')
        hat = 'tricorn' if self.role == 'pirate' else 'bicorne'
        hatpath = lambda p: 'M'+'L'.join(f'{n(p["H"][0]+x)},{n(p["H"][1]+y)}' for x,y in HATS[hat])+'Z'
        head = f'<path d="{hatpath(base)}" fill="{ink}">'+anim('d',self.pose,hatpath)+'</path>'
        head = group(head, follow(self.pos, .055, .09), 'rotate')
        coatpath = lambda p: f'M{nums(p["P"])}l-7,6 3,-12 8,0 3,12Z'
        coat = f'<path d="{coatpath(base)}" fill="{color}" opacity=".7">'+anim('d',self.pose,coatpath)+'</path>'
        coat = group(coat, follow(self.pos, .09, .07), 'rotate')
        blade = lambda p: 'M'+pts([p['RH'],p['WT']])
        sword = f'<path d="{blade(base)}" fill="none" stroke="{ink}" stroke-width="1.3">'+anim('d',self.pose,blade)+'</path>'
        inner = f'<g transform="scale({S})">'+coat+body+head+opacity(sword,self.sword)+'</g>'
        return opacity(group(group(group(group(inner,self.squash,'scale'),self.face,'scale'),self.rot,'rotate'),self.pos),self.op)


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





class Letter:
    def __init__(self, scene, name, c0, c1):
        self.scene, self.name = scene, name
        self.c0, self.c1 = c0, c1
        self.box = X0+c0*CW, Y0, X0+c1*CW, Y0+len(art_rows())*CH
        self.cx = (self.box[0]+self.box[2])/2
        self.tr, self.rot, self.op = Track((0.,0.)), Track(0.), Track(1)
        self.pivot = (self.cx, self.box[3])
        self.fragments, self.slabs = [], []
        scene.defs.append(f'<g id="glyph-{name}">{letter_inner(scene.p,art_rows(),c0,c1)}</g>')

    def surface(self, row=0):
        """Exposed solid cells, derived from the editable ASCII grid."""
        rows = art_rows()
        choices = [c for c in range(self.c0,self.c1) if rows[row][c]=='█' and (row==0 or rows[row-1][c]!='█')]
        if not choices:
            choices = [c for c in range(self.c0,self.c1) if rows[row][c]=='█']
        if not choices:
            raise ValueError(f'{self.name} has no walkable surface at row {row}')
        return X0+(sum(choices)/len(choices)+.5)*CW, Y0+row*CH

    def svg(self):
        inner = f'<use href="#glyph-{self.name}"/>'
        pivot = self.pivot
        rotation = Track((0., *pivot))
        rotation.k = [(t,(v,*pivot),e) for t,v,e in self.rot.k]
        return opacity(group(group(inner,rotation,'rotate'),self.tr),self.op)+''.join(self.slabs+self.fragments)


def segment_cross(a, b, box):
    """First blade contact with a glyph bounding rectangle, in page coordinates."""
    dx,dy = b[0]-a[0], b[1]-a[1]
    lo,hi = 0.,1.
    for p,q in ((-dx,a[0]-box[0]),(dx,box[2]-a[0]),(-dy,a[1]-box[1]),(dy,box[3]-a[1])):
        if abs(p)<1e-9:
            if q<0:
                raise ValueError('Blade misses letter')
        elif p<0:
            lo=max(lo,q/p)
        else:
            hi=min(hi,q/p)
    if lo>hi:
        raise ValueError('Blade misses letter')
    return (a[0]+lo*dx,a[1]+lo*dy)


def half_plane(poly,a,b,c):
    """Clip a convex polygon to a*x+b*y <= c, retaining the blade's exact line."""
    result=[]
    for p,q in zip(poly,poly[1:]+poly[:1]):
        dp,dq=a*p[0]+b*p[1]-c,a*q[0]+b*q[1]-c
        if dp<=0:
            result.append(p)
        if (dp<0)!=(dq<0) and dp!=dq:
            s=dp/(dp-dq)
            result.append(mix(p,q,s))
    return result


class Scene:
    def __init__(self, theme):
        self.p, self.defs = PALETTES[theme], []
        self.back, self.props, self.fx, self.front = [], [], [], []
        self.pan, self.zoom, self.shake = Track((0.,0.)), Track((1.,1.)), Track((0.,0.))
        self.letters = {name:Letter(self,name,*cols) for name,cols in zip('ANSIL',LETTER_COLS)}
        self.pir = Char(self,'pirate',(-60.,20.))
        self.off = Char(self,'navy',(330.,-65.))
        self.contacts = []
        self.story()

    def ring(self,x,y,t,r=30,duration=.32):
        op=Track(0).snap(t, .7).to(t+duration,0.,'in')
        radius=Track(1.).hold(t).to(t+duration,r,'out')
        inner=f'<ellipse cx="{n(x)}" cy="{n(y)}" rx="1" ry="3" fill="none" stroke="{self.p["fg"]}" stroke-width="1.1">'+anim('rx',radius)+'</ellipse>'
        self.fx.append(opacity(inner,op))

    def glint(self,x,y,t,size=9):
        d=f'M{n(x-size)},{n(y)}h{n(size*2)}M{n(x)},{n(y-size)}v{n(size*2)}'
        self.fx.append(opacity(f'<path d="{d}" fill="none" stroke="{self.p["fg"]}" stroke-width="1.2"/>',Track(0).snap(t,1).to(t+.22,0)))

    def blast(self,x,y,t):
        """Open ink forks and an expanding ring, with a clear vertical silhouette."""
        rays=[]
        for i in range(7):
            a=math.pi*(1.08+i*.14)
            points=[(math.cos(a)*r,math.sin(a)*r) for r in (15,28,43)]
            points[1]=(points[1][0]+3,points[1][1]-2)
            rays.append('M'+'L'.join(f'{n(px)},{n(py)}' for px,py in points))
        ink=self.p['fg']
        shape=f'<path d="{"".join(rays)}" fill="none" stroke="{ink}" stroke-width="1.1" stroke-linecap="round"/><circle cy="-12" r="18" fill="none" stroke="{ink}" stroke-width=".8"/>'
        scale=Track((.3,.3)).hold(t).to(t+.38,(1.8,1.8),'out')
        self.fx.append(f'<g transform="translate({n(x)} {n(y)})">'+opacity(group(shape,scale,'scale'),Track(0).snap(t,1).to(t+.43,0.,'in'))+'</g>')

    def smear(self,actor,t0,t1):
        a,b=actor.world(t0,'N'),actor.world(t1,'N')
        if math.dist(a,b)<=42*S:
            return
        line=f'<path d="M{nums(a)}L{nums(b)}" stroke="{self.p[actor.role]}" stroke-width="1.4" fill="none"/>'
        self.fx.append(opacity(line,Track(0).snap(t1,.3).to(t1+.09,0.,'in')))

    def dip(self,name,t):
        pc=self.letters[name]
        pc.tr.hold(t).to(t+.055,(0.,4.),'out').to(t+.14,(0.,-1.),'out').to(t+.24,(0.,0.),'smooth')
        self.contacts.append(('foot',name,t))

    def jolt(self,t,strength=2):
        self.shake.hold(t)
        for dt,x,y in ((.03,1,-.5),(.08,-.5,.3),(.14,0,0)):
            self.shake.to(t+dt,(strength*x,strength*y),'out')

    def punch(self,t):
        self.zoom.hold(t).to(t+.08,(1.035,1.035),'out').to(t+.32,(1.,1.),'smooth')
        self.jolt(t,3)

    def rope(self,x,top,points,op):
        end=Track(points[0][1])
        for t,value in points[1:]:
            end.to(t,value,'smooth')
        line=lambda v:f'M{n(x)},{n(top)}Q{n((x+v[0])/2+8)},{n((top+v[1])/2)} {nums(v)}'
        self.props.append(opacity(f'<path d="{line(end.k[0][1])}" fill="none" stroke="{self.p["fg"]}" stroke-width="1.2">'+anim('d',end,line)+'</path>',op))

    def slice_s(self,times):
        pc=self.letters['S']; actor=self.off
        cuts=[]
        for t in times:
            a,b=actor.world(t,'RH'),actor.world(t,'WT')
            contact=segment_cross(a,b,pc.box)
            normal=(-(b[1]-a[1]),b[0]-a[0])
            cuts.append((*normal,normal[0]*contact[0]+normal[1]*contact[1]))
            self.contacts.append(('blade','S',t,contact))
            self.glint(*contact,t); self.ring(*contact,t,20)
        # Three actual blade lines split the shared glyph into four clipped pieces.
        # Pieces below an unmade cut coincide until that cut's timestamp.
        pc.op.snap(times[0],0)
        x0,y0,x1,y1=pc.box
        for i in range(4):
            poly=[(x0,y0),(x1,y0),(x1,y1),(x0,y1)]
            if i:
                a,b,c=cuts[i-1]
                poly=half_plane(poly,-a,-b,-c)
            if i<len(cuts):
                poly=half_plane(poly,*cuts[i])
            cid=f'shelf-{i}'
            self.defs.append(f'<clipPath id="{cid}"><polygon points="{pts(poly)}"/></clipPath>')
            tt=times[max(0,i-1)]
            tr=Track((0.,0.)).hold(tt).to(tt+.32,((i-1.5)*7.,3.+i*6),'out')
            pc.slabs.append(opacity(group(f'<g clip-path="url(#{cid})"><use href="#glyph-S"/></g>',tr),visible(times[0],22.30)))

    def shatter(self,pc,t,heal):
        """Four shards, one shared glyph; heal traverses the same samples backwards."""
        x0,y0,x1,y1=pc.box
        mx=(x0+x1)/2+CW*.12; my=(y0+y1)/2-CH*.15
        polygons=[[(x0,y0),(mx,y0),(mx+7,my),(x0,my+9)],
                  [(mx,y0),(x1,y0),(x1,my-6),(mx+7,my)],
                  [(x0,my+9),(mx+7,my),(mx-5,y1),(x0,y1)],
                  [(mx+7,my),(x1,my-6),(x1,y1),(mx-5,y1)]]
        # Blunt impact at the actual lower face of this glyph.
        impact=(pc.cx,pc.box[3]); self.contacts.append(('blast',pc.name,t,impact))
        if pc.op.value != 0:
            pc.op.snap(t,0)
        pc.op.snap(heal,1)
        for i,poly in enumerate(polygons):
            cx=sum(p[0] for p in poly)/4; cy=sum(p[1] for p in poly)/4
            dx,dy=cx-impact[0],cy-impact[1]
            dist=max(1,math.hypot(dx,dy)); force=100+50*rnd(ord(pc.name)+i)
            vx=force*dx/dist; vy=-100-force*.4; spin=(i-1.5)*65
            samples=[(0.,(0.,0.),0.)]
            x=y=angle=0.
            for step in range(1,19):
                vy+=700*.055; x+=vx*.055; y+=vy*.055; angle+=spin*.055
                radians=math.radians(angle)
                extent=max((px-cx)*math.sin(radians)+(py-cy)*math.cos(radians) for px,py in poly)
                if cy+y+extent>FLOOR-3:
                    y=FLOOR-3-cy-extent; vy=-abs(vy)*.28; vx*=.7; spin*=.65
                samples.append((step*.055,(x,y),angle))
            tr,rot=Track((0.,0.)),Track((0.,cx,cy))
            tr.hold(t); rot.hold(t)
            for dt,xy,a in samples[1:]:
                tr.to(t+dt,xy); rot.to(t+dt,(a,cx,cy))
            reverse_start=heal-samples[-1][0]
            tr.hold(reverse_start); rot.hold(reverse_start)
            for dt,xy,a in reversed(samples[:-1]):
                tt=heal-dt
                tr.to(tt,xy); rot.to(tt,(a,cx,cy))
            cid=f'fragment-{pc.name}-{i}'
            self.defs.append(f'<clipPath id="{cid}"><polygon points="{pts(poly)}"/></clipPath>')
            shard=f'<g clip-path="url(#{cid})"><use href="#glyph-{pc.name}"/></g>'
            pc.fragments.append(opacity(group(group(shard,rot,'rotate'),tr),visible(t,heal)))
        self.ring(pc.cx,pc.box[3],heal,50,.4)

    def story(self):
        p,ink=self.p,self.p['fg']; pir,off=self.pir,self.off
        A,N,SS,I,L=(self.letters[c] for c in 'ANSIL')
        atop,ntop,stop,itop,ledge=A.surface(),N.surface(),SS.surface(),I.surface(),L.surface(4)
        mid,bottom=SS.surface(2),SS.surface(4)
        # 00.6: the page reacts before anyone arrives.
        for i,c in enumerate('ANSIL'):
            self.dip(c,.6+i*.075)
        # 01.0: rope enters, A supplies the kick, L catches the landing.
        pir.op.snap(1.,1); pir.act(.9,'hang')
        pir.move(.9,1.5,(atop[0]-18,atop[1]-35))
        self.rope(atop[0]-60,-35,[(0,(-60.,-20.)),(.9,(-60.,-20.)),(1.5,(atop[0]-18,atop[1]-35-42*S)),(2.1,(atop[0]+60,-50.))],visible(1.,2.2))
        pir.act(1.55,'kick'); pir.jump(1.5,1.7,atop,12); pir.land(1.7,'A')
        pir.act(1.85,'tuck'); pir.jump(1.78,2.4,ledge,45)
        pir.rot.hold(1.8).to(2.32,360.).snap(2.35,0.)
        pir.act(2.36,'fall'); pir.act(2.47,'crouch'); pir.land(2.4,'L')
        self.smear(pir,1.86,2.0)
        # 02.6: I is a mast; both hands and the flag lag the climb.
        pir.move(2.55,2.8,(itop[0]+18,itop[1]+55))
        pir.act(2.7,'climb_left'); pir.act(2.9,'climb_right'); pir.move(2.8,3.15,itop)
        pir.act(3.15,'tie_flag'); pir.act(3.4,'tighten_knot')
        self.dip('I',3.16)
        flag_pos=Track((itop[0]+3,itop[1]-40)).hold(8.56)
        flag_pos.to(8.95,(itop[0]-65,itop[1]-31),'in').hold(9.7).to(10.25,(itop[0]-96,FLOOR-12),'in')
        flag_wave=Track(0.)
        for j in range(1,31):
            flag_wave.to(3.35+j*.18,(-1 if j%2 else 1)*4.,'smooth')
        flag_wave.hold(9.).to(9.7,0.)
        flag=f'<path d="M0,0V40M0,1Q14,-4 28,2L28,21Q14,15 0,20Z" fill="{ink}" stroke="{ink}" stroke-width="1.1"/>'
        self.props.append(opacity(group(group(flag,flag_wave,'rotate'),flag_pos),visible(3.3,10.6)))
        # 03.8: the notice hangs from the middle bar of S.
        poster=(mid[0]-25,mid[1]+4)
        pir.act(3.65,'wind_throw'); pir.act(3.82,'throw',.07)
        dagger=Track(pir.world(3.82,'RH')).hold(3.82).to(4.06,(poster[0]+25,poster[1]+4),'in')
        dagger.hold(8.4).to(8.8,(bottom[0],FLOOR-4),'in').hold(13.0).to(14.2,(550.,DECK-4),'in')
        dagger_op=visible(3.82,17.7)
        self.props.append(opacity(group(f'<path d="M-8,0H10M0,-3V3" fill="none" stroke="{ink}" stroke-width="1.6"/>',dagger),dagger_op))
        px,py=poster
        notice=(f'<path d="M{n(px)},{n(py)}h50v61l-7,-2 -7,3 -8,-3 -8,3 -10,-2 -10,1Z" fill="{p["bg"]}" stroke="{ink}" stroke-width="1"/>'
                f'<text x="{n(px+25)}" y="{n(py+13)}" text-anchor="middle" font-family="monospace" font-size="8" fill="{ink}">{html.escape(POSTER_HEAD)}</text>'
                f'<circle cx="{n(px+25)}" cy="{n(py+28)}" r="6" fill="none" stroke="{ink}"/>'
                f'<path d="M{n(px+15)},{n(py+23)}l5,-5 5,2 5,-2 5,5Z" fill="{ink}"/>'
                f'<text x="{n(px+25)}" y="{n(py+44)}" text-anchor="middle" font-family="monospace" font-size="6" fill="{ink}">{html.escape(POSTER_NAME)}</text>'
                f'<text x="{n(px+25)}" y="{n(py+55)}" text-anchor="middle" font-family="monospace" font-size="4" fill="{ink}">{html.escape(POSTER_REWARD)}</text>')
        paper=Track((0.,px+25,py+4)).hold(4.06).to(4.16,(8.,px+25,py+4),'out').to(4.4,(-4.,px+25,py+4),'smooth').to(4.65,(0.,px+25,py+4),'smooth')
        paper.hold(7.8).to(8.6,(-18.,px+25,py+4),'smooth')
        paperfall=Track((0.,0.)).hold(8.4).to(9.2,(-22.,FLOOR-py-62),'in')
        notice=f'<g transform="translate({n(px+25)} {n(py+4)}) scale(1.15) translate({n(-px-25)} {n(-py-4)})">'+notice+'</g>'
        self.props.append(opacity(group(group(notice,paper,'rotate'),paperfall),visible(4.06,12.9)))
        self.glint(px+25,py+4,4.06)
        pir.act(4.2,'stand'); pir.act(4.65,'look_left')
        # 04.8: N supplies a staircase, with a footfall on each exposed step.
        off.op.snap(4.8,1); off.act(4.7,'rope_slide')
        off.move(4.7,5.05,ntop)
        self.rope(ntop[0],-60,[(0,(ntop[0],-60.)),(4.7,(ntop[0],-60.)),(5.05,(ntop[0],ntop[1]-40*S)),(5.5,(ntop[0],-65.))],visible(4.8,5.6))
        for j,row in enumerate((1,2,3)):
            tt=5.12+j*.26
            off.act(tt,'brake' if j==2 else RUN[j])
            off.move(tt,tt+.18,N.surface(row),'in')
            self.dip('N',tt+.18)
        off.act(5.82,'look_right'); off.act(6.02,'look_left'); off.act(6.21,'double_take')
        off.act(6.4,'spyglass'); off.act(6.55,'spyglass_lower')
        spy=Track(off.world(6.4,'RH')).hold(6.6)
        self.props.append(opacity(group(f'<path d="M0,-3h19v6H0Z" fill="{p["bg"]}" stroke="{ink}"/>',spy),visible(6.28,6.58)))
        # 06.6: whistle and a chase down the S's three shelves.
        pir.act(6.6,'whistle'); pir.act(6.8,'tuck')
        pir.jump(6.72,7.03,stop,20); pir.land(7.03,'S')
        pir.act(7.08,'runA'); pir.jump(7.08,7.38,mid,18); pir.act(7.4,'peek')
        off.sword.snap(6.85,1)
        # The blade tip, not a separately typed cut coordinate, defines each contact.
        cut_times=(7.48,7.87,8.26)
        for j,(tt,surface) in enumerate(zip(cut_times,(stop,mid,bottom))):
            target=(surface[0],surface[1]+8)
            wt=POSES['chop']['WT']
            feet=(target[0]-wt[0]*S,target[1]-wt[1]*S)
            off.move(tt-.28,tt-.10,feet)
            if off.face.value!=(1.,1.):
                off.face.snap(tt-.09,(1.,1.))
            off.act(tt-.12,'wind_hi',.10); off.act(tt,'chop',.06)
            off.hitstop(tt)
        self.slice_s(cut_times)
        pir.act(7.55,'tuck'); pir.jump(7.46,7.83,bottom,18); pir.act(7.9,'balance')
        pir.act(8.2,'reach_rope')
        # 08.5: a rope saves the pirate; the flag blinds his pursuer.
        pir.jump(8.3,8.95,(itop[0]+30,itop[1]+20),90); pir.act(8.53,'hang'); pir.act(9.02,'brake')
        self.rope(itop[0],itop[1]-40,[(0,(bottom[0],bottom[1]-42*S)),(8.3,(bottom[0],bottom[1]-42*S)),(8.62,(itop[0]+35,itop[1]-85)),(8.95,(itop[0]+30,itop[1]+20-42*S)),(9.3,(itop[0]+60,itop[1]+12))],visible(8.3,9.35))
        off.move(8.31,8.73,(itop[0]-65,itop[1]+23)); off.act(8.52,'sw_wind'); off.act(8.69,'sw_cut',.07)
        self.glint(itop[0]+3,itop[1]-34,8.56)
        off.act(8.96,'blind'); off.act(9.25,'blind_swing'); off.act(9.5,'blind')
        # 09.6: the same sword cuts the I at the bottom, pivoting it into a mast.
        target=(I.cx,I.box[3]-9); wt=POSES['chop']['WT']
        off.move(9.5,9.85,(target[0]-wt[0]*S,target[1]-wt[1]*S),'in')
        if off.face.value!=(1.,1.):
            off.face.snap(9.86,(1.,1.))
        off.act(9.82,'wind_hi'); off.act(9.96,'chop',.08)
        contact=segment_cross(off.world(9.96,'RH'),off.world(9.96,'WT'),I.box)
        self.contacts.append(('blade','I',9.96,contact)); self.glint(*contact,9.96)
        off.hitstop(9.96)
        I.rot.hold(10.).to(10.6,-13.,'in').to(11.25,-48.,'in').to(12.,-88.,'in').to(12.14,-81.,'out').to(12.36,-88.,'in')
        I.tr.hold(10.).to(12.,(0.,FLOOR-I.box[3]-4),'in')
        pir.act(10.3,'push'); pir.move(9.2,10.4,(I.cx+12,I.box[3]-20))
        pir.act(10.75,'push_low'); pir.act(11.2,'teeter_left'); pir.jump(11.25,11.85,(I.cx+58,FLOOR),28); pir.act(11.85,'brake')
        off.act(10.6,'push'); off.act(11.1,'push_low'); off.jump(11.3,11.9,(I.cx-170,FLOOR),22); off.act(11.9,'shield')
        # 12.0: the rotated mast's tip supplies the impact and the hole's centre.
        angle=math.radians(-88)
        impact=(I.cx+(I.box[3]-I.box[1])*math.sin(angle),FLOOR-4)
        hole_x=(impact[0]+I.cx)/2; hole_r=126.
        self.jolt(12.,3); self.ring(*impact,12.,65,.5)
        crack=(f'M{n(impact[0])},{FLOOR}l-17,5 -14,-8 -26,8 -19,-5M{n(impact[0])},{FLOOR}'
               'l19,-7 24,11 17,-7 34,6 20,-4')
        dash=Track(1.).hold(12.).to(12.65,0.,'out')
        self.front.append(opacity(f'<path d="{crack}" fill="none" stroke="{ink}" stroke-width="1.5" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1">'+anim('stroke-dashoffset',dash)+'</path>',visible(12.,13.35)))
        pir.act(12.25,'look_left'); pir.act(12.65,'teeter_right'); off.act(12.4,'peek'); off.act(12.8,'teeter_left')
        # Page-minus-hole clip: the foreground deck hides legs during both crossings.
        opening=Track(0.).hold(12.8).to(13.45,1.,'smooth').hold(31.5).to(32.7,0.,'smooth')
        holepath=lambda q: f'M0,{FLOOR-2}H{W}V{FLOOR+32}H0Z M{n(hole_x-hole_r*q)},{FLOOR+9}a{n(max(.001,hole_r*q))},22 0 1 0 {n(2*hole_r*q)},0a{n(max(.001,hole_r*q))},22 0 1 0 {n(-2*hole_r*q)},0Z'
        self.defs.append('<clipPath id="page-minus-hole"><path clip-rule="evenodd" d="'+holepath(0)+'">'+anim('d',opening,holepath)+'</path></clipPath>')
        self.front.append(f'<g clip-path="url(#page-minus-hole)"><path d="M0,{FLOOR}H{W}v30H0Z" fill="{p["bg"]}"/><path d="M0,{FLOOR}H{W}" stroke="{p["rule"]}" stroke-width="1.3"/></g>')
        for name in 'ANSL':
            pc=self.letters[name]
            pc.rot.hold(12.8).to(13.45,5. if pc.cx<hole_x else -5.,'smooth').hold(21.8).to(22.2,0.)
        # 13.2: camera follows the fall into a second, persistent set.
        pir.act(13.1,'fall'); off.act(13.12,'fall')
        pir.move(13.,13.5,(hole_x+30,FLOOR+40),'in'); pir.move(13.5,14.4,(620.,DECK),'in')
        off.move(13.,13.5,(hole_x-35,FLOOR+35),'in'); off.move(13.5,14.45,(290.,DECK),'in')
        pir.rot.hold(13.3).to(14.35,360.).snap(14.38,0.)
        off.rot.hold(13.3).to(14.35,-360.).snap(14.38,0.)
        self.pan.hold(13.15).to(14.45,(0.,-340.),'smooth')
        pir.act(14.4,'crouch'); off.act(14.45,'lying'); pir.land(14.4); off.land(14.45)
        self.below_deck(hole_x)
        # 14.4: lantern swings; officer recovers while the pirate notices a barrel.
        pir.act(14.8,'look_left'); off.act(15.,'crouch'); off.act(15.25,'guard')
        pir.act(15.15,'shrug'); pir.jump(15.3,15.8,(550.,DECK-58),35); pir.act(15.8,'balance'); pir.land(15.8)
        # 15.4: the blade's contact leaves the sword in the first barrel.
        off.move(15.28,15.55,(338.,DECK)); off.act(15.5,'sw_wind'); off.act(15.68,'chop',.08)
        swordtip=off.world(15.68,'WT'); swordhand=off.world(15.68,'RH')
        stuck=f'<path d="M{nums(swordhand)}L{nums(swordtip)}" stroke="{ink}" stroke-width="1.8"/>'
        wobble=Track((0.,*swordtip)).hold(15.68)
        for j in range(12):
            wobble.to(15.78+j*.14,((-1 if j%2 else 1)*(5-j*.3),*swordtip),'smooth')
        self.props.append(opacity(group(stuck,wobble,'rotate'),visible(15.68,20.05)))
        off.sword.snap(15.68,0); off.act(15.92,'pull'); self.glint(*swordtip,15.68)
        # 16.4: a rolling barrel carries the pirate towards the fallen dagger.
        for j in range(6):
            tt=16.+j*.23
            pir.act(tt,'teeter_left' if j%2 else 'teeter_right')
            off.act(tt+.08,'pull_hard' if j%2 else 'pull')
        pir.move(16.,17.3,(605.,DECK-58),'lin'); pir.act(17.45,'balance_low')
        pir.jump(17.5,17.76,(550.,DECK),12); pir.act(17.76,'light')
        # 17.8: a callback to the dagger lights a fuse drawn as one path.
        pir.act(17.94,'strike_flint'); self.glint(*pir.world(17.94,'RH'),17.94,6)
        pir.act(18.16,'look_left'); off.act(17.65,'pull_release'); off.act(18.05,'double_take'); off.act(18.45,'chase_spark')
        pir.jump(18.4,18.82,(670.,DECK),24); pir.act(18.85,'shield')
        off.run(18.65,19.22,(450.,DECK)); off.act(19.3,'chase_spark'); off.move(19.3,19.74,(475.,DECK))
        off.act(19.8,'shield'); pir.act(19.7,'peek')
        # 20.0: three thin ink explosions and camera punches; no filled flashes.
        for j,x in enumerate((365.,455.,605.)):
            tt=20.+j*.58
            self.ring(x,DECK-20,tt,90,.48); self.blast(x,DECK-25,tt); self.punch(tt)
        pir.act(20.12,'shield'); pir.act(20.7,'peek'); pir.act(21.2,'fall')
        off.act(20.15,'hit'); off.act(20.8,'shield'); off.act(21.25,'fly')
        # 22.0: camera returns; characters emerge from the hole and strike the letters.
        pir.move(21.3,21.9,(hole_x+20,470.),'out'); pir.move(21.9,22.38,(L.cx,190.),'out')
        off.move(21.35,21.95,(hole_x-25,460.),'out'); off.move(21.95,22.42,(SS.cx,190.),'out')
        pir.rot.hold(21.35).to(22.42,360.).snap(22.45,0.)
        off.rot.hold(21.4).to(22.45,-540.).snap(22.48,0.)
        self.smear(pir,22.03,22.18); self.smear(off,22.03,22.18)
        self.pan.hold(21.65).to(22.7,(0.,0.),'smooth')
        I.op.snap(13.35,0); I.tr.hold(21.8).to(22.,(0.,0.)); I.rot.hold(21.8).to(22.,0.)
        for j,pc in enumerate(self.letters.values()):
            self.shatter(pc,22.3+j*.035,26.05+j*.38)
        self.jolt(22.38,3)
        pir.act(22.4,'fall'); pir.jump(22.42,23.25,(L.cx+24,FLOOR),25); pir.act(23.25,'crouch')
        off.act(22.5,'fly'); off.jump(22.48,23.35,(L.cx+4,L.box[3]-20),55); off.act(23.3,'lying'); off.op.snap(23.42,0)
        self.ring(L.cx,L.box[3]-20,23.4,28)
        # 23.4: L holds the officer. Pirate waits, reacting to the returning rubble.
        pir.act(23.6,'look_left'); pir.act(24.1,'shrug'); pir.act(24.65,'double_take')
        pir.act(25.2,'shield'); pir.act(25.85,'peek'); pir.act(26.5,'look_left'); pir.act(27.1,'stand')
        # 25.0: each letter reverses its own fragment simulation, left to right.
        pir.jump(27.4,27.95,ledge,42); pir.act(27.92,'crouch'); pir.land(27.95,'L')
        # 28.2: a hat tip; only the trapped officer's hand is visible above the L.
        pir.act(28.25,'hat_tip'); pir.act(28.8,'bow'); pir.act(29.2,'look_left')
        handx,handy=ledge[0]-32,ledge[1]
        surrender=Track((0.,handx,handy)).hold(28.25)
        for j in range(8):
            surrender.to(28.45+j*.25,((-1 if j%2 else 1)*14.,handx,handy),'smooth')
        surrender.to(30.5,(0.,handx,handy))
        hand=(f'<path d="M{n(handx)},{n(handy+5)}v-27l4,-4" stroke="{p["navy"]}" stroke-width="2.4" fill="none"/>'
              f'<path d="M{n(handx+4)},{n(handy-31)}v-23m0,0q10,-5 22,1v15q-10,-5 -22,0" fill="{p["bg"]}" stroke="{ink}" stroke-width="1.1"/>')
        self.props.append(opacity(group(hand,surrender,'rotate'),visible(28.35,30.8)))
        pir.act(29.75,'shrug'); pir.act(30.4,'stand'); pir.act(30.9,'look_right')
        # 31.0: the entrance rope returns. Exit and repair finish before the seam.
        exitx=ledge[0]
        self.rope(exitx,-45,[(0,(exitx,-45.)),(30.95,(exitx,-45.)),(31.35,(exitx,ledge[1]-42*S)),(31.7,(exitx,ledge[1]-42*S)),(32.7,(exitx,-120.))],visible(31.,32.8))
        pir.act(31.25,'reach_rope'); pir.act(31.55,'hang'); pir.move(31.55,32.7,(exitx,-65.),'smooth'); pir.op.snap(32.75,0)
        self.ring(hole_x,FLOOR,32.65,35,.35)

    def below_deck(self,hole_x):
        p,ink=self.p,self.p['fg']
        # World-space second set. The camera reveals it instead of swapping scenes.
        self.back.append(f'<path d="M90,410H740M90,{DECK}H740M105,410V{DECK}M725,410V{DECK}" fill="none" stroke="{p["rule"]}" stroke-width="2"/>')
        for x in (135,695):
            self.back.append(f'<path d="M{x},410v240m-8,-238 16,20m-16,199 16,19" fill="none" stroke="{p["rule"]}" stroke-width="1"/>')
        lanternrot=Track((0.,415.,410.)).hold(13.4)
        for j in range(1,32):
            lanternrot.to(13.4+j*.27,((8 if j%2 else -8)*(1-j/40),415.,410.),'smooth')
        lantern=f'<path d="M415,410v40m-9,0h18l4,27h-26Z M415,457v12" fill="{p["bg"]}" stroke="{ink}" stroke-width="1.3"/>'
        self.back.append(group(lantern,lanternrot,'rotate'))
        for i,x in enumerate((365.,455.,550.)):
            body=(f'<path d="M-22,-57Q-34,-28 -22,0H22Q34,-28 22,-57Z" fill="{p["bg"]}" stroke="{ink}" stroke-width="1.4"/>'
                  f'<path d="M-27,-44h54M-28,-14h56M-12,-56Q-19,-28 -12,0M12,-56Q19,-28 12,0M0,-56V0" fill="none" stroke="{ink}" stroke-width=".9"/>')
            tr=Track((x,float(DECK)))
            if i==2:
                tr.hold(16.).to(17.3,(605.,float(DECK)),'lin')
            rotation=Track((0.,0.,-28.))
            if i==2:
                rotation.hold(16.).to(17.3,(110.,0.,-28.),'lin')
            self.props.append(opacity(group(group(body,rotation,'rotate'),tr),visible(13.25,20.+i*.58)))
        fuse_points=[(571.,DECK-20),(558.,DECK-7),(515.,DECK-7),(480.,DECK-10),(455.,DECK-10),(410.,DECK-5),(365.,DECK-10)]
        fuse='M'+'L'.join(f'{n(x)},{n(y)}' for x,y in fuse_points)
        self.back.append(opacity(f'<path d="{fuse}" stroke="{ink}" stroke-width="1" fill="none" stroke-dasharray="3 3"/>',visible(13.3,20.1)))
        spark=Track(fuse_points[0]).hold(17.94)
        for i,pt in enumerate(fuse_points[1:]):
            spark.to(17.94+(20.-17.94)*(i+1)/(len(fuse_points)-1),pt)
        shape=f'<path d="M-4,0H4M0,-4V4M-3,-3L3,3" stroke="{ink}" stroke-width="1"/>'
        self.props.append(opacity(group(shape,spark),visible(17.94,20.03)))

    def svg(self):
        scene=''.join(self.back)+''.join(pc.svg() for pc in self.letters.values())+''.join(self.props)
        scene+=self.pir.svg()+self.off.svg()+''.join(self.front)+''.join(self.fx)
        scene=group(scene,self.pan)
        scene=f'<g transform="translate({W/2} {H/2})">'+group(f'<g transform="translate({-W/2} {-H/2})">'+scene+'</g>',self.zoom,'scale')+'</g>'
        scene=group(scene,self.shake)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">'
                '<title id="title">ANSIL — below deck</title><desc id="desc">'+html.escape(ALT)+'</desc>'
                '<defs>'+''.join(self.defs)+'</defs>'
                f'<rect width="{W}" height="{H}" fill="{self.p["bg"]}"/>'+scene+'</svg>')


def lint_svg(svg):
    """Check the output itself, including the exact intervals that change on screen."""
    root=ET.fromstring(svg)
    nodes=list(root.iter()); parents={child:parent for parent in nodes for child in parent}
    ids=[el.attrib['id'] for el in nodes if 'id' in el.attrib]
    if len(ids)!=len(set(ids)):
        raise ValueError('Duplicate SVG IDs')
    for ref in re.findall(r'(?:url\(#|href="#)([^)" ]+)',svg):
        if ref not in ids:
            raise ValueError(f'Missing SVG reference: {ref}')
    records=[]; opacity_tracks={}; events=[]; instances={}
    for el in nodes:
        if el.tag.rsplit('}',1)[-1]=='use':
            instances.setdefault(el.attrib.get('href','').lstrip('#'),[]).append(el)
    for el in nodes:
        tag=el.tag.rsplit('}',1)[-1]
        if tag in ('script','foreignObject','filter','image','style'):
            raise ValueError(f'Unsupported SVG element: {tag}')
        for key,value in el.attrib.items():
            if key.startswith('on') or (key.endswith('href') and not value.startswith('#')):
                raise ValueError('External or executable SVG content')
        if tag not in ('animate','animateTransform'):
            continue
        vals=el.attrib['values'].split(';'); ts=[float(x)*T for x in el.attrib['keyTimes'].split(';')]
        if len(vals)!=len(ts) or ts[0]!=0 or abs(ts[-1]-T)>1e-6 or any(a>=b for a,b in zip(ts,ts[1:])):
            raise ValueError('Invalid animation timing')
        if len(el.attrib['keySplines'].split(';'))!=len(vals)-1:
            raise ValueError('Invalid spline count')
        if el.attrib['attributeName']=='d':
            signatures={re.sub(r'[-+]?(?:\d*\.)?\d+','#',v) for v in vals}
            if len(signatures)!=1:
                raise ValueError('Incompatible path morph commands')
        parent=parents[el]
        if el.attrib['attributeName']=='opacity':
            opacity_tracks[parent]=(ts,list(map(float,vals)))
        for i,(a,b) in enumerate(zip(ts,ts[1:])):
            if vals[i]!=vals[i+1]:
                events.extend(((a,1,parent),(b,-1,parent)))
        records.append(el)
    def shown(el,t):
        while el is not None:
            if el in opacity_tracks:
                ts,vals=opacity_tracks[el]; alpha=vals[-1]
                for i,b in enumerate(ts[1:]):
                    if t<=b:
                        s=(t-ts[i])/(b-ts[i]); alpha=vals[i]+(vals[i+1]-vals[i])*s; break
                if alpha<=0:
                    return False
            elif float(el.attrib.get('opacity','1'))==0:
                return False
            el=parents.get(el)
        return True
    events.sort(key=lambda x:(x[0],x[1]))
    active=Counter(); peak=0; when=0.
    for i,(t,delta,target) in enumerate(events):
        active[target]+=delta
        if active[target]==0:
            del active[target]
        if i+1<len(events) and events[i+1][0]>t:
            sample=(t+events[i+1][0])/2
            targets={target for el in active for target in instances.get(el.attrib.get('id'),[el])}
            count=sum(shown(el,sample) for el in targets)
            if count>peak:
                peak,when=count,sample
    size=len(svg.encode('utf-8'))
    if size>SIZE_LIMIT:
        raise ValueError(f'SVG size {size:,} exceeds {SIZE_LIMIT:,}')
    if peak>ACTIVE_LIMIT:
        raise ValueError(f'{peak} changing elements at {when:.3f}s exceed {ACTIVE_LIMIT}')
    return dict(bytes=size,elements=len(nodes),animation_tracks=len(records),peak_changing_elements=peak,
                peak_time=round(when,3),poses=len(POSES),duration=T)


def engine_checks():
    # A past timestamp must never silently move the choreography.
    tr=Track(0.).to(2.,1.)
    try:
        tr.to(1.,2.)
    except ValueError:
        pass
    else:
        raise AssertionError('Track accepted an out-of-order key')
    assert segment_cross((-1.,5.),(8.,5.),(0.,0.,10.,10.))==(0.,5.)
    assert len(POSES)>=60 and len(BEATS) in range(20,25)
    for pose in POSES.values():
        assert set(pose)==set(JOINTS)
    rows=art_rows()
    assert len(LETTER_COLS)==5 and all(b<=len(rows[0]) for _,b in LETTER_COLS)


def static_svg(svg):
    root=ET.fromstring(svg)
    for parent in list(root.iter()):
        for child in list(parent):
            if child.tag.rsplit('}',1)[-1] in ('animate','animateTransform'):
                parent.remove(child)
    ET.register_namespace('','http://www.w3.org/2000/svg')
    return ET.tostring(root,encoding='unicode')


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
                cols,tw,th=6,332,144
                sheet=Image.new('RGB',(cols*tw,math.ceil(len(indices)/cols)*(th+18)),PALETTES[theme]['bg'])
                draw=ImageDraw.Draw(sheet)
                for j,i in enumerate(indices):
                    with Image.open(folder/f'frame-{i:04d}.png') as im:
                        sheet.paste(im.resize((tw,th)),((j%cols)*tw,(j//cols)*(th+18)))
                    draw.text(((j%cols)*tw+6,(j//cols)*(th+18)+th+2),f'{i/fps:05.2f}s',fill=PALETTES[theme]['fg'])
                sheet.save(outdir/f'{theme}-{name}.jpg',quality=88)
            # A compact 24-beat overview is useful next to the full act sheets.
            sheet=Image.new('RGB',(3*415,8*198),PALETTES[theme]['bg']); draw=ImageDraw.Draw(sheet)
            for i,(t,_,_) in enumerate(BEATS):
                fi=min(frame_count-1,round((t+.28)*fps))
                with Image.open(folder/f'frame-{fi:04d}.png') as im:
                    sheet.paste(im.resize((415,180)),((i%3)*415,(i//3)*198))
                draw.text(((i%3)*415+7,(i//3)*198+181),f'{fi/fps:05.2f}s',fill=PALETTES[theme]['fg'])
            sheet.save(outdir/f'{theme}-storyboard.jpg',quality=92)
            if export:
                source=str(folder/'frame-%04d.png')
                subprocess.run([ffmpeg,'-y','-loglevel','error','-framerate',str(fps),'-i',source,'-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(outdir/f'raid-{theme}.mp4')],check=True)
                subprocess.run([ffmpeg,'-y','-loglevel','error','-framerate',str(fps),'-i',source,'-filter_complex','[0:v]split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer','-loop','0',str(outdir/f'raid-{theme}.gif')],check=True)
            # Exercise the actual image embedding mode in both desktop and mobile widths.
            embed=outdir/f'{theme}-embed.html'
            embed.write_text(f'<!doctype html><meta charset="utf-8"><style>body{{margin:0}}img{{display:block;width:100%}}</style><img src="{path.resolve().as_uri()}" alt="raid">',encoding='utf-8')
            pg.goto(embed.resolve().as_uri())
            pg.wait_for_function('document.querySelector("img").complete && document.querySelector("img").naturalWidth > 0')
            for width in (830,390):
                pg.set_viewport_size({'width':width,'height':max(1,round(width*H/W))})
                pg.screenshot(path=str(outdir/f'{theme}-embed-{width}.png'))
            pg.set_viewport_size({'width':W,'height':H})
            qa[theme]=dict(seam_pixels_equal=seam,repeat_pixels_equal=loop,img_embedding=True,frames=frame_count,fps=fps)
        b.close()
    (outdir/'render-report.json').write_text(json.dumps(qa,indent=2)+'\n',encoding='utf-8')
    return qa


def bundle(outdir,files):
    destination=outdir/'ansil-raid.zip'
    source=Path(__file__).resolve().parent
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
        for name in ('make_raid.py','test_raid.py','README.md','preview.html','QA.md'):
            path=source/name
            if path.exists():
                archive.write(path,'raid/'+name)
        root_readme=source.parent/'README.md'
        if root_readme.exists():
            archive.write(root_readme,'README.md')
        for name in ('validation.json','raid-light-static.svg','raid-dark-static.svg'):
            archive.write(outdir/name,'raid/'+name)
        for path in files.values():
            archive.write(path,'raid/'+path.name)
        for path in sorted((outdir/'preview').glob('*')):
            if path.is_file() and path.suffix in ('.jpg','.gif','.mp4','.json','.png'):
                archive.write(path,'raid/preview/'+path.name)
    print(f'Bundle: {destination}',flush=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out',type=Path,default=Path(__file__).resolve().parent)
    ap.add_argument('--preview',action='store_true')
    ap.add_argument('--export',action='store_true',help='GIF, MP4 and zip; requires --preview')
    ap.add_argument('--check',action='store_true',help='fail if committed SVGs differ; do not write')
    ap.add_argument('--fps',type=int,default=12)
    ap.add_argument('--browser',help='optional Chromium or Chrome executable path')
    args=ap.parse_args()
    if args.export and not args.preview:
        ap.error('--export requires --preview')
    if args.check and (args.preview or args.export):
        ap.error('--check cannot be combined with --preview or --export')
    if not 1<=args.fps<=60:
        ap.error('--fps must be between 1 and 60')
    engine_checks()
    reports,files,outputs={},{},{}
    for theme in PALETTES:
        scene=Scene(theme); svg=scene.svg()
        if svg!=Scene(theme).svg():
            raise ValueError('Generator is not deterministic')
        reports[theme]=lint_svg(svg)
        reports[theme]['sha256']=hashlib.sha256(svg.encode()).hexdigest()
        reports[theme]['geometry_contacts']=len(scene.contacts)
        files[theme]=args.out/f'raid-{theme}.svg'
        outputs[files[theme]]=svg
        outputs[args.out/f'raid-{theme}-static.svg']=static_svg(svg)
        print(f'{theme}: {reports[theme]}',flush=True)
    if args.check:
        for path,content in outputs.items():
            if not path.exists() or path.read_text(encoding='utf-8')!=content:
                raise ValueError(f'Stale generated asset: {path}')
        print('Generated assets are current.')
        return
    args.out.mkdir(parents=True,exist_ok=True)
    for path,content in outputs.items():
        path.write_text(content,encoding='utf-8')
    (args.out/'validation.json').write_text(json.dumps(reports,indent=2)+'\n',encoding='utf-8')
    if args.preview:
        preview(args.out/'preview',files,args.fps,args.export,args.browser)
    if args.export:
        bundle(args.out,files)


if __name__=='__main__':
    try:
        main()
    except (ValueError,RuntimeError) as exc:
        print(f'raid: {exc}',file=sys.stderr)
        sys.exit(1)
