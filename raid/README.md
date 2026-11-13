# README animation

The profile README uses the V2 animated SVGs in this directory. The generator,
editable act sources, tests, and design notes are all for V2; the older V1
generator has been removed.

## Build and validate

Python 3.12 or later, Pillow, and Liberation Sans (Linux) or Arial (Windows/macOS)
are required to build. Use the same font installation when comparing output.

```sh
python -m pip install Pillow
python raid/assemble_v2.py
python -m unittest discover -s raid -p "test_*.py"
python raid/make_raid_v2.py
python raid/make_raid_v2.py --check
```

The build refreshes the animated and static light/dark SVGs plus
`validation.json`. The GitHub Actions workflow runs these steps for V2 source
changes.

## Preview

```sh
python -m http.server 8000
```

Open `http://localhost:8000/raid/preview.html`. For rendered act sheets, GIFs,
and MP4s, install Playwright with Chromium and ffmpeg (or `imageio-ffmpeg`),
then run:

```sh
python raid/make_raid_v2.py --preview --export
```

Generated frames and preview exports are ignored by Git.

See [V2_DESIGN.md](./V2_DESIGN.md) for the choreography, layout, validation
results, and source organization.
