"""Assemble the V2 generator from its engine and editable scene sources."""
from pathlib import Path

RAID = Path(__file__).resolve().parent
SOURCE = RAID / "make_raid_v2.py"
lines = SOURCE.read_text(encoding="utf-8").splitlines(keepends=True)


def find_line(prefix):
    matches = [i for i, line in enumerate(lines) if line.startswith(prefix)]
    if len(matches) != 1:
        raise ValueError(f"Expected one source line starting with {prefix!r}, found {len(matches)}")
    return matches[0]


act1_start = find_line("# ================================================================ ACT 1")
act1_end = find_line("def stuck_katana(")
chopper_start = find_line("class Chopper:")
act4_start = find_line("# ================================================================ ACT 4")
render_start = find_line("def render(theme):")
if not act1_start < act1_end < chopper_start < act4_start < render_start:
    raise ValueError("V2 generator sections are not in the expected order")

head = "".join(lines[:act1_start])
act1 = "".join(lines[act1_start:act1_end])
tail = "".join(lines[render_start:])

chopper_end = act4_start
chopper = "".join(lines[chopper_start:chopper_end]).rstrip() + "\n"

scene = (
    (RAID / "_v2_acts_2_3.py").read_text(encoding="utf-8") + "\n\n"
    + chopper + "\n"
    + (RAID / "_v2_act4.py").read_text(encoding="utf-8") + "\n"
    + (RAID / "_v2_act5.py").read_text(encoding="utf-8") + "\n"
    + (RAID / "_v2_act6.py").read_text(encoding="utf-8") + "\n\n"
)

SOURCE.write_text(head + act1 + scene + tail, encoding="utf-8")
print("assembled", len((head + act1 + scene + tail).splitlines()), "lines")
