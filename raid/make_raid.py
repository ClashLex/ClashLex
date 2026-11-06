#!/usr/bin/env python3
"""ANSIL: Below deck. A joint-driven, self-contained SVG short.

Build: python raid/make_raid.py
Check: python raid/make_raid.py --check
Render: python raid/make_raid.py --preview --export [--browser PATH]
The engine uses the standard library. Rendering uses Playwright and Pillow;
video export additionally needs ffmpeg or imageio-ffmpeg.
"""
import argparse
from bisect import bisect_right
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
CW, CH, X0, Y0 = 15, 22, 137, 116
FLOOR, DECK, SCALE = 306, 646, 1.08
SIZE_LIMIT, ACTIVE_LIMIT = 750_000, 60
EPS = .002
PALETTES = {
    'light': dict(bg='#faf8f3', fg='#252b30', rule='#c7c5bb', pirate='#ad4c35', navy='#345c85'),
    'dark': dict(bg='#11171d', fg='#e0e2dc', rule='#414b52', pirate='#eb967b', navy='#8eafda'),
}
ALT = ('ANSIL becomes a pirate stage: a rope arrival, a flag on the I, and an '
       'officer chasing a pirate down the S. A blind swing fells the I and '
       'breaks the deck. Below, a stuck sword and a lit fuse cause a barrel '
       'blast. The shattered letters rebuild, and a surrender flag emerges from L.')
ACTS = [('01-arrival', 0, 6.6), ('02-chase', 6.6, 13.2),
        ('03-below-deck', 13.2, 22), ('04-return', 22, 34)]
BEATS = [
    (.60, 'A distant footfall ripples through ANSIL', 'A to L / footfall'),
    (1.00, 'The pirate swings in, kicks A, and lands on L', 'rope / A apex / L ledge'),
    (2.35, 'A climb turns I into a flag mast', 'I / flag'),
    (3.45, 'A dagger pins the wanted notice to S', 'S / dagger / poster'),
    (4.50, 'An officer slides down onto the N staircase', 'N / rope'),
    (5.50, 'Poster, pirate, poster; a spyglass double-take', 'poster / recognition'),
    (6.60, 'A whistle starts the chase down S', 'S shelves'),
    (7.15, 'Three connected swings separate the shelves', 'S / sword'),
    (8.70, 'The pirate escapes on the flag rope', 'flag / rope'),
    (9.25, 'A cut rope drops the flag over the officer', 'flag / blindness'),
    (9.95, 'A blind swing cuts the foot of I', 'I / blade'),
    (10.60, 'Both brace against the falling mast', 'I / resistance'),
    (12.00, 'The mast hits; a crack opens the deck', 'I / hole'),
    (13.20, 'The page gives way; a fall reveals below deck', 'hole / camera'),
    (14.50, 'A landing, a look up, and a renewed pursuit', 'lantern / barrels'),
    (15.30, 'The sword sticks; its owner pulls twice', 'sword / barrel'),
    (16.50, 'The pirate walks a barrel under his feet', 'barrel / balance'),
    (17.80, 'The dagger returns to strike the fuse', 'dagger / fuse'),
    (18.60, 'The officer chases the spark; the pirate takes cover', 'fuse / sword'),
    (20.00, 'Two blasts, a pause, then the third barrel', 'barrels / anticipation'),
    (22.00, 'They burst upward through ANSIL', 'hole / letters'),
    (23.30, 'L catches the officer; fragments fall and reverse', 'L / visible repair'),
    (28.00, 'A hat tip receives a very small surrender flag', 'flag / L'),
    (31.00, 'The rope returns and the page closes behind them', 'rope / deck'),
]
ART_RAW = [
    '█████╗ ███╗   ██╗███████╗██╗██╗     ',
    '██╔══██╗████╗  ██║██╔════╝██║██║     ',
    '███████║██╔██╗ ██║███████╗██║██║     ',
    '██╔══██║██║╚██╗██║╚════██║██║██║     ',
    '██║  ██║██║ ╚████║███████║██║███████╗',
    '╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝╚═╝╚══════╝',
]
LETTER_COLS = [(0, 8), (8, 18), (18, 26), (26, 29), (29, 37)]
EASINGS = {'linear': (0, 0, 1, 1), 'ease': (.42, 0, .58, 1),
           'in': (.55, 0, 1, 1), 'out': (0, 0, .25, 1)}


def num(x):
    s = f'{x:.3f}'.rstrip('0').rstrip('.')
    return '0' if s in ('', '-0') else s


def values(v):
    return ' '.join(num(x) for x in v) if isinstance(v, (tuple, list)) else num(v)


def add(a, b):
    return a[0]+b[0], a[1]+b[1]


def sub(a, b):
    return a[0]-b[0], a[1]-b[1]


def mul(a, k):
    return a[0]*k, a[1]*k


def lerp(a, b, u):
    if isinstance(a, (list, tuple)):
        return tuple(lerp(x, y, u) for x, y in zip(a, b))
    return a+(b-a)*u


def rotate(p, angle):
    a = math.radians(angle)
    return p[0]*math.cos(a)-p[1]*math.sin(a), p[0]*math.sin(a)+p[1]*math.cos(a)


def ease(u, kind):
    if kind == 'linear' or u in (0, 1):
        return u
    x1, y1, x2, y2 = EASINGS[kind]
    lo, hi = 0., 1.
    for _ in range(26):
        s = (lo+hi)/2
        if 3*(1-s)**2*s*x1+3*(1-s)*s*s*x2+s**3 < u:
            lo = s
        else:
            hi = s
    return 3*(1-s)**2*s*y1+3*(1-s)*s*s*y2+s**3


class Curve:
    """A property timeline. Time never moves to accommodate an authoring error."""
    def __init__(self, value):
        self.keys = [(0., value, 'linear')]

    def key(self, t, value, easing='linear'):
        t = round(t, 6)
        if not 0 <= t <= T or easing not in EASINGS:
            raise ValueError(f'Invalid key {t}, {easing}')
        if t == self.keys[-1][0] and value == self.keys[-1][1]:
            return self
        if t <= self.keys[-1][0]:
            raise ValueError(f'Conflicting or past key {t}; previous {self.keys[-1][0]}')
        self.keys.append((t, value, easing))
        return self

    def hold(self, t):
        return self.key(t, self.keys[-1][1])

    def go(self, start, end, value, easing='ease'):
        return self.hold(start).key(end, value, easing)

    def step(self, t, value):
        return self.hold(t-EPS).key(t, value)

    def at(self, t):
        i = bisect_right([k[0] for k in self.keys], t)-1
        if i < 0:
            return self.keys[0][1]
        if i >= len(self.keys)-1:
            return self.keys[-1][1]
        a, x, _ = self.keys[i]
        b, y, e = self.keys[i+1]
        return lerp(x, y, ease((t-a)/(b-a), e))

    def finished(self):
        return self.keys if self.keys[-1][0] == T else self.keys+[(T, self.keys[-1][1], 'linear')]


def animation(attribute, track, formatter=values, transform=None):
    keys = track.finished()
    rendered = [formatter(v) for _, v, _ in keys]
    if len(set(rendered)) == 1:
        return ''
    tag = 'animateTransform' if transform else 'animate'
    typ = f' type="{transform}"' if transform else ''
    return (f'<{tag} attributeName="{attribute}"{typ} dur="{num(T)}s" repeatCount="indefinite" '
            'calcMode="spline" keyTimes="'+';'.join(num(t/T) if t in (0, T) else f'{t/T:.8f}' for t, _, _ in keys)+'" '
            'values="'+';'.join(rendered)+'" keySplines="'+
            ';'.join(values(EASINGS[e]) for _, _, e in keys[1:])+'"/>')


def group(content, track=None, kind='translate', **attrs):
    attributes = ''.join(f' {k.replace("_", "-")}="{html.escape(str(v), quote=True)}"' for k, v in attrs.items())
    if track is None:
        return f'<g{attributes}>{content}</g>'
    initial = values(track.keys[0][1])
    return f'<g transform="{kind}({initial})"{attributes}>'+animation('transform', track, transform=kind)+content+'</g>'


def opacity(content, track):
    return f'<g opacity="{num(track.keys[0][1])}">'+animation('opacity', track)+content+'</g>'


def visible(start, end):
    return Curve(0.).step(start, 1.).step(end, 0.)


def path(points):
    return 'M'+'L'.join(f'{num(x)},{num(y)}' for x, y in points)


