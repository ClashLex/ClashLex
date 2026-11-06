# ANSIL — below deck

A 34-second loop in four acts. A pirate turns the I into a mast, an officer cuts
his way down the S, and the fallen mast breaks the deck. A chase among barrels
below launches them back through the banner. Its fragments reverse their fall,
rebuilding A, N, S, I, L. A surrender flag and the returning rope close the loop.

The profile uses self-contained SMIL SVGs: no scripts, CSS animation, fonts to
download, images, filters, or external references. Light and dark are palette
variants. Static SVGs provide a reduced-motion alternative.

## Build and watch

Python 3.12 or later; building and linting use only the standard library.

```sh
python raid/make_raid.py
python raid/make_raid.py --check
python -m unittest discover -s raid -p "test_*.py"
python raid/make_raid.py --out build/raid
python -m http.server 8000
```

Open `http://localhost:8000/raid/preview.html` for play/pause, a timeline, act
navigation, speed, and theme controls. Opening the HTML directly still displays
the banner; the controls need HTTP because they load the SVG document.

For the complete render package:

```sh
python -m pip install pillow playwright imageio-ffmpeg
python -m playwright install chromium
python raid/make_raid.py --preview --export
```

An installed Chrome/Chromium can be selected with `--browser /path/to/browser`.
On Windows, quote the path, for example
`--browser "C:\Program Files\Google\Chrome\Application\chrome.exe"`.
`--fps` defaults to 12. Missing preview/export dependencies fail with a nonzero
status rather than silently omitting the requested artifacts.

The output includes:

- `raid-{light,dark}.svg` and matching `-static.svg` files.
- `validation.json`: size, track/element counts, concurrency, poses and hashes.
- `preview/{theme}/frame-*.png`: every frame at the selected rate.
- `preview/{theme}-01-arrival.jpg` through `04-return.jpg`: all frames per act.
- `preview/{theme}-storyboard.jpg`: a compact 24-beat overview.
- `preview/raid-{theme}.gif` and `.mp4` when `--export` is selected.
- `preview/render-report.json`: browser embedding and pixel-equal loop checks.
- `ansil-raid.zip`: SVGs, available source/docs and shareable previews.

PNG frames, contact sheets, video files and the release zip are local build
artifacts and ignored by Git. The four SVGs and `validation.json` are committed.

## Beat sheet

| Time | Action | Mechanism / callback |
| --- | --- | --- |
| 0.6 | A ripple travels A to L | footfalls |
| 1.0 | Rope swing, A apex kick, L ledge landing | rope / A / L |
| 2.6 | Climb the I and tie a flag | I / flag |
| 3.8 | Dagger pins a wanted notice to the S | dagger / poster |
| 4.8 | Officer descends onto the N staircase | N / rope |
| 5.8 | Poster, pirate, poster: the spyglass confirms it | poster |
| 6.6 | A whistle; the pirate drops down the S | S shelves |
| 7.4 | Three blade contacts separate the S shelves | S / sword |
| 8.5 | Flag rope swing; a slash drops the flag on the officer | flag / rope |
| 9.6 | Blinded swing cuts the I at its foot | flag / I |
| 10.7 | The I falls like a mast; both try to stop it | I |
| 12.0 | The mast hits the deck; cracks race out | I / hole |
| 13.2 | The letters lean in; both fall through | hole |
| 14.4 | Below deck: a lantern reveals the barrel room | hole / lantern |
| 15.4 | The officer sticks his sword into a barrel | sword |
| 16.4 | Pirate balances on a rolling barrel; officer pulls | barrel / sword |
| 17.8 | The dagger strikes a spark on the fuse | dagger / fuse |
| 18.8 | Officer chases the spark; the pirate ducks | fuse |
| 20.0 | Three barrels burst in sequence | barrels / fuse |
| 22.0 | Blast through the hole; ANSIL shatters from below | hole / letters |
| 23.4 | Officer wedges into the L while rubble falls | L |
| 25.0 | Fragments reverse their fall and lock A to L | letters / heal |
| 28.2 | Pirate tips his hat; a surrender flag emerges from L | flag / L |
| 31.0 | Opening rope returns; the pirate leaves; the deck heals | rope / hole |

Beat times mark setups; holds, secondary motion, recoveries and payoffs continue
between them. They are not isolated one-frame events.

## Edit the animation

`ART_RAW` and `LETTER_COLS` define the five vector glyphs. Keep five letters and
solid walkable cells in the rows used by the story: A/I row 0, N rows 0–3, S rows
0/2/4, L row 4. Glyph edits feed the surface map and shared definitions.
`CW`, `CH`, `X0`, `Y0` position the artwork; changing the overall layout may also
require retuning the room and rope staging.

`PALETTES` contains paper, ink, a neutral rule color, and one accent per character.
`ALT` becomes the SVG description; update the root README's image description
when changing the story. `POSTER_*` edits the wanted notice.

- `Track` rejects conflicting and out-of-order keys instead of silently retiming them.
- `Char` morphs a composite body path rather than a separate track for every limb.
  There are 68 poses, including climbs, gaze changes, blind swings, pushes,
  balance, pulling, flint, shielding, bowing and surrender.
- `Letter.surface()` reads exposed solid cells. `segment_cross()` checks the
  actual hand-to-tip segment against the letter before registering a cut.
- Each glyph exists once in `defs`; shelves and fragments use local `use` references.
- `follow()` supplies delayed hat and coat response. Flag, rope and lantern
  tracks add settling motion. The camera combines pan, punch and shake.
- Shards collide using rotated vertices. Reconstruction visits their exact
  position and rotation samples backwards, then reveals the intact glyph.
- A page-minus-hole foreground deck clip hides legs during the crossing.

## Verification

Every build checks XML, internal references, compatible path morphs, strict
keyframe order, deterministic output, a 750,000-byte per-SVG budget, at least 60
poses, and a maximum of 60 simultaneously changing elements. Concurrency is
measured by sweeping all changing keyframe intervals, excluding elements under
fully transparent ancestors. It counts elements, not attributes or total tracks.
Animated definitions count each visible `use` instance separately.

Preview generation compares rendered pixels at 0, 33.999 and 34.001 seconds,
then checks SVG image embedding at 830px and 390px widths. `--check` detects stale
animated and static SVGs. Browser rendering is a separate optional step; a
successful source-only build does not claim a visual seam check.

The reference was supplied during development as `../inspiration.py` and reviewed
for timing, physical contacts, occlusion and silhouette readability. Its characters,
franchise props, story and code were not incorporated. The original raid's poses
and vector glyphs remain the starting vocabulary. See `QA.md` for the review.
