"""Physical contacts, joint invariants, serialization and the release contract."""
import importlib.util
import math
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
    @classmethod
    def setUpClass(cls):
        cls.film = raid.Film('light')
        cls.svg = cls.film.svg()

    def test_conflicting_timestamps_do_not_retime_or_mutate(self):
        track = raid.Curve(0.).key(2., 10.)
        before = list(track.keys)
        for t in (1., 2., raid.T+1):
            with self.assertRaises(ValueError):
                track.key(t, 20.)
            self.assertEqual(track.keys, before)
        self.assertEqual(track.go(3, 4, 30.).at(2.5), 10.)
        self.assertAlmostEqual(track.at(3.5), 20., places=5)

    def test_two_bone_solver_preserves_lengths_and_limits_reach(self):
        for target in ((0, 0), (3, 11), (100, 0), (-19, 7)):
            for side in (-1, -.2, 1):
                middle, end = raid.two_bone((0, 0), target, 12, 13, side)
                self.assertAlmostEqual(math.dist((0, 0), middle), 12, places=6)
                self.assertAlmostEqual(math.dist(middle, end), 13, places=6)
                self.assertLessEqual(math.hypot(*end), 25)

    def test_interpolated_performance_keeps_every_limb_length(self):
        for actor in (self.film.pirate, self.film.navy):
            for i in range(int(raid.T*12)):
                j = actor.local(i/12)
                for limb in ('left', 'right', 'lf', 'rf'):
                    origin, length = ('shoulder', 12) if limb in ('left', 'right') else ('hip', 13)
                    self.assertAlmostEqual(math.dist(j[origin], j[limb+'_mid']), length, places=5)
                    self.assertAlmostEqual(math.dist(j[limb+'_mid'], j[limb]), length, places=5)

    def test_geometry_contacts_use_the_performed_joints(self):
        actors = {'pirate': self.film.pirate, 'navy': self.film.navy}
        for contact in self.film.contacts:
            t = contact['time']
            if contact['kind'] == 'foot':
                point = actors[contact['actor']].world(contact['joint'], t)
                self.assertLess(math.dist(point, contact['point']), .001)
                col = int((point[0]-raid.X0)//raid.CW)
                row = round((point[1]-raid.Y0)/raid.CH)
                self.assertEqual(raid.art_rows()[row][col], '█')
            elif contact['kind'] == 'blade':
                self.assertEqual(contact['hilt'], self.film.navy.world('right', t))
                self.assertEqual(contact['tip'], self.film.navy.world('tip', t))
                a, b, p = contact['hilt'], contact['tip'], contact['point']
                self.assertAlmostEqual(math.dist(a, p)+math.dist(p, b), math.dist(a, b), places=5)
        self.assertEqual(len([c for c in self.film.contacts if c['kind'] == 'blade']), 4)
        self.assertLess(math.dist(self.film.pirate.world('rf', 1.4), self.film.letters['A'].surface(0)), .001)
        retrieval = next(c for c in self.film.contacts if c['kind'] == 'retrieve')
        self.assertLess(math.dist(retrieval['point'], retrieval['target']), .001)

    def test_tugging_hand_stays_on_lodged_sword(self):
        for i in range(19):
            t = 15.72+i*(17.27-15.72)/18
            self.assertLess(math.dist(self.film.navy.world('right', t), self.film.lodged[0]), .001)

    def test_rope_swings_keep_the_hand_on_a_circle(self):
        mast = self.film.letters['I']
        swings = [(.92, 1.4, (77, -55), 'left'),
                  (8.76, 9.25, (mast.x+mast.width/2, raid.Y0-50), 'right')]
        for start, end, anchor, hand in swings:
            lengths = [math.dist(self.film.pirate.world(hand, start+(end-start)*i/100), anchor)
                       for i in range(101)]
            self.assertLess(max(lengths)-min(lengths), .75)

    def test_shards_collide_and_retrace_the_same_samples(self):
        for fragment in self.film.physics:
            for dt, position, angle in fragment['samples']:
                for vertex in fragment['polygon']:
                    rotated = raid.add(fragment['center'], raid.rotate(raid.sub(vertex, fragment['center']), angle))
                    self.assertLessEqual(rotated[1]+position[1], raid.FLOOR+.00001)
                forward = fragment['motion'].at(fragment['start']+dt)
                reverse = fragment['motion'].at(fragment['restore']-dt)
                self.assertLess(math.dist(forward, reverse), .0001)
                self.assertAlmostEqual(fragment['rotation'].at(fragment['start']+dt)[0],
                                       fragment['rotation'].at(fragment['restore']-dt)[0], places=4)

    def test_sword_miss_and_polygon_half_plane(self):
        self.assertEqual(raid.segment_box((-5, 3), (5, 3), (0, 0, 10, 10)), (0, 3))
        self.assertIsNone(raid.segment_box((-5, 12), (15, 12), (0, 0, 10, 10)))
        clipped = raid.clip_polygon([(0, 0), (10, 0), (10, 10), (0, 10)], (0, 1), 4)
        self.assertTrue(all(y <= 4 for _, y in clipped))
        self.assertIn((10, 4), clipped)

    def test_build_is_repeatable_and_meets_svg_contract(self):
        self.assertEqual(self.svg, self.film.svg())
        self.assertEqual(self.svg, raid.Film('light').svg())
        report = raid.lint_svg(self.svg)
        self.assertLessEqual(report['bytes'], 750_000)
        self.assertLessEqual(report['peak_changing_elements'], 60)
        self.assertGreaterEqual(len(self.film.pirate.used | self.film.navy.used), 60)
        self.assertTrue(20 <= len(raid.BEATS) <= 24)
        static = ET.fromstring(raid.static_svg(self.svg))
        self.assertFalse(any(n.tag.endswith(('}animate', '}animateTransform')) for n in static.iter()))

    def test_linter_rejects_missing_references_and_executable_content(self):
        for body, message in (('<use href="#absent"/>', 'Missing SVG reference'),
                              ('<script/>', 'Unsupported SVG element'),
                              ('<use href="https://example.com/a.svg"/>', 'Executable or external')):
            with self.assertRaisesRegex(ValueError, message):
                raid.lint_svg('<svg xmlns="http://www.w3.org/2000/svg">'+body+'</svg>')

    def test_concurrency_counts_visible_uses_of_shared_morphs(self):
        morph = raid.animation('d', raid.Curve('M0,0L1,1').key(1, 'M0,0L2,2'), str)
        svg = ('<svg xmlns="http://www.w3.org/2000/svg"><defs><path id="body" d="M0,0L1,1">'+morph+
               '</path></defs><use href="#body"/><use href="#body"/><g opacity="0"><use href="#body"/></g></svg>')
        self.assertEqual(raid.lint_svg(svg)['peak_changing_elements'], 2)

    def test_custom_output_and_stale_asset_detection(self):
        with tempfile.TemporaryDirectory(prefix='raid-output-') as temporary:
            out = Path(temporary)/'new directory #1'/'nested'
            command = [sys.executable, str(SCRIPT), '--out', str(out)]
            for suffix in ([], ['--check']):
                result = subprocess.run(command+suffix, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(list(out.glob('*.svg'))), 4)
            (out/'validation.json').write_text('{}', encoding='utf-8')
            stale = subprocess.run(command+['--check'], capture_output=True, text=True)
            self.assertNotEqual(stale.returncode, 0)
            self.assertIn('Stale generated asset', stale.stderr)


if __name__ == '__main__':
    unittest.main()
