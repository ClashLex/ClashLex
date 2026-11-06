# ANSIL - Below deck

A 34-second SVG short: a pirate turns the I into a mast, an officer chases him
down the S, and their fight breaks the deck. Below, a stuck sword, a rolling
barrel and a lit fuse send them back through the banner. The fragments retrace
their flight to rebuild ANSIL; a small surrender flag closes the argument.

The animation uses a jointed rig, geometry-driven contacts and a four-act
timeline. The cast, props, ASCII banner and story are original to this project.

## Build

Python 3.12 or later. Building and validation use only the standard library.

```sh
python raid/make_raid.py
python raid/make_raid.py --check
python -m unittest discover -s raid -p "test_*.py"
python raid/make_raid.py --out build/raid
python -m http.server 8000
```

Open `http://localhost:8000/raid/preview.html` for playback, scrubbing, speed,
act navigation and theme controls. The player reads the beat sheet directly
from SVG metadata. Reduced-motion preferences start playback paused; the
profile README provides separate static SVGs.

```sh
python -m pip install pillow playwright imageio-ffmpeg
python -m playwright install chromium
python raid/make_raid.py --preview --export
```

To use installed Chrome on Windows, append:

```sh
--browser "C:\Program Files\Google\Chrome\Application\chrome.exe"
```

`--fps` defaults to 12. Preview/export dependencies are optional for building,
but missing dependencies fail explicitly when rendering is requested.

## The new engine

- `Curve` rejects conflicting timestamps. Held anticipation, contact freezes
  and recovery have explicit keys; authoring errors never retime the film.
- `Actor` evaluates a two-bone rig with fixed arm and leg lengths. A single
  world-space joint evaluator supplies carried props, rope endpoints and cuts.
- Feet land on solid cells from `ART_RAW`. The supporting letter dips and the
  actor follows it until takeoff. Rope swings follow circular hand trajectories.
- Shelf cuts alternate down/up/down. The visible blade intersects solid glyph
  cells; those intersections define the fragment clipping planes.
- The lodged sword inherits its carried silhouette. Constrained wrists stay
  on its hilt while the hips shift through two increasingly strained pulls.
- Hats and coat tails settle after the main pose. The flag, lantern, rolling
  barrel and camera have their own timelines.
- A foreground deck mask hides the fall; a separate clip hides the officer's
  legs when L catches him. One camera travels between both physical floors.
- Twenty fragments collide with the floor using their rotated vertices, then
  visit exactly the same position and rotation samples in reverse.
- Body morphs and glyphs are shared through `defs`/`use`. Animation sampling
  is limited to visible prop windows. IDs and output are deterministic.

`ART_RAW` and `LETTER_COLS` preserve the editable vector ASCII identity. Glyphs
need no font. Keep exposed solid cells on A/I row 0, N rows 0-2, S row 0 and L
row 4 when editing terrain. `PALETTES` defines paper, ink, neutral rules and
one accent per character. `POSES`, `BEATS` and `ACTS` are the authoring vocabulary.
The actual choreography lives in `Film.choreograph()`.

## Beat sheet

| Time | Setup and payoff | Mechanism / callback |
| --- | --- | --- |
| 0.60 | A distant footfall ripples through ANSIL | A to L / footfall |
| 1.00 | The pirate swings in, kicks A, and lands on L | rope / A apex / L ledge |
| 2.35 | A climb turns I into a flag mast | I / flag |
| 3.45 | A dagger pins the wanted notice to S | S / dagger / poster |
| 4.50 | An officer slides down onto the N staircase | N / rope |
| 5.50 | Poster, pirate, poster; a spyglass double-take | poster / recognition |
| 6.60 | A whistle starts the chase down S | S shelves |
| 7.15 | Three connected swings separate the shelves | S / sword |
| 8.70 | The pirate escapes on the flag rope | flag / rope |
| 9.25 | A cut rope drops the flag over the officer | flag / blindness |
| 9.95 | A blind swing cuts the foot of I | I / blade |
| 10.60 | Both brace against the falling mast | I / resistance |
| 12.00 | The mast hits; a crack opens the deck | I / hole |
| 13.20 | The page gives way; a fall reveals below deck | hole / camera |
| 14.50 | A landing, a look up, and a renewed pursuit | lantern / barrels |
| 15.30 | The sword sticks; its owner pulls twice | sword / barrel |
| 16.50 | The pirate walks a barrel under his feet | barrel / balance |
| 17.80 | The dagger returns to strike the fuse | dagger / fuse |
| 18.60 | The officer chases the spark; the pirate takes cover | fuse / sword |
| 20.00 | Two blasts, a pause, then the third barrel | barrels / anticipation |
| 22.00 | They burst upward through ANSIL | hole / letters |
| 23.30 | L catches the officer; fragments fall and reverse | L / visible repair |
| 28.00 | A hat tip receives a very small surrender flag | flag / L |
| 31.00 | The rope returns and the page closes behind them | rope / deck |

## Outputs and verification

The build writes both animated SVGs, both static fallbacks, and `validation.json`.
The report contains byte size, changing-element concurrency, performed poses,
SHA-256 hashes and the actual geometry contacts. `--check` verifies all five
artifacts without writing them. The SVGs contain no scripts, CSS animation,
external resources, raster images, filters or `foreignObject`.

`--preview` renders every frame, one full contact sheet per act and theme,
compact storyboards, and a browser report. It compares pixels at 0, 33.999 and
34.001 seconds, and checks image embedding at 830px and 390px. `--export` adds
GIF, MP4 and `ansil-raid.zip`. Frames, previews and the zip are ignored local
artifacts; source, the four SVGs and validation are versioned.

Tests cover interpolated bone lengths, real foot/blade/hand contacts, sword
attachment, floor collisions, exact reversed fragment motion, deterministic
serialization, SVG restrictions, shared-instance concurrency and stale assets.
See `validation.json` for measured sizes, animation counts and contact records.
Optional browser checks write their results to `preview/render-report.json`.
