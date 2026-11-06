# the raid

The top of the profile README looks like plain text. It isn't. `raid-light.svg` and
`raid-dark.svg` are 31-second looping animated SVGs (pure SMIL: no JavaScript, no CSS,
no external files), so GitHub renders them as-is inside `<img>`.

`make_raid.py` generates both. One file, no framework.

```
pip install pillow
python3 make_raid.py              # writes raid-light.svg + raid-dark.svg
python3 make_raid.py --preview    # also saves PNG frames to ./preview
                                  # (pip install playwright && playwright install chromium)
```

Open `preview.html` in a browser to see both themes side by side before you push.

## Edit the banner

The page content is ASCII art. `ART_RAW`, `LETTER_COLS`, `ALT` and the `POSTER_*` strings
sit at the top of `make_raid.py`.

- `ART_RAW`: paste any block-letter ASCII art made of `█ ╗ ╔ ╝ ╚ ═ ║` (for example from
  patorjk.com, font "ANSI Shadow"). It is drawn as vector shapes, not font text, so it
  looks identical everywhere.
- `LETTER_COLS`: one `(start_col, end_col)` pair per letter. Each letter becomes its own
  piece, so the officer cuts them one by one. Count columns in the art; every letter is
  the same row width.
- Sized by `CW, CH` (one character cell in px) and placed by `X0, Y0`. Keep the banner
  under about 460px wide so it stays clear of the poster at x≈655.
- If a paste drops the leading space of the first row, the script repairs it.

## The story (seconds)

The fight happens on top of the ANSIL banner. The letter tops are the platform, and each letter
gives under a foot, jumps when hit, and can be cut out from under someone.

| t | beat |
|---|------|
| 0.7 | distant boom, the banner shivers |
| 1.0 | pirate swings in on a rope, flips onto the L |
| 2.7 | dagger pins the bounty poster |
| 3.8 | navy officer leaps in from off-page, flipping, lands on the A |
| 5.3 | low air-slash skims the banner, the pirate hops it, it cuts the poster |
| 6.1 | officer runs the tops of the letters, each one dips under his foot |
| 7.3 | three sword clashes; the last one cracks each letter in proportion to its distance from the blow |
| 9.0 | pirate's spin; officer flips over it and lands behind him |
| 10.6 | wind-up, then a chop cuts the I out from under the pirate |
| 11.2 | officer stabs the floor, sword sticks, pirate rolls clear |
| 12.6 | pirate kicks him in the back into the A, which loses a chunk from the corner he hit |
| 15.0 | officer dashes back, yanks the sword out, second duel |
| 16.9 | pirate is disarmed, his sword spins into the floor |
| 17.5 | cannon pops up, pirate hops it and lights the fuse |
| 19.1 | BOOM: officer is launched left through every letter, each one breaking where he hits it |
| 20.9 | a horn: six sailors pour in from the left |
| 22.5 | pirate relights the cannon, the line charges, sees the fuse, skids |
| 23.2 | BOOM: the ball bowls through the line, then bounces off the letters and the banner collapses |
| 25.2 | the opening rope drops again, pirate grabs it and is hauled out of the page |
| 27.0 | a tide sweeps the page and restores everything for the loop |

## How things break

Two kinds of damage, chosen by what hit the letter:

- **Blade = a cut.** `Piece.slice()` makes two copies clipped to either side of a line (the line is
  where the blade crossed). Both halves fall, bounce and fade. The poster is cut the same way, but
  its halves flutter down like paper (`paper=True`).
- **Blunt = a shatter.** `Piece.crack()` grows cracks outward from the impact point
  (`stroke-dashoffset`), then `Piece.release()` breaks loose everything within `R` of it. The
  letter is pre-cut into Voronoi fragments (a jittered grid of seeds, each cell clipped to the
  letter by half-planes). Each fragment's launch is worked out in Python:
  speed falls off with distance from the impact, direction is the blow plus "away from the
  impact point", spin comes from how far off-centre it was hit, and the shock reaches far
  fragments a moment later. Then gravity, a floor bounce and a fade, written out as keyframes.
  Fragments outside `R` stay in place, so a letter can lose only a corner, and a second hit
  carries on from the damage of the first.
- A light hit only calls `Scene.scuff()`: cracks and a few chips, nothing detaches.

## How it works

- **Track** is a list of `(time, value, easing)` keyframes. `anim()` turns it into one
  `<animate>` with `keyTimes` and `keySplines`. Every element shares one timeline, so
  everything stays in sync with no scripting.
- **Char** is a stick figure. A pose is a dict of joint points; each limb is a
  `<polyline points>` and SMIL morphs it from pose to pose. A run cycle is six poses.
  Squash/stretch, facing and rotation are nested transform groups.
- **Effects**: smears that follow the blade tip, afterimages, comic starbursts, shock rings, speed
  lines, anticipation rings, hit-stop and screen shake.
- **Piece** can move, rotate, fade, pop in, and be cut in half (two copies of the
  same content, each clipped to one side of the cut line).
- The banner is drawn from rectangles and lines (one group per letter), so it never
  depends on which monospace font the viewer has.
- `eased()` reimplements the browser's cubic-bezier, so Python can ask where something is
  mid-tween (`Char.world()`) and land sparks and thrown daggers exactly on the hand.
- The wave covers the page fully for about a second. Letters, poster and props are reset
  while it is covering, so the loop seam is invisible.

Theme: pirate vs navy officer, both original characters. Light and dark differ only in the
`PALETTES` dict.
