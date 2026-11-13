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
