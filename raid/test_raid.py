"""Regression checks for timing, geometric contacts and the artifact contract."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

SCRIPT = Path(__file__).with_name('make_raid.py')
spec = importlib.util.spec_from_file_location('raid', SCRIPT)
raid = importlib.util.module_from_spec(spec)
spec.loader.exec_module(raid)


class EngineTests(unittest.TestCase):
    def test_conflicting_keys_fail_without_retiming(self):
        track = raid.Track(0).to(2, 10)
        before = list(track.k)
        for t in (1, 2, raid.T + 1):
            with self.assertRaises(ValueError):
                track.to(t, 20)
            self.assertEqual(track.k, before)

    def test_spline_endpoint_and_hold(self):
        track = raid.Track((0., 0.)).hold(1).to(2, (20., 30.), 'smooth')
        self.assertEqual(track.at(.8), (0., 0.))
        self.assertEqual(track.at(2.8), (20., 30.))
        self.assertAlmostEqual(track.at(1.5)[0], 10, places=4)

    def test_blade_contact_and_miss(self):
        self.assertEqual(raid.segment_cross((-5, 3), (5, 3), (0, 0, 10, 10)), (0, 3))
        with self.assertRaises(ValueError):
            raid.segment_cross((-5, 12), (15, 12), (0, 0, 10, 10))
        clipped = raid.half_plane([(0, 0), (10, 0), (10, 10), (0, 10)], 0, 1, 4)
        self.assertTrue(all(y <= 4 for _, y in clipped))
        self.assertIn((10., 4.), clipped)

    def test_scene_contract_and_static_fallback(self):
        scene = raid.Scene('light')
        svg = scene.svg()
        self.assertEqual(svg, raid.Scene('light').svg())
        report = raid.lint_svg(svg)
        self.assertLessEqual(report['bytes'], 750_000)
        self.assertLessEqual(report['peak_changing_elements'], 60)
        self.assertGreaterEqual(report['poses'], 60)
        self.assertEqual(len([c for c in scene.contacts if c[0] == 'blade']), 4)
        root = ET.fromstring(raid.static_svg(svg))
        self.assertFalse(any(el.tag.endswith(('}animate', '}animateTransform')) for el in root.iter()))

    def test_linter_rejects_broken_references_and_executable_content(self):
        with self.assertRaisesRegex(ValueError, 'Missing SVG reference'):
            raid.lint_svg('<svg xmlns="http://www.w3.org/2000/svg"><use href="#absent"/></svg>')
        with self.assertRaisesRegex(ValueError, 'Unsupported SVG element'):
            raid.lint_svg('<svg xmlns="http://www.w3.org/2000/svg"><script/></svg>')

    def test_concurrency_counts_visible_instances(self):
        morph = raid.anim('d', raid.Track('M0,0L1,1').to(1, 'M0,0L2,2'), str)
        svg = ('<svg xmlns="http://www.w3.org/2000/svg"><defs><path id="body" d="M0,0L1,1">'
               + morph + '</path></defs><use href="#body"/><use href="#body"/>'
               '<g opacity="0"><use href="#body"/></g></svg>')
        self.assertEqual(raid.lint_svg(svg)['peak_changing_elements'], 2)

    def test_new_output_directory_and_stale_asset_detection(self):
        with tempfile.TemporaryDirectory(prefix='raid-output-') as temp:
            out = Path(temp) / 'new directory #1' / 'nested'
            command = [sys.executable, str(SCRIPT), '--out', str(out)]
            built = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            self.assertEqual(len(list(out.glob('*.svg'))), 4)
            current = subprocess.run(command + ['--check'], capture_output=True, text=True)
            self.assertEqual(current.returncode, 0, current.stderr)
            (out / 'raid-light.svg').write_text('<svg/>', encoding='utf-8')
            stale = subprocess.run(command + ['--check'], capture_output=True, text=True)
            self.assertNotEqual(stale.returncode, 0)
            self.assertIn('Stale generated asset', stale.stderr)


if __name__ == '__main__':
    unittest.main()