def two_bone(origin, target, upper, lower, bend=1):
    """Return the elbow/knee and attainable endpoint, preserving both lengths."""
    dx, dy = sub(target, origin)
    distance = math.hypot(dx, dy)
    d = min(upper+lower-.00001, max(abs(upper-lower)+.00001, distance))
    direction = math.atan2(dy, dx)
    offset = math.acos(max(-1, min(1, (upper*upper+d*d-lower*lower)/(2*upper*d))))
    side = 1 if bend >= 0 else -1
    joint = add(origin, (upper*math.cos(direction+side*offset), upper*math.sin(direction+side*offset)))
    end = add(origin, (d*math.cos(direction), d*math.sin(direction)))
    return joint, end


def pose(hip=(0, -24), lean=0, look=0, left=(-12, -25), right=(12, -25),
         feet=((-7, 0), (8, 0)), blade=-65, bends=(-1, 1, 1, 1)):
    return (*hip, lean, look, *left, *right, *feet[0], *feet[1], blade, *bends)


# Silhouettes are authored as intentions. Joint positions are solved, never drawn
# independently; the same wrist controls the sword, dagger, spyglass and rope.
POSES = {
    'rest': pose(),
    'breathe': pose(hip=(0, -24.6), lean=.6, left=(-12, -26), right=(12, -26)),
    'listen': pose(lean=-3, look=-3, right=(14, -40)),
    'look_left': pose(lean=-2, look=-5, left=(-12, -29)),
    'look_right': pose(lean=3, look=5, right=(13, -29)),
    'double_take': pose(hip=(-3, -23), lean=-6, look=-5, right=(15, -38)),
    'hips': pose(left=(-11, -29), right=(11, -29)),
    'shrug': pose(hip=(0, -23), left=(-19, -42), right=(19, -42), bends=(1, -1, 1, 1)),
    'point': pose(lean=4, look=4, right=(27, -41)),
    'scope_raise': pose(left=(-7, -31), right=(14, -45)),
    'scope': pose(lean=2, look=4, left=(9, -42), right=(18, -48)),
    'scope_recoil': pose(hip=(-4, -23), lean=-7, look=-4, right=(10, -48)),
    'whistle': pose(lean=-2, right=(6, -48), left=(-14, -25)),
    'hat_tip': pose(lean=-3, look=-2, right=(10, -57)),
    'bow': pose(hip=(-4, -23), lean=14, look=3, right=(22, -31)),
    'dust_left': pose(lean=-3, right=(-10, -28), left=(-14, -19)),
    'dust_right': pose(lean=2, left=(10, -28), right=(14, -19)),
    'crouch': pose(hip=(-2, -14), lean=7, left=(-13, -13), right=(17, -17), feet=((-12, 0), (13, 0))),
    'compress': pose(hip=(0, -11), lean=7, left=(-15, -17), right=(19, -17), feet=((-14, 0), (15, 0))),
    'rise': pose(hip=(0, -20), lean=3, left=(-14, -24), right=(14, -24)),
    'takeoff': pose(hip=(0, -25), lean=9, left=(-14, -35), right=(19, -49), feet=((-9, -3), (0, 0))),
    'tuck': pose(hip=(0, -24), lean=5, left=(-13, -43), right=(19, -43), feet=((-15, -13), (16, -15))),
    'fall': pose(hip=(0, -24), lean=-4, left=(-21, -47), right=(17, -52), feet=((-12, -3), (14, -6))),
    'hang': pose(hip=(0, -24), lean=0, left=(-6, -62), right=(9, -60), feet=((-10, -4), (13, -6))),
    'swing': pose(hip=(-4, -24), lean=12, left=(13, -58), right=(20, -54), feet=((-24, -13), (12, -7))),
    'kick_apex': pose(hip=(1, -23), lean=-8, left=(-5, -60), right=(11, -51), feet=((-12, -4), (22, -11))),
    'climb_left': pose(hip=(0, -24), lean=4, left=(8, -61), right=(14, -37), feet=((-14, -7), (13, -18))),
    'climb_right': pose(hip=(0, -24), lean=4, left=(14, -37), right=(8, -61), feet=((-12, -18), (14, -7))),
    'tie_low': pose(hip=(0, -22), lean=8, left=(17, -34), right=(20, -37)),
    'tie_high': pose(hip=(0, -24), lean=4, left=(12, -56), right=(17, -55)),
    'throw_draw': pose(lean=-6, left=(13, -35), right=(-21, -49)),
    'throw_release': pose(lean=12, look=3, right=(31, -43), left=(-9, -25)),
    'throw_follow': pose(hip=(4, -22), lean=10, right=(28, -31), left=(-8, -24)),
    'retrieve': pose(hip=(-2, -14), lean=7, right=(25, -32/SCALE), left=(-12, -13), feet=((-12, 0), (13, 0))),
    'slide': pose(hip=(0, -23), lean=-5, left=(-6, -59), right=(8, -53), feet=((-17, -8), (17, -8))),
    'skid': pose(hip=(-6, -13), lean=-8, right=(13, -33), feet=((-18, 0), (17, 0))),
    'run_contact': pose(hip=(0, -21), lean=9, left=(-13, -38), right=(22, -28), feet=((-19, 0), (16, -4))),
    'run_down': pose(hip=(0, -18), lean=10, left=(-9, -38), right=(20, -30), feet=((-10, 0), (16, -10))),
    'run_pass': pose(hip=(0, -23), lean=8, left=(8, -32), right=(4, -38), feet=((0, 0), (13, -17))),
    'run_flight': pose(hip=(0, -24), lean=9, left=(19, -31), right=(-9, -40), feet=((17, -6), (-16, -12))),
    'draw': pose(lean=-3, right=(-9, -29), left=(7, -27), blade=-20),
    'guard': pose(lean=2, right=(18, -36), left=(-11, -31), blade=-65),
    'wind_high': pose(hip=(-3, -23), lean=-7, right=(-7, -60), left=(14, -35), blade=-130),
    'cut_down': pose(hip=(3, -17), lean=12, right=(24, -24), left=(-9, -27), feet=((-15, 0), (16, 0)), blade=42),
    'cut_through': pose(hip=(4, -16), lean=15, right=(26, -15), left=(-8, -30), feet=((-16, 0), (17, 0)), blade=65),
    'wind_low': pose(hip=(-3, -18), lean=-5, right=(-9, -15), left=(15, -40), blade=30),
    'cut_up': pose(hip=(3, -22), lean=8, right=(24, -35), left=(-9, -29), feet=((-14, 0), (14, 0)), blade=-35),
    'cut_high': pose(hip=(2, -25), lean=7, right=(18, -57), left=(-10, -30), blade=-75),
    'recover': pose(hip=(0, -21), lean=5, right=(21, -29), left=(-11, -26), blade=10),
    'stab': pose(hip=(3, -19), lean=12, right=(32, -34), left=(-7, -28), feet=((-16, 0), (16, 0)), blade=0),
    'flinch': pose(hip=(-4, -20), lean=-10, right=(7, -44), left=(-18, -42), blade=70),
    'duck': pose(hip=(-3, -10), lean=12, left=(-10, -16), right=(21, -18), feet=((-15, 0), (16, 0))),
    'blind_left': pose(hip=(-3, -21), lean=-8, left=(-16, -48), right=(18, -35), blade=-125),
    'blind_right': pose(hip=(2, -19), lean=8, left=(1, -52), right=(27, -24), blade=25),
    'push_reach': pose(hip=(-5, -21), lean=14, left=(30, -37), right=(32, -40), feet=((-18, 0), (12, 0))),
    'push_load': pose(hip=(-9, -17), lean=16, left=(29, -31), right=(32, -34), feet=((-21, 0), (10, 0))),
    'push_fail': pose(hip=(-13, -11), lean=16, left=(25, -23), right=(29, -26), feet=((-22, 0), (8, 0))),
    'stumble': pose(hip=(0, -20), lean=15, left=(-10, -42), right=(31, -37), feet=((-20, -7), (13, 0))),
    'rim_hang': pose(hip=(0, -24), lean=0, left=(-17, -51), right=(17, -51), feet=((-12, -4), (11, -7))),
    'rim_pull': pose(hip=(0, -16), lean=0, left=(-18, -37), right=(18, -37), feet=((-14, -5), (13, -8))),
    'land_hard': pose(hip=(0, -9), lean=12, left=(-15, -9), right=(23, -10), feet=((-17, 0), (17, 0))),
    'balance_left': pose(hip=(-3, -23), lean=-9, left=(-30, -40), right=(13, -49), feet=((-8, 0), (9, -3))),
    'balance_right': pose(hip=(3, -23), lean=8, left=(-16, -49), right=(30, -37), feet=((-8, -3), (9, 0))),
    'balance_cross': pose(hip=(0, -22), lean=1, left=(-25, -43), right=(25, -43), feet=((6, 0), (-7, -4))),
    'grip': pose(hip=(-3, -21), lean=12, left=(24, -32), right=(27, -32), feet=((-16, 0), (15, 0))),
    'pull': pose(hip=(-6, -17), lean=14, left=(27, -33), right=(31, -34), feet=((-20, 0), (10, 0))),
    'pull_hard': pose(hip=(-12, -12), lean=21, left=(27, -33), right=(31, -34), feet=((-22, 0), (6, 0))),
    'release': pose(hip=(-6, -19), lean=-12, left=(-11, -47), right=(-1, -49), feet=((-20, -4), (11, 0))),
    'flint_raise': pose(hip=(0, -14), lean=9, left=(22, -14), right=(12, -38), feet=((-14, 0), (15, 0))),
    'flint_strike': pose(hip=(0, -12), lean=12, left=(25, -12), right=(27, -13), feet=((-15, 0), (15, 0))),
    'stamp_high': pose(hip=(0, -23), lean=8, left=(-15, -42), right=(25, -36), feet=((-7, 0), (17, -20))),
    'stamp': pose(hip=(1, -18), lean=11, left=(-12, -39), right=(25, -29), feet=((-10, 0), (19, 0))),
    'shield': pose(hip=(-5, -12), lean=-3, left=(-7, -45), right=(5, -47), feet=((-16, 0), (13, 0))),
    'blast': pose(hip=(0, -24), lean=-10, left=(-28, -31), right=(12, -55), feet=((-20, -7), (18, -12))),
    'wedge': pose(hip=(0, -17), lean=-6, left=(-22, -33), right=(17, -49), feet=((-13, -1), (12, -5))),
    'wave_low': pose(lean=-2, left=(-12, -27), right=(15, -50)),
    'wave_high': pose(lean=-1, left=(-12, -27), right=(8, -61)),
    'exit_grip': pose(hip=(0, -24), lean=1, left=(-6, -62), right=(9, -55), feet=((-10, -8), (12, -12))),
}


