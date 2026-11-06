# Upgrade review — 6 November 2026

The reference arrived during development as `../inspiration.py`. It was reviewed
in full as an animation reference and left unchanged. The final story, props,
character accents, geometry engine and exports belong to the ANSIL version.

## Ten reference techniques and their application

| Reference location | Technique | ANSIL application |
| --- | --- | --- |
| `inspiration.py:152` | Evaluate browser easing in world space | Hand-to-tip contacts use the same splines as rendering |
| `inspiration.py:234` | Specific acting poses | 68 named poses; gaze, whistle, knot, balance, flint and surrender |
| `inspiration.py:588` | Landing compression and recovery | Squash, overshoot and settle on the A/L and below deck |
| `inspiration.py:600` | Brief impact holds | Officer freezes at each S cut and the I cut |
| `inspiration.py:617` | World-space joint lookup | Dagger release, blade contacts and flint sparks |
| `inspiration.py:637` | Knockout outline over busy artwork | Two body uses share one animated definition, with a paper under-stroke |
| `inspiration.py:737` | Damage follows the blade line | S pieces are clipped with the actual hand-to-tip half-planes |
| `inspiration.py:926` | Thin rings and glints | Open ink forks, rings and small contact glints; no full-frame flashes |
| `inspiration.py:1332` | Foreground occlusion makes a hole physical | The page-minus-hole deck hides legs during the fall and return |
| `inspiration.py:2453` | Restoration belongs in the story | Fragment motion reverses visibly, A to L, before the exit |

## Ten weaknesses addressed in the previous raid

1. Generic logo platform: A, N, S, I and L now supply different terrain or props.
2. Repeated cannon payoff: replaced by a causal chase, mast crash, fuse and return.
3. Flat set: a persistent room below deck is revealed by the camera.
4. Limited acting: gaze, double-take, knot, push, balance, tug and surrender poses.
5. Static secondary elements: hat/coat followers, flag motion, ropes and lantern.
6. Detached impact coordinates: surface cells and blade intersections feed contacts.
7. Filled impact flashes: replaced by thin ink marks and small camera punches.
8. Tide-wipe reset: replaced by the exact reverse fragment trajectories.
9. Repeated glyph markup: shared glyphs and body definitions with local `use` references.
10. Unchecked output: strict timing, geometry/CLI tests, size/concurrency lint,
    deterministic rebuild checks and rendered seam comparisons.

## Act review checks and fixes

Each act has a full 12 fps contact sheet in both palettes. The compact storyboard
is an overview; the full sheets include the short contacts between beat markers.

### Arrival

- Reduced the long A-to-L jump height after the first render left the frame.
- Enlarged the notice around its pinned point to improve readability.
- Added a paper under-stroke so figures remain legible against solid glyphs.
- Made figures turn toward their direction of travel.
- Checked the knot, delayed flag movement and returning empty rope independently.

### Chase

- Replaced approximate shelf boundaries with the actual blade half-planes.
- Added a deliberate turn before cuts after automatic facing exposed a missed contact.
- Added short impact holds to distinguish contact from travel.
- Checked that separated S pieces remain displaced until the blast.
- Checked flag-over-head staging, the I pivot, its floor contact and crack timing.

### Below deck

- Moved the pirate's initial landing clear of the right-hand barrel.
- Added vertical ink forks after the first explosions read as ground dust alone.
- Checked room framing during the camera descent at desktop and mobile widths.
- Checked the sword remains a separate stuck prop through the pulling poses.
- Checked the dagger callback, travelling fuse spark and three sequential punches.

### Return

- Changed fragment collision to use rotated vertices after pieces sank into the deck.
- Checked reverse playback uses the fall's exact positions and angles.
- Checked the officer's disappearance into L precedes the surrender-hand payoff.
- Checked the pirate's departure and hole closure finish before the quiet tail.
- Compared rendered pixels across the end and repeated start of the loop.

## Automated evidence

- Both SVGs: **231,538 bytes**, below the **750,000-byte** budget.
- **50** simultaneously changing elements at peak, below **60**; animated `use`
  instances count separately and fully transparent ancestor groups are excluded.
- **68** poses, **24** beats, **34 seconds**, **22** recorded geometry contacts.
- Seven regression tests cover strict timing, easing, blade hit/miss, clipping,
  deterministic SVGs, static fallbacks, forbidden content, new output folders and
  stale-asset detection and visible animated-instance counting.
- Browser output: **408 frames per theme at 12 fps**, four act sheets and one
  storyboard per theme, GIF/MP4 exports and a release zip.
- Render checks compare 0, 33.999 and 34.001 seconds and exercise image embedding
  at 830px and 390px. Results are in `preview/render-report.json`.
- Preview controls were exercised for play/pause, seeking, act navigation,
  playback speed, theme continuity, reduced motion and mobile overflow. Results
  are in `preview/controls-report.json`.

Testing used local Chrome on Windows. GitHub's live image proxy and other browser
engines were not exercised. The source-only CI runs tests and lint; pixel checks
run through the optional browser preview command.
