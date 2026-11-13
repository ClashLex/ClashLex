# “Margin Duel” — V2 production animation

Design and implementation reference for the published README animation.

- **Production:** `main`
- **Generator:** `raid/make_raid_v2.py`
- **Output:** tracked V2 assets in `raid/`
- **Status:** published; V2 is the only maintained generator
- **Historical baseline:** V1 assets at commit `a50b87c`

---

## 1. Goals

1. Replace the fight choreography completely while keeping the visual quality,
   timing discipline and rendering pipeline of V1.
2. Keep the same profile copy, 830×277 stage, 31-second loop, six-act structure,
   light/dark themes and SMIL-only SVG output.
3. Reuse the proven vocabulary: cracks, hole, word shattering, word slicing,
   dust, sparks, impact lines, slash arcs, hitstop, camera shake, trails,
   clones, love charm, blocks, rubble and the void/reset.
4. Keep Chopper as a cameo.
5. Replace “Domain Expansion” with an original **Bankai: Margin Storm**.
6. Use the love-charm sequence and character multiplication in new situations
   that serve the vertical “margin duel” rather than repeating V1’s staging.
7. Keep editable act sources and the assembled generator together so builds
   remain reproducible without the retired V1 generator.

### Non-goals

- No raster images, external fonts, CSS animation, JavaScript, filters or
  external assets inside the SVG.
- No change to the bio text.
- No change to the 31-second duration or six-act player contract.
- No engine redesign; the choreography continues to use the established,
  tested animation primitives.

---

## 2. Source organization

`make_raid_v2.py` is the assembled, self-contained production generator.
`assemble_v2.py` uses its engine, opening act, Chopper definition, and renderer
as a template, then inserts the separately editable act sources. It discovers
these sections by their markers rather than depending on the retired V1 file
or fixed line numbers.

The generated light/dark animated SVGs, static exports, and validation report
are committed beside the generator. V1-only generator and test files have
been removed; historical profile material remains under `archive/`.

---

## 3. The new story: “Margin Duel”

The page is treated as a vertical arena:

- the heading rule (`y=50`) is a tightrope;
- the bio lines (`y=84`, `124`, `164`, `204`) are ledges;
- the floor (`y=272`) is the pit;
- the words are the terrain, shields, projectiles and casualties;
- the left margin is the climb; the right side is the Bankai stage.

The fight is a duel between **Red** (the intruder) and **Ink** (the margin’s
guardian). V1’s clone/laser/wall/domain sequence is replaced by an ascent, a
three-level word ladder, a vertical clone pincer, a charm reversal and a Bankai.

### Act structure

| Display time | Act | Purpose |
| --- | --- | --- |
| 0.00–5.53 | Break In | Red tears out of “things.” and scatters “rebuild” |
| 5.53–7.91 | The Climb | Red climbs the bio lines; first clash on the rule |
| 7.91–11.89 | The Word Ladder | Rule breaks; three words are cut during level swaps |
| 11.89–17.73 | Chopper / Clones / Charm | Cameo, vertical clone pincer, love-charm reversal |
| 17.73–25.45 | Bankai: Margin Storm | Ink’s Bankai; block wall; Red buried and digs out |
| 25.45–31.00 | Reset | Page and words heal; salute; Chopper waves; loop |

---

## 4. Beat sheet

The canonical beat list lives in `BEATS` and is emitted into the SVG’s
`#film-timeline` metadata. All times below are **display times** (authoring
times minus the 0.25-second lead trim), so they match what the player shows.