def joints(parameters):
    hx, hy, lean, look, lx, ly, rx, ry, ax, ay, bx, by, blade, *bends = parameters
    hip = (hx, hy)
    shoulder = add(hip, (lean, -17))
    head = add(shoulder, (look*.45, -10))
    result = dict(hip=hip, shoulder=shoulder, head=head)
    for name, origin, target, lengths, bend in (
        ('left', shoulder, (lx, ly), (12, 12), bends[0]),
        ('right', shoulder, (rx, ry), (12, 12), bends[1]),
        ('lf', hip, (ax, ay), (13, 13), bends[2]),
        ('rf', hip, (bx, by), (13, 13), bends[3])):
        result[name+'_mid'], result[name] = two_bone(origin, target, *lengths, bend)
    result['tip'] = add(result['right'], rotate((36, 0), blade))
    return result


def body_path(j):
    x, y = j['head']; r = 5.1
    head = f'M{num(x-r)},{num(y)}a{r},{r} 0 1 0 {2*r},0a{r},{r} 0 1 0 {-2*r},0'
    return head+path([add(j['head'], (0, r)), j['shoulder'], j['hip']])+''.join(
        path([j['shoulder'] if name in ('left', 'right') else j['hip'], j[name+'_mid'], j[name]])
        for name in ('left', 'right', 'lf', 'rf'))


def sampled(function, tracks, rate=16, window=(0., T), lag=0):
    """Sample only authored changes; retain exact contact keys and held poses."""
    start, end = window
    times = {0., T, start, end}
    for track in tracks:
        for (a, x, _), (b, y, _) in zip(track.keys, track.keys[1:]):
            if b < start or a > end:
                continue
            a, b = max(a, start), min(b, end)
            times.update((a, b, min(end, a+lag), min(end, b+lag)))
            if x != y:
                count = max(1, math.ceil((b-a)*rate))
                times.update(a+(b-a)*i/count for i in range(1, count))
    curve = Curve(function(start))
    raw = [(t, function(max(start, min(end, t)))) for t in sorted({round(t, 6) for t in times})]
    # Remove interior identical samples, retaining both ends of every hold.
    for i, (t, value) in enumerate(raw[1:], 1):
        if i < len(raw)-1 and value == raw[i-1][1] == raw[i+1][1]:
            continue
        curve.key(t, value)
    return curve


class Actor:
    def __init__(self, name, x, y):
        self.name = name
        self.position = Curve((x, y))
        self.acting = Curve(POSES['rest'])
        self.angle = Curve(0.)
        self.facing = Curve(1.)
        self.show = Curve(0.)
        self.weapon = Curve(0.)
        self.used = {'rest'}
        self.pins = []
        self.supports = []

    def act(self, t, name, duration=.12):
        self.used.add(name)
        begin = max(self.acting.keys[-1][0], t-duration)
        self.acting.go(begin, t, POSES[name], 'ease')
        return self

    def travel(self, start, end, destination, height=0):
        self.position.hold(start)
        origin = self.position.at(start)
        if not height:
            self.position.key(end, destination, 'ease')
        else:
            for i in range(1, 17):
                u = i/16
                x, y = lerp(origin, destination, u)
                self.position.key(start+(end-start)*u, (x, y-4*height*u*(1-u)))
        return self

    def leap(self, start, end, destination, height=35):
        self.act(start-.02, 'crouch').act(start+.08, 'takeoff', .08)
        self.act(start+(end-start)*.46, 'tuck', .14).act(end-.06, 'fall', .10)
        self.act(end+.05, 'compress', .11).act(end+.22, 'rise', .17)
        return self.travel(start, end, destination, height)

    def arc(self, start, end, anchor, hand, end_angle, radius=None, start_angle=None):
        endpoint = self.world(hand, start)
        radius = radius or math.dist(endpoint, anchor)
        first = math.degrees(math.atan2(endpoint[1]-anchor[1], endpoint[0]-anchor[0])) if start_angle is None else start_angle
        self.position.hold(start-EPS)
        for i in range(25):
            t = start+(end-start)*i/24
            theta = lerp(first, end_angle, i/24)
            endpoint = add(anchor, rotate((radius, 0), theta))
            local = self.local(t)[hand]
            self.position.key(t, sub(endpoint, (local[0]*SCALE*self.facing.at(t), local[1]*SCALE)))
        return self

    def face(self, t, sign):
        self.facing.step(t, float(sign))
        return self

    def local(self, t):
        result = joints(self.acting.at(t))
        for start, end, name, target in self.pins:
            if start <= t <= end:
                point = sub(target, self.root(t))
                point = (point[0]/(SCALE*self.facing.at(t)), point[1]/SCALE)
                origin = result['shoulder'] if name in ('left', 'right') else result['hip']
                length = 12 if name in ('left', 'right') else 13
                result[name+'_mid'], result[name] = two_bone(origin, point, length, length, -1 if name == 'left' else 1)
        # Recompute the carried blade after any wrist constraint.
        result['tip'] = add(result['right'], rotate((36, 0), self.acting.at(t)[12]))
        return result

    def root(self, t):
        position = self.position.at(t)
        for start, end, support in self.supports:
            if start <= t <= end and self.position.at(start) == position:
                return add(position, support.at(t))
        return position

    def world(self, name, t):
        x, y = self.local(t)[name]
        pivot = (0., -25*SCALE)
        local = (x*SCALE*self.facing.at(t), y*SCALE)
        return add(self.root(t), add(pivot, rotate(sub(local, pivot), self.angle.at(t))))

    def render(self, palette):
        ink, paper = palette[self.name], palette['bg']
        rig = sampled(lambda t: body_path(self.local(t)), [self.acting])
        definition = f'<defs><path id="rig-{self.name}" d="{rig.keys[0][1]}">'+animation('d', rig, str)+'</path></defs>'
        body = f'<use href="#rig-{self.name}" fill="none" stroke="{ink}" stroke-width="2.35" stroke-linecap="round" stroke-linejoin="round"/>'
        # Share the morph, but draw a paper halo below the ink silhouette.
        halo = body.replace(f'stroke="{ink}" stroke-width="2.35"', f'stroke="{paper}" stroke-width="5.4"')
        head_track = sampled(lambda t: body_path(self.local(t)).split('M')[1], [self.acting])
        head = f'<path d="M{head_track.keys[0][1]}" fill="{paper}">'+animation('d', head_track, lambda d: 'M'+d)+'</path>'
        hat_track = sampled(lambda t: self.hat(t), [self.acting, self.angle], lag=.07)
        hat = f'<path d="{hat_track.keys[0][1]}" fill="{paper}" stroke="{ink}" stroke-width="1.8">'+animation('d', hat_track, str)+'</path>'
        coat_track = sampled(lambda t: self.coat(t), [self.acting, self.angle], lag=.09)
        coat = f'<path d="{coat_track.keys[0][1]}" fill="{paper}" stroke="{ink}" stroke-width="1.4">'+animation('d', coat_track, str)+'</path>'
        sword = sampled(lambda t: self.sword(t), [self.acting])
        blade = f'<path d="{sword.keys[0][1]}" fill="{paper}" stroke="{ink}" stroke-width="1.25" stroke-linejoin="round">'+animation('d', sword, str)+'</path>'
        body = definition+halo+coat+head+body+hat+opacity(blade, self.weapon)
        body = group(body, sampled(lambda t: (SCALE*self.facing.at(t), SCALE), [self.facing]), 'scale')
        body = group(body, sampled(lambda t: (self.angle.at(t), 0, -25*SCALE), [self.angle]), 'rotate')
        translation = sampled(self.root, [self.position]+[support for _, _, support in self.supports])
        return opacity(group(body, translation, id=self.name), self.show)

    def hat(self, t):
        head = self.local(t)['head']
        lag = (self.acting.at(max(0, t-.07))[2]-self.acting.at(t)[2])*.28
        points = [(-10, -3), (-6, -6), (-4, -10), (2, -9), (8, -3), (-10, -3)] if self.name == 'pirate' else [(-8, -4), (-7, -9), (6, -9), (7, -4), (11, -3), (-8, -3)]
        return path([add(head, rotate(p, lag)) for p in points])+'Z'

    def coat(self, t):
        j = self.local(t)
        lag = (self.acting.at(max(0, t-.09))[2]-self.acting.at(t)[2])*.5
        return path([add(j['shoulder'], (-3, 2)), add(j['hip'], (-7-lag, 7)),
                     add(j['hip'], (0, 3)), add(j['hip'], (7-lag, 7)), add(j['shoulder'], (3, 2))])+'Z'

    def sword(self, t):
        j = self.local(t); wrist = j['right']; angle = self.acting.at(t)[12]
        return path([add(wrist, rotate(p, angle)) for p in [(-5, -1), (0, -1), (30, -2), (36, 0), (30, 2), (0, 1), (-5, 1)]])+'Z'+path([add(wrist, rotate((1, -5), angle)), add(wrist, rotate((1, 5), angle))])


