"""Assemble raid/make_raid_v2.py from the V1 engine slices and the V2 act sources.

V2 keeps V1's engine, Act 1, renderer and CLI while replacing Acts 2-6. Edit the
act sources, then run this script and regenerate the assets:

    python raid/assemble_v2.py
    python raid/make_raid_v2.py --out build/raid-v2
"""
from pathlib import Path

RAID = Path(__file__).resolve().parent
SRC = RAID / "make_raid.py"

lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)

# Engine: constants, tracks, poses, Char, Word, layout, generic effects and cast.
head = "".join(lines[:1284])
head = head.replace("FADE = (27.13, 27.63)", "FADE = (26.55, 27.05)")
head = head.replace("RESTORE = (27.23, 28.23)", "RESTORE = (26.65, 27.65)")

# Act 1: break-in, hole, climb and the "rebuild" kick. The hand-off already ends
# with Red facing the heading rule, so no body change is needed.
act1 = "".join(lines[1285:1449])

# Renderer, static export, linter, preview and CLI.
tail = "".join(lines[2606:])
tail = tail.replace(
    'out.append(ink.svg(p["fg"]))',
    'out.append(ink.svg(p["fg"], weapons=p, katana_win=(6.0, 26.0)))',
)
tail = tail.replace(
    'out.append(ink.svg(p["void_fg"], op_track=VOID_WIN))',
    'out.append(ink.svg(p["void_fg"], weapons=p, op_track=BANKAI_INK_WIN, katana_win=(18.8, 25.0)))',
)
tail = tail.replace(
    "katana_win=(6.0, 17.4), pick_win=(24.8, 26.4)",
    "katana_win=(6.0, 24.4), pick_win=(24.3, 25.6)",
)

# The Chopper class lives in V1's Act 4, outside the engine slice. Copy it
# verbatim so the cameo keeps V1's geometry and boot-grip helper.
start = next(i for i, line in enumerate(lines) if line.startswith("class Chopper:"))
end = next(i for i in range(start + 1, len(lines))
           if lines[i] and not lines[i][0].isspace() and not lines[i].startswith("#"))
chopper = "".join(lines[start:end]).rstrip() + "\n"

# Keep the source files independently editable but preserve the blank-line
# separation the assembled scene expects between acts.
scene = (
    (RAID / "_v2_acts_2_3.py").read_text(encoding="utf-8") + "\n\n"
    + chopper + "\n"
    + (RAID / "_v2_act4.py").read_text(encoding="utf-8") + "\n"
    + (RAID / "_v2_act5.py").read_text(encoding="utf-8") + "\n"
    + (RAID / "_v2_act6.py").read_text(encoding="utf-8") + "\n\n"
)

out = head + act1 + scene + tail
(RAID / "make_raid_v2.py").write_text(out, encoding="utf-8")
print("assembled", len(out.splitlines()), "lines")
