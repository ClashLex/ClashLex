
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
