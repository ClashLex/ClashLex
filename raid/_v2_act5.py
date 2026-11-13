
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