def art_rows():
    width = max(b for _, b in LETTER_COLS)
    rows = list(ART_RAW)
    if len(rows[0]) == max(map(len, rows))-1:
        rows[0] = ' '+rows[0]
    return [r.ljust(width) for r in rows]


def cell_shape(ch, x, y):
    if ch == '█':
        return f'M{x},{y}h{CW}v{CH}h{-CW}Z'
    if ch == ' ':
        return ''
    # Each corner is two nested right angles, not crossing horizontal/vertical bars.
    cx, cy, gap = x+CW/2, y+CH/2, 2.5
    polylines = {
        '═': [[(x, cy-gap), (x+CW, cy-gap)], [(x, cy+gap), (x+CW, cy+gap)]],
        '║': [[(cx-gap, y), (cx-gap, y+CH)], [(cx+gap, y), (cx+gap, y+CH)]],
        '╔': [[(x+CW, cy-gap), (cx-gap, cy-gap), (cx-gap, y+CH)], [(x+CW, cy+gap), (cx+gap, cy+gap), (cx+gap, y+CH)]],
        '╗': [[(x, cy-gap), (cx+gap, cy-gap), (cx+gap, y+CH)], [(x, cy+gap), (cx-gap, cy+gap), (cx-gap, y+CH)]],
        '╚': [[(cx-gap, y), (cx-gap, cy+gap), (x+CW, cy+gap)], [(cx+gap, y), (cx+gap, cy-gap), (x+CW, cy-gap)]],
        '╝': [[(cx+gap, y), (cx+gap, cy+gap), (x, cy+gap)], [(cx-gap, y), (cx-gap, cy-gap), (x, cy-gap)]],
    }
    strips = []
    for line in polylines.get(ch, []):
        for a, b in zip(line, line[1:]):
            left, top = min(a[0], b[0])-.55, min(a[1], b[1])-.55
            strips.append(f'M{num(left)},{num(top)}h{num(abs(a[0]-b[0])+1.1)}v{num(abs(a[1]-b[1])+1.1)}h-{num(abs(a[0]-b[0])+1.1)}Z')
    return ''.join(strips)


class Letter:
    def __init__(self, name, bounds):
        self.name, self.cols = name, bounds
        self.x, self.y = X0+bounds[0]*CW, Y0
        self.width, self.height = (bounds[1]-bounds[0])*CW, CH*6
        self.offset = Curve((0., 0.))
        self.angle = Curve((0., self.x+self.width/2, self.y+self.height))
        self.show = Curve(1.)

    def surface(self, row, fraction=.5):
        rows = art_rows(); a, b = self.cols
        cells = [c for c in range(a, b) if rows[row][c] == '█' and (row == 0 or rows[row-1][c] != '█')]
        if not cells:
            raise ValueError(f'{self.name} row {row} has no exposed solid surface')
        c = cells[min(len(cells)-1, int(fraction*len(cells)))]
        return X0+(c+.5)*CW, Y0+row*CH

    def dip(self, t, weight=2):
        self.offset.go(t, t+.06, (0., weight), 'out').key(t+.20, (0., 0.), 'out')

    def definition(self):
        rows = art_rows(); a, b = self.cols
        d = ''.join(cell_shape(rows[r][c], X0+c*CW, Y0+r*CH) for r in range(6) for c in range(a, b))
        return f'<path id="glyph-{self.name}" d="{d}"/>'

    def render(self):
        return opacity(group(group(f'<use href="#glyph-{self.name}"/>', self.offset), self.angle, 'rotate'), self.show)


def segment_box(a, b, box):
    """First point where an actual blade segment enters a solid glyph cell."""
    x0, y0, x1, y1 = box; dx, dy = sub(b, a); low, high = 0., 1.
    for p, q in ((-dx, a[0]-x0), (dx, x1-a[0]), (-dy, a[1]-y0), (dy, y1-a[1])):
        if abs(p) < 1e-10:
            if q < 0:
                return None
        elif p < 0:
            low = max(low, q/p)
        else:
            high = min(high, q/p)
    return lerp(a, b, low) if low <= high else None


def clip_polygon(poly, normal, offset):
    result = []
    for a, b in zip(poly, poly[1:]+poly[:1]):
        da = a[0]*normal[0]+a[1]*normal[1]-offset
        db = b[0]*normal[0]+b[1]*normal[1]-offset
        if da <= 0:
            result.append(a)
        if (da <= 0) != (db <= 0):
            result.append(lerp(a, b, da/(da-db)))
    return result


