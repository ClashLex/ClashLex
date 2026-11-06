# ANSIL - README rumble

A direct adaptation of the supplied `inspiration.py`, recovered from repository
history. The original 31-second animation, 88-pose library, six acts, characters,
weapons, effects and scene transitions are preserved. The profile now reads:

> Hi, I'm Ansil.
>
> B.Tech CSE Undergraduate.
>
> Developer. Experimenter. Builder.
>
> I build, break, and rebuild things.

The reference's crossed-out diary line is removed. The three bio lines occupy
its three action-bearing rows. The fight kicks `rebuild`, breaks through
`things.`, and slices `break,`, `Experimenter.`, and `Undergraduate.`.
All seven letters of `rebuild` use the reference's existing flight patterns.

## Build and preview

Python 3.12 or later, Pillow, and Liberation Sans (Linux) or Arial (Windows/macOS).
Pillow measures the text during the build; the generated SVG needs no Python,
JavaScript, CSS animation, external fonts, raster images or filters.

```sh
python -m pip install Pillow
python raid/make_raid.py
python raid/make_raid.py --check
python -m unittest discover -s raid -p "test_*.py"
python -m http.server 8000
```

Open `http://localhost:8000/raid/preview.html` for play/pause, scrubbing, speed,
theme switching and navigation through all six acts. Reduced-motion preferences
start the player paused. The profile README always selects an animated SVG for
the current theme; it has no automatic static-image fallback.

```sh
python -m pip install playwright imageio-ffmpeg
python -m playwright install chromium
python raid/make_raid.py --preview --export
```

An installed Chrome can be used with
`--browser "C:\Program Files\Google\Chrome\Application\chrome.exe"`.
`--fps` defaults to 12; `--out build/raid` selects another output directory.
For a particular Liberation Sans installation, set `RAID_FONT_DIR` to the
folder containing `LiberationSans-Regular.ttf` and `LiberationSans-Bold.ttf`.
Use the same font installation when comparing builds across machines.

The build writes `raid-light.svg`, `raid-dark.svg`, both optional `-static.svg` exports,
and `validation.json`. Optional rendering creates frame PNGs, six act sheets
per theme, compact storyboards, GIF/MP4 previews and `ansil-raid.zip`.
MP4 export pads the reference's 277px height to 278px for H.264 compatibility.
Generated preview files and the release zip are ignored by Git.

## Editing the profile

`H1_TEXT` is the heading. `PARAS` contains the four text slots; the first is
intentionally empty. `WORD_TARGETS` maps five choreography roles to exact words
in those slots, including punctuation. Update the mapping if those words change.
The reference's layout engine measures the new text and supplies the action
coordinates. `PALETTES` retains the original light and dark colors.

The supplied engine is kept intact apart from deterministic clipping IDs.
A portable font loader, accessible SVG metadata, the CLI, validation and
preview/export tools provide the repository integration. The reference source
fingerprint is recorded as `REFERENCE_SHA256` and in the validation report.
The previous pirate/ASCII animation engine is no longer used.

## Acts

| Display time | Act |
| --- | --- |
| 0.00-5.53s | Break In |
| 5.53-7.91s | Challenge |
| 7.91-11.89s | Chase |
| 11.89-17.73s | Escalation |
| 17.73-25.45s | Counterattack |
| 25.45-31.00s | Reset |

Display times include the reference's 0.25-second lead trim. `BEATS` supplies
the player labels from the actual action timeline; it does not retime the film.

## Validation

`--check` verifies all five generated artifacts without writing. The linter
checks XML, references, strict serialized timing, path morph compatibility,
and executable/external content. It reports the actual file size and concurrent
animation count; the full reference effects are retained, including their higher
concurrency than the previous simplified animation.

Tests check the exact bio, all seven kicked letters, the climb handoff, staged
limb visibility, restored cut words, weapon geometry, world coordinates, the
lead trim, deterministic IDs across Python hash seeds and stale asset detection.
Browser rendering checks pixel equality at 0, 30.999 and 31.001 seconds and
image embedding at desktop and mobile widths, including a check that pixels
change while the SVG plays inside an image element. Results are written to
`preview/render-report.json`.

Before personalization, 77 sampled moments per theme were pixel-identical to
the recovered reference under the same font and browser; the comparison is
recorded in `preview/reference-comparison.json`. All reference functions
and methods remain unchanged except `Word.svg` (stable IDs) and `render`
(accessibility and player metadata). The seven-letter flight loop is the only
choreography adjustment needed for the supplied bio.