| Display | Act | Beat | Tag |
| --- | --- | --- | --- |
| 0.65 | 1 | Cracks spread through a word | page |
| 1.45 | 1 | The page shatters and a hole opens | hole |
| 2.07 | 1 | Hands catch the rim; the figure climbs out | climb |
| 3.61 | 1 | Both feet reach the page | handoff |
| 4.71 | 1 | A landing, a dust-off, a look around | acting |
| 5.39 | 1 | A jump kick scatters the letters | type |
| 5.73 | 2 | Ink waits on the heading rule | arrival |
| 6.05 | 2 | Red climbs the bio lines like a staircase | climb |
| 6.81 | 2 | The first clash rings out on the rule | clash |
| 7.09 | 2 | A teleport turns a slash into a miss | teleport |
| 7.59 | 2 | The counter-cut nicks the rule | rule break |
| 8.04 | 3 | A cut splits Experimenter. | first cut |
| 8.11 | 3 | A rising cut splits Undergraduate. | second cut |
| 8.45 | 3 | A third cut splits break, | third cut |
| 9.33 | 3 | The katana sticks in the floor | sword |
| 10.57 | 3 | A kick interrupts the pulling | kick |
| 12.10 | 4 | Chopper grabs a boot | Chopper |
| 13.27 | 4 | Three clones dive from three levels | clones |
| 14.69 | 4 | A charm heart finds its mark | heart |
| 16.30 | 4 | The charm turns dark | reversal |
| 17.30 | 4→5 | Bankai: Margin Storm | Bankai |
| 18.15 | 5 | The ink field and the spectral blade rise | field |
| 18.90 | 5 | The blade storm begins | storm |
| 21.70 | 5 | Six blocks become a wall | wall |
| 23.15 | 5 | The final cut breaks the wall | impact |
| 24.20 | 5 | A pickaxe clears the rubble | pickaxe |
| 24.65 | 5 | The Bankai collapses into the sword | collapse |
| 27.00 | 6 | The page heals | reset |
| 28.10 | 6 | Words and rule return | restore |
| 28.80 | 6 | A salute, a bow | salute |
| 29.35 | 6 | Chopper peeks in to wave | cameo |
| 30.35 | 6 | The page is quiet again | loop |

### 4.1 Staging notes

**Act 1 — Break In (0.00–5.53).** Reused byte-for-byte from V1: the hole, the
climb, the hand-off and the “rebuild” kick. Red lands at `x≈124` facing left;
Act 2 turns him toward Ink at 6.02 before the staircase begins.

**Act 2 — The Climb (5.53–7.91).** Ink appears on the heading rule at `x=270`
and walks to `x=240`. Red uses the bio lines as a staircase
(`y=204 → 164 → 124 → 84 → 50`) with a `!` mark at display 5.95. The first
clash is on the rule at 6.81. Ink teleports behind Red, taps him, and the
counter-cut opens a visible gap in the rule at 7.59.

**Act 3 — The Word Ladder (7.91–11.89).** The rule gives way and both fighters
fall to the words. The three cuts are split across both fighters during level
swaps: Red cuts “Experimenter.” on the way down, Ink cuts “Undergraduate.” on
the way up, and Red cuts “break,” on a third drop. Both reach the floor, Red
buries the katana at `x=560`, and the tug-of-war begins. Ink’s kick at 10.57
sends Red to `x=470`; Ink whistles while Red lies on the floor.

**Act 4 — Chopper / Clones / Charm (11.89–17.73).** Chopper enters from the
right, grabs Red’s boot during the shake-off, and is flung to `x=650` before
settling at `x=780` as a sideline witness. Red forms three clones on lines
1/2/3 (`x=300/380/460`); they dive as a vertical pincer, two collide at
`(560,190)`, and the third is cut at `(700,230)`. Red switches to the charm:
the heart crosses the page, Ink floats, the orbiting hearts darken, and the
crushed charm becomes the Bankai trigger.

**Act 5 — Bankai: Margin Storm (17.73–25.45).** The announcement bubble reads
“Bankai. / Margin Storm.” A dark ink field expands to radius 740, the ghosted
bio text stays visible, and a giant spectral katana rises at `x=716`. Twelve
blade-crescents orbit at radii 150–260. Red cuts three out of the air, is hit,
and builds a six-block wall. The final cut at 23.15 breaks the wall and buries
him. He digs out with the pickaxe, and the field retracts into Ink’s sword.

**Act 6 — Reset (25.45–31.00).** Ink sheathes; Red drops off the rubble and
runs to `x=540`, Ink walks to `x=600`. The rule heals, the cut words and
kicked letters restore, and the hole closes. They salute at 28.80, Chopper
peeks back in at 29.35, and everyone is off the page before the loop point.