class Film:
    def __init__(self, theme):
        self.palette = PALETTES[theme]
        self.letters = {n: Letter(n, c) for n, c in zip('ANSIL', LETTER_COLS)}
        self.pirate, self.navy = Actor('pirate', -55., 145.), Actor('navy', 350., -75.)
        self.camera = Curve((0., 0.))
        self.shake = Curve((0., 0.))
        self.zoom = Curve((1., 1.))
        self.defs, self.back, self.terrain, self.props, self.front, self.effects = [], [], [], [], [], []
        self.contacts, self.damage, self.physics = [], [], []
        self.choreograph()
        self.stage()

    def stroke(self, d, width=1, color=None):
        return f'<path d="{d}" fill="none" stroke="{color or self.palette["fg"]}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>'

    def ring(self, t, point, radius=14, duration=.3):
        grow = Curve((.1, .1)).hold(t).key(t+duration, (1., 1.), 'out')
        fade = Curve(0.).step(t, 1.).key(t+duration, 0.)
        mark = f'<ellipse rx="{radius}" ry="{radius*.4}" fill="none" stroke="{self.palette["fg"]}" stroke-width=".9"/>'
        self.effects.append(group(opacity(group(mark, grow, 'scale'), fade), transform=f'translate({values(point)})'))

    def dust(self, t, point, direction=1):
        for i in range(3):
            tr = Curve(point).hold(t).key(t+.32+i*.03, add(point, (direction*(9+i*9), -7-i*4)), 'out')
            d = f'M{-2-i},0l{4+i},-2'
            self.effects.append(opacity(group(self.stroke(d, .9), tr), Curve(0.).step(t, .7).key(t+.36+i*.03, 0.)))

    def jolt(self, t, amount=2):
        self.shake.hold(t).key(t+.025, (amount, -amount)).key(t+.075, (-amount*.65, amount*.5)).key(t+.14, (0., 0.))

    def land(self, actor, letter, row, t):
        pc = self.letters[letter]; rows = art_rows()
        grounded = []
        for joint in ('lf', 'rf'):
            foot = actor.world(joint, t)
            col = math.floor((foot[0]-X0)/CW)
            if pc.cols[0] <= col < pc.cols[1] and rows[row][col] == '█' and abs(foot[1]-(Y0+row*CH)) < 1:
                grounded.append((joint, foot))
        if not grounded:
            raise ValueError(f'Unplanted landing {actor.name}/{letter} at {t}')
        joint, foot = grounded[0]
        self.contacts.append(dict(kind='foot', actor=actor.name, joint=joint, letter=letter, time=t, point=foot))
        self.letters[letter].dip(t, 2.3)
        actor.supports.append((t, t+.2, pc.offset))
        self.dust(t, foot, -actor.facing.at(t))

    def cut(self, t, letter):
        a, b = self.navy.world('right', t), self.navy.world('tip', t)
        pc = self.letters[letter]; rows = art_rows(); hits = []
        for row in range(5):
            for col in range(*pc.cols):
                if rows[row][col] != '█':
                    continue
                hit = segment_box(a, b, (X0+col*CW, Y0+row*CH, X0+(col+1)*CW, Y0+(row+1)*CH))
                if hit is not None:
                    hits.append(hit)
        if not hits:
            raise ValueError(f'Sword misses {letter} at {t}: {a} -> {b}')
        point = min(hits, key=lambda p: math.dist(p, a))
        self.contacts.append(dict(kind='blade', letter=letter, time=t, point=point, hilt=a, tip=b))
        self.damage.append((letter, t, a, b, point))
        self.ring(t, point, 10, .22); self.dust(t, point); self.jolt(t, 1.4)
        self.effects.append(opacity(self.stroke(path([a, b]), 1.3, self.palette['navy']), visible(t-.035, t+.09)))

    def swing(self, t, upward=False):
        actor = self.navy
        actor.act(t-.24, 'wind_low' if upward else 'wind_high', .2)
        actor.act(t, 'cut_up' if upward else 'cut_down', .075)
        actor.act(t+.07, 'cut_up' if upward else 'cut_down', .07)  # held impact
        actor.act(t+.20, 'cut_high' if upward else 'cut_through', .13)
        actor.act(t+.34, 'guard' if upward else 'recover', .14)

    def choreograph(self):
        p, n, letters = self.pirate, self.navy, self.letters
        A, N, S, I, L = (letters[k] for k in 'ANSIL')
        a, ledge, mast = A.surface(0), L.surface(4, .75), I.surface(0)
        # 00.60: the set wakes before the cast enters.
        for i, letter in enumerate(letters.values()):
            letter.dip(.60+i*.07, 1.2)
        # 01.00: the rope, kick, flight and landing are one continuous arrival.
        p.show.step(.9, 1.).step(32.7, 0.)
        p.act(.95, 'hang').act(1.15, 'swing').act(1.4, 'kick_apex')
        apex_root = sub(a, mul(joints(POSES['kick_apex'])['rf'], SCALE))
        anchor = (77, -55)
        kick_hand = add(apex_root, mul(joints(POSES['kick_apex'])['left'], SCALE))
        final_angle = math.degrees(math.atan2(kick_hand[1]-anchor[1], kick_hand[0]-anchor[0]))
        p.arc(.92, 1.4, anchor, 'left', final_angle, math.dist(anchor, kick_hand), 145.)
        p.act(1.5, 'takeoff').act(1.78, 'tuck').act(2.07, 'fall').act(2.15, 'compress', .08).act(2.32, 'rise')
        p.travel(1.44, 2.10, ledge, 89)
        self.land(p, 'L', 4, 2.15)
        self.ring(1.4, a); A.dip(1.4, 3)
        self.contacts.append(dict(kind='kick', letter='A', joint='rf', time=1.4, point=p.world('rf', 1.4)))
        # 02.35: climbing has alternating holds before the hands tie the flag.
        p.face(2.36, -1).act(2.48, 'climb_left').act(2.69, 'climb_right').act(2.88, 'climb_left')
        p.travel(2.38, 2.95, (mast[0]+15, mast[1]), 8)
        p.act(3.04, 'tie_low').act(3.2, 'tie_high').act(3.35, 'hips')
        # 03.45: dagger flies from the wrist; the notice is pinned at its endpoint.
        p.act(3.60, 'throw_draw').act(3.76, 'throw_release', .07).act(3.89, 'throw_follow')
        p.act(4.15, 'hips').act(4.65, 'breathe').act(5.05, 'look_left')
        # 04.50: N is a staircase, each landing drives its own dip.
        n.show.step(4.46, 1.).step(31.4, 0.)
        n.act(4.48, 'slide').travel(4.48, 4.85, N.surface(0, .8))
        n.act(4.90, 'compress').act(5.03, 'rise')
        self.land(n, 'N', 0, 4.90)
        n.travel(5.06, 5.23, N.surface(1, .5), 8).act(5.12, 'run_flight').act(5.28, 'compress')
        self.land(n, 'N', 1, 5.28)
        n.travel(5.34, 5.46, N.surface(2, .5), 7).act(5.39, 'run_flight').act(5.49, 'compress', .06)
        self.land(n, 'N', 2, 5.49)
        # 05.50: readable holds between the looks sell recognition.
        n.act(5.65, 'look_right').act(5.88, 'look_left').act(6.08, 'scope_raise').act(6.22, 'scope').act(6.48, 'scope_recoil', .08)
        p.act(5.7, 'look_right').act(6.05, 'shrug').act(6.4, 'whistle')
        # 06.60: escape over S; the officer follows the same levels.
        p.leap(6.63, 7.00, (S.x+76, Y0), 34)
        self.land(p, 'S', 0, 7.05)
        n.act(6.68, 'draw').act(6.86, 'guard')
        n.weapon.step(6.78, 1.).step(15.58, 0.)
        n.travel(6.65, 7.01, (S.x-8, Y0+CH), 25)
        n.face(6.67, 1)
        # 07.15: down / up / down form one blade arc across three shelves.
        for t, row, upward in ((7.22, 0, False), (7.90, 2, True), (8.58, 4, False)):
            root_y = Y0+row*CH+18 if not upward else Y0+row*CH+45
            n.travel(t-.18, t-.08, (S.x-12, root_y))
            self.swing(t, upward)
            self.cut(t, 'S')
        p.travel(7.28, 7.53, (S.x+86, Y0+2*CH), 12).act(7.34, 'tuck').act(7.58, 'compress')
        p.travel(7.94, 8.22, (S.x+88, Y0+4*CH), 16).act(8.01, 'tuck').act(8.27, 'retrieve')
        p.act(8.53, 'look_left').act(8.77, 'hang')
        # 08.70: the escaping pirate takes the rope; the flag takes the officer.
        p.act(9.01, 'swing').act(9.3, 'fall').act(9.55, 'compress').act(9.72, 'look_left')
        p.arc(8.76, 9.25, (I.x+I.width/2, Y0-50), 'right', 45.)
        p.travel(9.26, 9.5, (I.x+60, FLOOR), -5)
        n.travel(8.97, 9.22, (I.x-22, FLOOR), 20).act(9.13, 'cut_high').act(9.36, 'flinch')
        n.act(9.62, 'blind_left').act(9.86, 'blind_right')
        # 09.95: the wild blade intersects a solid cell at I's base.
        n.travel(9.7, 9.97, (I.x-24, Y0+5*CH+5))
        n.act(10.04, 'cut_down', .07).act(10.12, 'cut_down', .08)
        self.cut(10.04, 'I')
        n.act(10.3, 'recover').act(10.52, 'look_right')
        # 10.60: both plant their feet against the mast, then lose the load.
        n.travel(10.35, 10.68, (I.x+39, FLOOR), 9).face(10.56, -1)
        p.face(10.48, -1).travel(10.5, 10.8, (I.x+92, FLOOR))
        for actor, lag in ((n, 0), (p, .12)):
            actor.act(10.82+lag, 'push_reach').act(11.13+lag, 'push_load').act(11.48+lag, 'push_fail')
            actor.act(11.73+lag, 'stumble').act(12.08+lag, 'shield').act(12.48+lag, 'look_left')
        I.angle.go(10.11, 10.65, (9., I.x+I.width/2, I.y+5*CH), 'in')
        I.angle.key(11.05, (28., I.x+I.width/2, I.y+5*CH), 'in').hold(11.42)
        # The lowest rotated corner determines when the mast reaches the floor.
        pivot = (I.x+I.width/2, I.y+5*CH)
        corner = (I.x+I.width, I.y)
        hit_angle = next(a/10 for a in range(901, 1801) if add(pivot, rotate(sub(corner, pivot), a/10))[1] >= FLOOR)
        I.angle.key(12.0, (hit_angle, *pivot), 'in').key(12.12, (hit_angle-6, *pivot), 'out').key(12.32, (hit_angle, *pivot), 'in')
        # The upward blast lifts the fallen mast before it breaks with the banner.
        I.angle.go(21.48, 22.40, (0., *pivot), 'out')
        impact = add(pivot, rotate(sub(corner, pivot), hit_angle))
        self.contacts.append(dict(kind='mast', time=12., point=impact))
        self.mast_impact = impact
        self.jolt(12., 4); self.dust(12., impact, -1); self.ring(12., impact, 28, .45)
        # 13.20: first a hesitation at the rim, then the actual fall.
        p.face(12.7, -1).act(12.88, 'double_take').act(13.12, 'fall')
        n.face(12.7, 1).act(12.9, 'double_take').act(13.18, 'fall')
        p.travel(12.82, 13.38, (548, FLOOR+95), 14)
        n.travel(12.86, 13.44, (473, FLOOR+95), 10)
        p.act(13.53, 'tuck').act(14.2, 'fall').act(14.48, 'land_hard').act(14.7, 'rise')
        n.act(13.58, 'tuck').act(14.28, 'fall').act(14.57, 'land_hard').act(14.8, 'rise')
        p.travel(13.39, 14.43, (577, DECK), -35)
        n.travel(13.45, 14.52, (378, DECK), -35)
        self.camera.go(13.25, 14.25, (0., FLOOR-DECK), 'ease')
        self.ring(14.44, (577, DECK), 20); self.ring(14.53, (378, DECK), 20)
        # 14.50: the characters take in the new room before repeating the mistake.
        p.act(14.96, 'dust_left').act(15.17, 'look_left')
        n.act(14.99, 'look_right').act(15.2, 'guard')
        # 15.30: the sword's last carried endpoints define the lodged prop.
        n.face(15.22, 1).travel(15.23, 15.53, (428, DECK)).act(15.36, 'wind_high').act(15.58, 'stab', .08)
        self.lodged = (n.world('right', 15.58), n.world('tip', 15.58))
        n.pins.extend([(15.58, 17.27, 'right', self.lodged[0]),
                       (15.72, 17.27, 'left', add(self.lodged[0], (-3, 0)))])
        n.act(15.72, 'grip').act(16.02, 'pull').act(16.22, 'grip').act(16.55, 'pull_hard')
        n.act(16.82, 'grip').act(17.17, 'pull_hard').act(17.45, 'release')
        # 16.50: the barrel rolls while the feet exchange support.
        p.leap(15.5, 15.95, (591, DECK-51), 35)
        p.act(16.25, 'balance_left').act(16.57, 'balance_right').act(16.88, 'balance_cross')
        p.act(17.16, 'balance_left').act(17.42, 'balance_right')
        p.travel(16.15, 17.45, (640, DECK-51))
        p.leap(17.5, 17.78, (621, DECK), 15)
        # 17.80: the same dagger strikes; the officer sees it a beat too late.
        p.face(17.82, -1).act(18.10, 'flint_raise').act(18.22, 'flint_strike', .07).act(18.34, 'flint_strike')
        self.fuse_start = p.world('right', 18.22)
        n.act(17.78, 'look_right').act(18.04, 'double_take').act(18.36, 'point')
        # 18.60: stamping follows the spark, always just behind it.
        n.travel(18.5, 18.83, (536, DECK)).act(18.65, 'run_contact').act(18.79, 'stamp_high').act(18.92, 'stamp')
        n.travel(19., 19.27, (464, DECK)).act(19.06, 'run_pass').act(19.23, 'stamp_high').act(19.36, 'stamp')
        p.act(18.63, 'look_left').act(18.89, 'duck').travel(18.62, 18.93, (663, DECK))
        p.act(19.35, 'shield').act(19.76, 'look_left')
        # 20.00: two quick bursts and a delayed third; no filled flashes.
        for i, t in enumerate((20., 20.55, 21.48)):
            self.explosion(t, (365+i*113, DECK-24), i)
        n.act(19.72, 'flinch').act(20.08, 'shield').act(20.72, 'shield').act(21.06, 'look_right')
        p.act(20.08, 'shield').act(20.69, 'shield').act(21.02, 'look_left').act(21.55, 'blast', .07)
        n.act(21.55, 'blast', .07)
        # 22.00: the blast supplies the upward velocity; the letters catch it.
        p.travel(21.6, 22.72, (518, 140), 35)
        n.travel(21.6, 22.76, (642, 177), 55)
        p.angle.go(21.61, 22.7, (-330.), 'out').go(22.75, 23.15, (-360.), 'out')
        n.angle.go(21.61, 22.73, (300.), 'out').go(22.79, 23.21, (360.), 'out')
        self.camera.go(21.8, 22.7, (0., 0.), 'ease')
        self.jolt(22.69, 3)
        p.act(22.83, 'tuck').act(23.23, 'fall').act(23.62, 'compress').act(23.87, 'rise')
        p.travel(22.77, 23.56, (ledge[0]-58, FLOOR), 30)
        n.act(22.9, 'flinch').act(23.3, 'wedge').act(23.75, 'wedge')
        n.travel(22.78, 23.27, (L.x+38, Y0+4*CH+36), 13)
        # 23.30: L catches a person; the other fragments have actual floor collisions.
        p.act(24.12, 'look_right').act(24.52, 'hips').act(25.02, 'double_take').act(25.55, 'look_left')
        p.act(26.10, 'look_right').act(26.65, 'breathe').act(27.15, 'shrug')
        n.act(24.4, 'wedge').act(25.1, 'flinch').act(26.1, 'wedge').act(27.1, 'wedge')
        # 28.00: the flag is returned in a different spirit.
        p.leap(27.45, 27.83, (ledge[0]+9, ledge[1]), 30)
        self.land(p, 'L', 4, 27.88)
        p.face(28.12, -1).act(28.35, 'hat_tip').act(28.73, 'bow').act(29.15, 'rest')
        n.act(28.36, 'wave_low').act(28.77, 'wave_high').act(29.15, 'wave_low').act(29.54, 'wave_high')
        p.act(29.54, 'look_left').act(29.93, 'shrug').act(30.35, 'hips')
        n.act(30., 'wave_low').act(30.5, 'wave_high').act(31.05, 'wedge')
        # 31.00: the original rope takes the pirate away; all visible states reset.
        p.act(31.12, 'exit_grip').act(31.43, 'climb_left').act(31.73, 'climb_right').act(32.07, 'climb_left')
        p.travel(31.18, 32.62, (ledge[0]+9, -90))
        self.exit_x = ledge[0]+9
        self.shatter()

    def explosion(self, t, point, index):
        self.ring(t, point, 46, .55); self.dust(t, point, -1); self.dust(t, point)
        self.jolt(t, 2.5+index*.7)
        self.zoom.go(t-.05, t+.04, (1.015, 1.015), 'out').key(t+.32, (1., 1.), 'out')
        for i in range(3):
            angle = -140+i*48+index*9
            dest = add(point, rotate((37+i*6, 0), angle))
            moving = Curve(point).hold(t).key(t+.35, dest, 'out')
            self.effects.append(opacity(group(self.stroke('M-3,-2l6,4', 1.3), moving), visible(t, t+.42)))

    def shatter(self):
        for index, letter in enumerate(self.letters.values()):
            start, restore = 22.70+index*.035, 26.15+index*.29
            letter.show.step(start, 0.).step(restore, 1.)
            # Reset the intact I while its fragments are on screen.
            if letter.name == 'I':
                letter.angle.step(25., (0., letter.x+letter.width/2, letter.y+letter.height))
            for quadrant in range(4):
                x = letter.x+(quadrant%2)*letter.width/2
                y = letter.y+(quadrant//2)*letter.height/2
                poly = [(x, y), (x+letter.width/2, y), (x+letter.width/2, y+letter.height/2), (x, y+letter.height/2)]
                cx, cy = x+letter.width/4, y+letter.height/4
                ident = f'fragment-{index}-{quadrant}'
                self.defs.append(f'<clipPath id="{ident}"><path d="{path(poly)}Z"/></clipPath>')
                vx = (cx-510)*.48+(quadrant%2*2-1)*24
                vy = -100-(index*13+quadrant*17)%65
                omega = (1 if quadrant%2 else -1)*(40+index*8)
                samples = [(0., (0., 0.), 0.)]
                px, py, angle = 0., 0., 0.
                for k in range(1, 23):
                    dt = .045; vy += 390*dt; px += vx*dt; py += vy*dt; angle += omega*dt
                    bottom = max(rotate(sub(v, (cx, cy)), angle)[1]+cy+py for v in poly)
                    if bottom > FLOOR:
                        py -= bottom-FLOOR
                        if vy > 0:
                            vy *= -.28; vx *= .69; omega *= .63
                    samples.append((k*dt, (px, py), angle))
                moving, turning = Curve((0., 0.)), Curve((0., cx, cy))
                moving.hold(start); turning.hold(start)
                for dt, position, rotation in samples[1:]:
                    moving.key(start+dt, position); turning.key(start+dt, (rotation, cx, cy))
                rewind = restore-samples[-1][0]
                moving.hold(rewind); turning.hold(rewind)
                for dt, position, rotation in reversed(samples[:-1]):
                    moving.key(restore-dt, position); turning.key(restore-dt, (rotation, cx, cy))
                self.physics.append(dict(letter=letter.name, polygon=poly, center=(cx, cy), samples=samples, start=start, restore=restore, motion=moving, rotation=turning))
                glyph = f'<g clip-path="url(#{ident})"><use href="#glyph-{letter.name}"/></g>'
                self.front.append(opacity(group(group(glyph, turning, 'rotate'), moving), visible(start, restore)))
            self.ring(restore, (letter.x+letter.width/2, letter.y+letter.height), 20)

    def stage(self):
        p, n, ink, paper = self.pirate, self.navy, self.palette['fg'], self.palette['bg']
        self.defs.extend(letter.definition() for letter in self.letters.values())
        mask_height = Curve(1200.).step(23.28, Y0+4*CH+100.)
        self.defs.append('<clipPath id="trapped-officer"><rect x="0" y="-100" width="830" height="1200">'+animation('height', mask_height)+'</rect></clipPath>')
        # A single camera sees both floors. The foreground plank masks the fall.
        hole_x = (self.mast_impact[0]+510)/2
        hole = [(hole_x-94, FLOOR), (hole_x-72, FLOOR+12), (hole_x+79, FLOOR+10), (hole_x+104, FLOOR), (hole_x+67, FLOOR-9), (hole_x-70, FLOOR-7)]
        hole_d = path(hole)+'Z'
        page_minus = 'M0,0H830V1100H0Z'+hole_d
        self.defs.append(f'<clipPath id="deck-mask"><path clip-rule="evenodd" d="{page_minus}"/></clipPath>')
        self.back.append(self.stroke(f'M44,{FLOOR}H786', .9, self.palette['rule']))
        room = self.stroke(f'M80,{FLOOR+50}V{DECK}H750V{FLOOR+50}M80,{DECK+8}H750', 1, self.palette['rule'])
        room += ''.join(self.stroke(f'M{x},{DECK+8}l-13,18', .7, self.palette['rule']) for x in range(99, 750, 44))
        self.back.append(room)
        cracks = ''.join(path([self.mast_impact, (hole_x+dx*.5, FLOOR+dy*.3), (hole_x+dx, FLOOR+dy)]) for dx, dy in [(-124, -6), (-91, 13), (103, -9), (118, 12)])
        crack = f'<path d="{cracks}" fill="none" stroke="{ink}" stroke-width="1" stroke-dasharray="420" stroke-dashoffset="420">'+animation('stroke-dashoffset', Curve(420.).go(12.03, 12.7, 0.))+'</path>'
        self.back.append(opacity(crack, Curve(0.).step(12.01, 1.).go(32.7, 33.65, 0.)))
        self.back.append(opacity(f'<path d="{hole_d}" fill="{ink}"/>', Curve(0.).go(12.76, 13.15, 1.).go(32.4, 33.65, 0.)))
        deck = f'<path d="M{hole_x-125},{FLOOR}h255v82h-255Z" fill="{paper}" clip-path="url(#deck-mask)"/>'
        self.front.append(opacity(deck, visible(13.06, 14.35)))
        # Rope endpoints follow hands, including the original rope's return.
        rope_track = sampled(lambda t: path([(77, -55), p.world('left', t)]), [p.position, p.acting, p.facing, p.angle], window=(.9, 1.45))
        rope = f'<path d="{rope_track.keys[0][1]}" stroke="{ink}" stroke-width="1.2" fill="none">'+animation('d', rope_track, str)+'</path>'
        self.back.append(opacity(rope, visible(.9, 1.45)))
        exit_track = sampled(lambda t: path([(self.exit_x, -100), p.world('left', t)]), [p.position, p.acting], window=(30.8, 32.7))
        self.props.append(opacity(f'<path d="{exit_track.keys[0][1]}" fill="none" stroke="{ink}" stroke-width="1.2">'+animation('d', exit_track, str)+'</path>', visible(30.8, 32.7)))
        navy_rope = sampled(lambda t: path([(350, -80), n.world('left', t)]), [n.position, n.acting], window=(4.46, 5.02))
        self.back.append(opacity(f'<path d="{navy_rope.keys[0][1]}" fill="none" stroke="{ink}" stroke-width="1">'+animation('d', navy_rope, str)+'</path>', visible(4.46, 5.02)))
        self.flag_and_notice()
        self.shelves()
        self.barrels()
        self.attached_props()

    def flag_and_notice(self):
        p, n, I, ink, paper = self.pirate, self.navy, self.letters['I'], self.palette['fg'], self.palette['bg']
        pole = (I.x+I.width/2, Y0-50)
        self.props.append(opacity(self.stroke(path([(pole[0], Y0), pole]), 1.3), visible(2.96, 10.11)))
        flag_shape = 'M0,0C10,-5 18,6 30,1L30,19C18,24 10,13 0,18Z'
        flag = f'<path d="{flag_shape}" fill="{ink}" stroke="{ink}" stroke-width="1.2"/>'+self.stroke('M8,5l12,8M20,5L8,13', 1, paper)
        flutter = Curve((0., 0., 9.))
        for i in range(13):
            flutter.key(3.15+i*.43, ((-1 if i%2 else 1)*5., 0., 9.), 'ease')
        tr = Curve(pole).hold(9.25)
        for t in (9.34, 9.44, 9.56, 9.86, 10.04, 10.12, 10.32):
            head = n.world('head', t); tr.key(t, (head[0]-15, head[1]-7))
        tr.key(10.57, (I.x-35, FLOOR-5), 'in')
        self.props.append(opacity(group(group(flag, flutter, 'rotate'), tr), visible(3.1, 10.75)))
        rope = sampled(lambda t: path([pole, p.world('right', t)]), [p.position, p.acting, p.facing], window=(8.74, 9.28))
        self.back.append(opacity(f'<path d="{rope.keys[0][1]}" stroke="{ink}" stroke-width="1" fill="none">'+animation('d', rope, str)+'</path>', visible(8.74, 9.28)))
        # The throw and the notice share the computed dagger endpoint.
        notice = (self.letters['S'].x+61, Y0+2*CH+12)
        release = p.world('right', 3.76)
        dagger = self.stroke('M-7,0H9M-3,-4V4M9,0L4,-2M9,0L4,2', 1.2)
        flight = Curve(release).hold(3.76).key(3.94, notice)
        self.props.append(opacity(group(dagger, flight), visible(3.76, 8.27)))
        card = f'<path d="M-20,-4h40v47l-4,-2 -5,2 -6,-2 -5,2 -6,-2 -7,2 -7,-2Z" fill="{paper}" stroke="{ink}" stroke-width=".9"/>'
        card += f'<text x="0" y="8" text-anchor="middle" font-family="monospace" font-size="5.7" fill="{ink}">WANTED</text>'
        card += self.stroke('M-5,16a5,5 0 1 0 10,0a5,5 0 1 0 -10,0M0,21v10M0,24l-8,7M0,24l8,7M-9,14l4,-4 5,1 7,4', 1)
        card_drop = Curve(notice).hold(8.27).key(8.9, (notice[0]-14, FLOOR-12), 'in')
        self.props.append(opacity(group(card, card_drop), visible(3.94, 9.1)))
        self.contacts.append(dict(kind='dagger', time=3.94, point=notice, origin=release))
        self.contacts.append(dict(kind='retrieve', time=8.27, point=p.world('right', 8.27), target=notice))

    def shelves(self):
        S = self.letters['S']; cuts = [d for d in self.damage if d[0] == 'S']
        # Replace the glyph by progressively cut pieces; retain damage until blast.
        S.show = Curve(1.).step(cuts[0][1], 0.).step(26.73, 1.)
        remaining = [(S.x-2, Y0-2), (S.x+S.width+2, Y0-2), (S.x+S.width+2, Y0+S.height+2), (S.x-2, Y0+S.height+2)]
        for i, (_, t, a, b, hit) in enumerate(cuts):
            normal = (-(b[1]-a[1]), b[0]-a[0])
            if normal[1] < 0:
                normal = mul(normal, -1)
            offset = normal[0]*hit[0]+normal[1]*hit[1]
            above = clip_polygon(remaining, normal, offset)
            remaining = clip_polygon(remaining, mul(normal, -1), -offset)
            for label, poly, start, end, shift in (
                ('cut', above, t, 22.77, (-7-i*3, 7+i*3)),
                ('rest', remaining, t, cuts[i+1][1] if i < 2 else 22.77, (0, 0))):
                ident = f'shelf-{i}-{label}'
                self.defs.append(f'<clipPath id="{ident}"><path d="{path(poly)}Z"/></clipPath>')
                tr = Curve((0., 0.)).hold(t).key(t+.26, shift, 'out')
                if label == 'cut':
                    tr.go(21.9, 22.4, (0., 0.), 'in')
                glyph = f'<g clip-path="url(#{ident})"><use href="#glyph-S"/></g>'
                self.terrain.append(opacity(group(glyph, tr), visible(start, end)))

    def barrels(self):
        ink, paper = self.palette['fg'], self.palette['bg']
        for index, x in enumerate((365, 478, 591)):
            body = f'<path d="M-22,0Q-34,-26 -22,-52Q0,-58 22,-52Q34,-26 22,0Q0,6 -22,0Z" fill="{paper}" stroke="{ink}" stroke-width="1.4"/>'
            body += self.stroke('M-27,-42Q0,-37 27,-42M-27,-12Q0,-7 27,-12M-9,-54Q-17,-27 -9,2M9,-54Q17,-27 9,2', .9)
            tr, rot = Curve((float(x), float(DECK))), Curve((0., 0., -26.))
            if index == 2:
                body = f'<circle cx="0" cy="-26" r="26" fill="{paper}" stroke="{ink}" stroke-width="1.4"/>'
                body += self.stroke('M-20,-42L20,-10M-23,-29L12,-2M-10,-50L24,-23M-18,-45A26,26 0 0 1 20,-9M-20,-42A26,26 0 0 0 18,-7', .9)
                tr.go(16.15, 17.45, (float(x+49), float(DECK)))
                rot.go(16.15, 17.45, (108., 0., -26.), 'linear')
            self.back.append(opacity(group(group(body, rot, 'rotate'), tr), visible(13.3, (20., 20.55, 21.48)[index])))
        # The stuck blade is the exact final carried silhouette, in world space.
        a, b = self.lodged
        stuck_shape = f'<path d="{self.navy.sword(15.58)}" fill="{paper}" stroke="{self.palette["navy"]}" stroke-width="1.25" stroke-linejoin="round"/>'
        stuck = group(group(stuck_shape, transform=f'scale({SCALE})'), transform=f'translate({values(self.navy.position.at(15.58))})')
        wiggle = Curve((0., *b)).hold(15.58)
        for t in (16.02, 16.55, 17.17):
            wiggle.hold(t-.12).key(t, (3., *b)).key(t+.10, (-2., *b)).key(t+.20, (0., *b))
        self.props.append(opacity(group(stuck, wiggle, 'rotate'), visible(15.58, 20.55)))
        self.ring(15.58, b, 9)
        self.contacts.append(dict(kind='lodged', time=15.58, point=b, hilt=a))
        # Lantern pendulum is slow enough to make the room feel separate.
        lantern = self.stroke('M0,0V38M-7,38H7L10,57H-10ZM-7,61H7M-3,42V54M3,42V54', 1)
        swing = Curve((0., 0., 0.))
        for i in range(14):
            swing.key(13.3+i*.60, ((-1 if i%2 else 1)*(8-i*.3), 0., 0.), 'ease')
        self.back.append(group(group(lantern, swing, 'rotate'), transform=f'translate(515 {FLOOR+55})'))
        points = [self.fuse_start, (586, DECK-6), (540, DECK-9), (497, DECK-5), (451, DECK-9), (405, DECK-5), (365, DECK-24)]
        self.back.append(opacity(self.stroke(path(points), .9), visible(14.3, 20.01)))
        distances = [0.]
        for a, b in zip(points, points[1:]):
            distances.append(distances[-1]+math.dist(a, b))
        spark = Curve(points[0]).hold(18.22)
        for point, distance in zip(points[1:], distances[1:]):
            spark.key(18.22+1.78*distance/distances[-1], point)
        self.props.append(opacity(group(self.stroke('M-3,0H3M0,-3V3M-2,-2L2,2', 1), spark), visible(18.22, 20.02)))
        self.ring(18.22, self.fuse_start, 7, .18)

    def attached_props(self):
        ink, paper, n, p = self.palette['fg'], self.palette['bg'], self.navy, self.pirate
        scope = sampled(lambda t: path([n.world('right', t), add(n.world('right', t), (18, 0))]), [n.acting, n.position], window=(6.08, 6.58))
        self.props.append(opacity(f'<path d="{scope.keys[0][1]}" stroke="{ink}" stroke-width="5" fill="none">'+animation('d', scope, str)+'</path>', visible(6.08, 6.58)))
        dagger = sampled(lambda t: path([p.world('right', t), add(p.world('right', t), (-10, 5))]), [p.acting, p.position, p.facing], window=(18.01, 18.36))
        self.props.append(opacity(f'<path d="{dagger.keys[0][1]}" stroke="{ink}" stroke-width="1.6" fill="none">'+animation('d', dagger, str)+'</path>', visible(18.01, 18.36)))
        # An overlaid L hides the trapped torso, leaving the waving arm above it.
        L = self.letters['L']
        self.front.append(opacity(f'<use href="#glyph-L"/>', visible(27.31, 31.42)))
        hand = sampled(lambda t: n.world('right', t), [n.acting, n.position, n.angle], window=(28.3, 31.05))
        flag = self.stroke('M0,0V-22', 1)+f'<path d="M0,-22q9,-4 18,0v12q-9,-4 -18,0Z" fill="{paper}" stroke="{ink}" stroke-width=".9"/>'
        self.front.append(opacity(group(flag, hand), visible(28.30, 31.05)))

    def svg(self):
        ink = self.palette['fg']
        scene = ''.join(self.back)+''.join(letter.render() for letter in self.letters.values())+''.join(self.terrain)
        scene += self.pirate.render(self.palette)+group(self.navy.render(self.palette), clip_path='url(#trapped-officer)')+''.join(self.props)+''.join(self.front)+''.join(self.effects)
        scene = group(scene, self.camera)
        scene = group(group(group(scene, transform=f'translate({-W/2} {-H/2})'), self.zoom, 'scale'), transform=f'translate({W/2} {H/2})')
        scene = group(scene, self.shake)
        metadata = html.escape(json.dumps(dict(duration=T, acts=ACTS, beats=BEATS), separators=(',', ':')))
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">'
                '<title id="title">ANSIL — below deck</title><desc id="desc">'+html.escape(ALT)+'</desc>'
                f'<metadata id="film-timeline">{metadata}</metadata><defs>'+''.join(self.defs)+'</defs>'
                f'<rect width="{W}" height="{H}" fill="{self.palette["bg"]}"/><g fill="{ink}">'+scene+'</g></svg>')


