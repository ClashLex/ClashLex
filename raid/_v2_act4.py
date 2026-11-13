
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