### 4.2 Final timing deviations from the plan

- The Bankai field collapses at authoring 24.10–24.90 (display 23.85–24.65),
  not 24.90–25.30, so the pickaxe escape is visible. The giant blade fades by
  24.35 and the fallen wall is gone by 23.62.
- The reset centers Red at `x=540` and Ink at `x=600`. The page heal uses
  `FADE=(26.55, 27.05)` and `RESTORE=(26.65, 27.65)`, earlier than V1.
- The storm grew from 9 to 12 blades at radii 150–260 with a 0.72 vertical
  squash, so it fills the page without clipping the stage.
- The wall and the giant blade render in `over_red`; the final cut line is in
  `top`. This keeps the blade above the ink field and the wall above both,
  while the cut still lands on top of everything.
- Ink is armed in V2. The renderer passes `weapons=p` to both the normal and
  spectral Ink, with katana windows `6.0–26.0` and `18.8–25.0`.
- Chopper waits at `x=780` after the shake-off. `follow_boot()` is authored
  after Red’s jump tracks so the grip samples the final boot path.
- The first `!` mark is placed at 6.20 (display 5.95) after the climb hops, so
  `head_mark()` samples Red’s airborne head instead of his floor pose.

---

## 5. Reuse map

### Kept exactly

- `T`, `W`, `H`, `FLOOR`, `LEAD_TRIM`, `PALETTES`, `FONT`, `FONT_STACK`
- `Track`, easing, `animate`, `animate_tf`
- the 88-pose library and `Char` world transform
- `Word` layout, `shake`, `fly`, `dip`, `slice`, `restore`
- `crack_set`, `shards_svg`, `hole_svg`
- `spark`, `dust`, `poof`, `speed_lines`, `crescent`, `smear_line`,
  `impact_lines`, `flash`, `mark`, `blink`, `ghost`, `teleport`, `trail`,
  `jolt`, `rumble`, `hit`, `heavy_slash`, `heavy_upswing`, `blade_cut_point`,
  `hop`, `stuck_katana`
- `render`, `static_svg`, `lint_svg`, `preview`, `bundle`, `main`
- the final metadata contract and the player’s act/beat format

### Reused with new staging

| Component | V1 use | V2 use |
| --- | --- | --- |
| word kick | Red kicks “rebuild” on the floor | same opening, but it becomes the staircase debris |
| cuts | three cuts by Red in a row | three cuts split across both fighters during level swaps |
| katana stuck | floor tug-of-war | same mechanic, new position after the word ladder |
| Chopper | boot grab during tug-of-war | boot grab during the same tug-of-war, then sideline witness |
| clones | three clones collide side-by-side | vertical three-level pincer; two collide midair |
| charm heart | Red charms Ink; Ink floats | Red charms Ink; the charm is crushed and becomes the Bankai trigger |
| blocks | Red builds a wall; Ink pushes it over | Red builds a wall against Bankai; Bankai cuts through and buries him |
| pickaxe | Red digs out of the block pile | same, but the pile is Bankai rubble |
| void | Domain Expansion swallows the fight | Bankai ink field; retracts into Ink’s sword |

### New or adapted effects

- `rule_break_svg` — a visible gap in the heading rule with splinters.
- `bankai_bubble_svg` — “Bankai. / Margin Storm.” speech bubble.
- `bankai_svg` — dark ink field, giant spectral blade, blade-crescent storm,
  ghost text and the final vertical cut.
- `bankai_storm_svg` — orbiting/falling blade crescents.
- `bankai_blade_svg` — the giant spectral katana silhouette.
- `block wall` / `loose blocks` — copied from V1 with new coordinates.
- `heart_svg` / `float_hearts_svg` — copied with new coordinates and a dark
  phase for the Bankai trigger.

---

## 6. Technical implementation

### 6.1 Source layout and assembly

`raid/make_raid_v2.py` is assembled by `raid/assemble_v2.py` from its own
engine, opening act, Chopper definition, and renderer, found by section
markers, plus the editable scene sources:

1. `raid/_v2_acts_2_3.py` (Acts 2–3 and the rule-gap prop);
2. `raid/_v2_act4.py` (Chopper, clones, charm);
3. `raid/_v2_act5.py` (Bankai, wall, rubble, pickaxe);
4. `raid/_v2_act6.py` (reset, restore, salute, metadata).

Run `python raid/assemble_v2.py` after editing any act source. The assembled
file is the production generator; the act sources are the editable units.

### 6.2 Scene globals the renderer expects

`render()` reads these from the scene module:

- `HOLE_PTS`, `HOLE_SCALE`, `HOLE_*`
- `FRAME`
- `LINES`, `NL`, `RD`
- `crawl`, `red`, `ink`, `c1`, `c2`, `c3`, `chopper`
- `LAYERS`
- `glow_svg`, `void_svg`
- `ACTS`, `BEATS`, `ALT`, `H1_TEXT`

The V2 scene must define all of them, even if an effect is unused.

### 6.3 Timing discipline

Every new action uses the existing helpers:

- `anticipation` 0.08–0.4 s;
- `contact` 0.045–0.1 s with `snap` or `out`;
- `follow-through` 0.1–0.3 s;
- `recovery` 0.2–0.4 s;
- hitstop on both actors at major contacts;
- no more than one major camera shake per exchange;
- effects fade before the next beat.

The 0.25-second lead trim is applied by `animate()`; authoring times in the
scene are pre-trim and the renderer shifts them automatically.

### 6.4 Determinism

- no sets or dict iteration in geometry output;
- all random-looking values use `rnd(seed)`;
- clipping IDs use the existing SHA-256 scheme;
- `render(theme)` must be identical on repeated calls;
- `PYTHONHASHSEED=1` and `349` must produce the same hash.

### 6.5 Renderer hooks

`render()` keeps the layer order:

```
background → H1 → rule → words → NL → hole → cracks
→ crawl (clipped) → RD → debris/props/fx_low → glow
→ clones → ink → fx_mid → void/bankai (field, ghost text, storm)
→ crawl (page clip) → hole edge → chopper → red
→ over_red (wall, loose blocks, giant blade)
→ ink (spectral window) → fx_high (bubble, hearts, cut crack)
→ marks → top (final cut line)
```

The ink field, ghost text and blade storm live in `void_svg`; they sit above
the page but behind the fighters. The giant blade and the fallen wall are in
`over_red`, so they read above the dark field and the wall reads above Red.
The spectral Ink is drawn after `over_red`, and the final cut line is in
`top`, above everything. The renderer passes `weapons=p` to both Ink copies;
the normal katana window is `6.0–26.0` and the spectral window is `18.8–25.0`.

### 6.6 Metadata

`ACTS` and `BEATS` are rewritten for the new story. `ALT` describes the Margin
Duel. The player reads the same `#film-timeline` JSON, so no player changes are
required.

---

## 7. Quality gates and QA results

The gates below are the review contract. The current branch has passed the
build, unit-test, loop-seam, embedded-image and reduced-motion checks. The
storyboards and act sheets have been reviewed in both themes.

### Build and contract — pass

- `python raid/assemble_v2.py` → 2,866 lines;
- `python raid/make_raid_v2.py --out build/raid-v2` → both themes,
  766,834 bytes each, 95 changing elements, 88 poses;
- `python raid/make_raid_v2.py --out build/raid-v2 --check` →
  `Generated assets are current.`;
- static SVGs contain no animation nodes;
- XML is valid; no duplicate IDs; no missing references;
- no `script`, `foreignObject`, `image`, `filter`, `style` or external URL.

### Unit tests — pass

`python -m unittest discover -s raid -p 'test_*.py'` → **22 V2 tests**,
all passing. The suite covers:

- exact bio copy and word targets;
- six-act metadata and the Margin Duel beat tags;
- Bankai replaces Domain Expansion, including the bubble text and ALT;
- Bankai effects are invisible at 0 and 31;
- the field reaches radius 740 and retracts into the sword;
- twelve storm blades at radii 150–260;
- Chopper’s boot grip stays within 0.2 px during the shake-off;
- Chopper enters, leaves before Bankai, and waves at the end;
- the vertical clone pincer uses three levels and poofs by 14.06;
- the charm reaches Ink, turns dark, and triggers the Bankai;
- the rule gap heals and all cut words restore;
- kicked letters, characters and Chopper leave a clean loop;
- the reset centers Red at 540 and Ink at 600;
- weapon windows for Red’s katana, pickaxe and Ink’s katana;
- deterministic hashes across `PYTHONHASHSEED=1` and `349`;
- static fallback, linter rejection and stale asset detection.

### Visual validation — pass

- 122 key frames (61 per theme) captured with Playwright and reviewed as
  contact sheets across all six acts;
- loop-seam pixels equal at `0`, `30.999` and `31.001` for both themes;
- embedded `<img>` animation changes pixels at 830 px and 390 px;
- reduced-motion player starts paused and shows the V2 act labels;
- no frame with an actor outside the viewBox in the key-frame pass;
- H1 remains readable except during intentional flashes;
- every major contact has anticipation, impact and follow-through;
- Full 372-frame 12 fps exports completed for both themes using Python
  Playwright and Chrome; loop-seam and embedded-image checks passed.
- Generated six act sheets per theme, two storyboards, GIFs, MP4s and the
  release ZIP.

Reproduce the full export with:

```sh
python raid/make_raid_v2.py --out build/raid-v2 --preview --export
```

This requires Playwright with Chromium and either ffmpeg or the
`imageio-ffmpeg` package. Pass `--browser PATH` to use an installed Chrome or
Chromium executable.

### Performance — pass

- approximately 767 KB per animated SVG;
- 890 animation tracks (budget ≤1,250);
- 95 peak changing elements (budget ≤120);
- 88 poses;
- 12 fps key-frame capture completes without missing frames.

---

## 8. File layout

```
raid/
  assemble_v2.py        # assembles V2 from its marked template and act sources
  make_raid_v2.py       # self-contained V2 production generator
  _v2_acts_2_3.py       # editable Acts 2–3
  _v2_act4.py           # editable Act 4
  _v2_act5.py           # editable Act 5
  _v2_act6.py           # editable Act 6 + metadata
  test_raid_v2.py       # V2 regression tests
  README.md             # V2 build and preview instructions
  V2_DESIGN.md          # choreography and implementation notes
  preview.html          # player; V2 act labels are read from metadata
  raid-*.svg            # published V2 light/dark animated/static assets
build/
  raid-v2/              # optional review renders (gitignored)
```

---

## 9. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| New choreography feels less polished | author from the beat sheet; review act-by-act and compare rendered sheets |
| Engine regression | run the V2 geometry, rendering, and bundle tests |
| Broken spatial continuity | `world()` assertions at every hand-off/contact; contact sheets |
| Weapon continuity errors | explicit katana windows; `stuck_katana` reuse; tests |
| Loop seam | restore all effects before 31 s; pixel seam test |
| File bloat | reuse geometry, cap storm count, track count budget |
| Bankai too similar to Domain Expansion | separate effect design: blade spirit + storm + ink field, not a void swallow |
| Chopper/clone/charm feel bolted on | they each change the fight’s advantage: interruption, pincer, reversal |
| CI misses a choreography change | workflow watches the V2 generator and every editable act source |

---

## 10. Definition of done

1. `make_raid_v2.py` builds four SVGs and `validation.json` in the selected
   output directory (`raid/` by default).
2. The V2 test suite passes.
3. `--check` is clean.
4. Loop, embedding, reduced-motion and player controls pass.
5. V1 and V2 contact sheets have been compared.
6. The design document is updated with final timings and any deviations.
7. V2 is the published production animation; V1-only sources and documentation
   are retired, while historical materials remain in `archive/`.

Status: all build, test, stale-asset, visual-review, and full 372-frame export
gates pass. The V2 release ZIP contains the maintained generator, assembler,
editable act sources, tests, player, and design notes.