def static_svg(svg):
    root = ET.fromstring(svg)
    for parent in list(root.iter()):
        for child in list(parent):
            if child.tag.rsplit('}', 1)[-1] in ('animate', 'animateTransform'):
                parent.remove(child)
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    return ET.tostring(root, encoding='unicode')


def lint_svg(svg):
    root = ET.fromstring(svg)
    nodes = list(root.iter()); parents = {child: parent for parent in nodes for child in parent}
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
        if len(node.get('keySplines', '').split(';')) != len(vals)-1:
            raise ValueError('Invalid spline count')
        if node.get('attributeName') == 'd':
            signatures = {re.sub(r'[-+]?(?:\d*\.)?\d+', '#', v) for v in vals}
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
                alpha = lerp(vs[i], vs[i+1], (t-ts[i])/(ts[i+1]-ts[i]))
            if alpha <= 0:
                return False
            node = parents.get(node)
        return True
    events.sort(key=lambda event: (event[0], event[1]))
    active = Counter(); peak, when = 0, 0.
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
    size = len(svg.encode('utf-8'))
    if size > SIZE_LIMIT or peak > ACTIVE_LIMIT:
        raise ValueError(f'Animation budget exceeded: {size} bytes, {peak} changing elements')
    return dict(bytes=size, elements=len(nodes), animation_tracks=len(animations),
                peak_changing_elements=peak, peak_time=round(when, 3), poses=len(POSES), duration=T)


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
        for name in ('make_raid.py','test_raid.py','README.md','preview.html'):
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
        preview_names = ['render-report.json', 'controls-report.json', 'player-desktop.png', 'player-mobile.png']
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
        film = Film(theme)
        svg = film.svg()
        if svg != Film(theme).svg():
            raise ValueError('Nondeterministic build')
        report = lint_svg(svg)
        report.update(sha256=hashlib.sha256(svg.encode()).hexdigest(), geometry_contacts=film.contacts,
                      used_poses=sorted(film.pirate.used | film.navy.used), engine='joint-rig-v3')
        reports[theme] = report
        files[theme] = args.out/f'raid-{theme}.svg'
        outputs[files[theme]] = svg
        outputs[args.out/f'raid-{theme}-static.svg'] = static_svg(svg)
        print(f'{theme}: {report["bytes"]:,} bytes, {report["peak_changing_elements"]} changing elements, {len(report["used_poses"])} performed poses', flush=True)
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
