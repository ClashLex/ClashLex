"""Reference adaptation: profile content, choreography continuity and SVG output."""
import importlib.util
import json
import math
import os
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


class ReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.svg = raid.render('light')

    def test_exact_profile_copy_and_personalized_targets(self):
        self.assertEqual(raid.H1_TEXT, "Hi, I'm Ansil.")
        self.assertEqual([line for line in raid.PARAS if line], [
            'B.Tech CSE Undergraduate.', 'Developer. Experimenter. Builder.',
            'I build, break, and rebuild things.',
        ])
        self.assertEqual(''.join(letter.text for letter in raid.NL), 'rebuild')
        self.assertEqual([raid.RD.text, raid.S1.text, raid.S2.text, raid.S3.text],
                         ['things.', 'break,', 'Experimenter.', 'Undergraduate.'])
        text = ''.join(ET.fromstring(self.svg).itertext())
        for original_info in ('Jeremy', 'UWaterloo', 'teddy', 'Ted.', 'Dear', 'Diary'):
            self.assertNotIn(original_info, text)

    def test_climb_handoff_keeps_every_joint_at_the_same_position(self):
        for joint in ('H', 'N', 'P', 'LH', 'RH', 'LF', 'RF'):
            self.assertLess(math.dist(raid.crawl.world(3.86, joint), raid.red.world(3.86, joint)), .00001)
        self.assertEqual(raid.eval_num(raid.crawl.op, 3.86), 0)
        self.assertEqual(raid.eval_num(raid.red.op, 3.86), 1)

    def test_climb_reveals_hands_then_body_then_legs(self):
        stages = ((2.31, {'LA', 'RA'}), (3.1, {'LA', 'RA', 'H', 'torso'}),
                  (3.5, {'LA', 'RA', 'H', 'torso', 'RL'}),
                  (3.8, {'LA', 'RA', 'H', 'torso', 'RL', 'LL'}))
        for time, expected in stages:
            shown = {name for name, track in raid.crawl.lop.items() if raid.eval_num(track, time) == 1}
            self.assertEqual(shown, expected)

    def test_all_seven_kicked_letters_move_and_return(self):
        self.assertEqual(len(raid.NL), 7)
        for letter in raid.NL:
            self.assertTrue(letter.animated)
            self.assertGreater(math.hypot(*raid.eval_num(letter.tr, 6.5)), 1)
            self.assertEqual(raid.eval_num(letter.tr, 30.9), (0, 0))
            self.assertEqual(raid.eval_num(letter.rot, 30.9), 0)

    def test_cut_words_restore_without_leaving_halves_visible(self):
        for word in (raid.S1, raid.S2, raid.S3):
            self.assertEqual(len(word.halves), 2)
            self.assertEqual(raid.eval_num(word.op, 30.9), 1)
            self.assertEqual(raid.eval_num(word.tr, 30.9), (0, 0))
            for half in word.halves:
                self.assertEqual(raid.eval_num(half.op, 30.9), 0)
                self.assertEqual(raid.eval_num(half.tr, 30.9), (0, 0))
                self.assertEqual(raid.eval_num(half.rot, 30.9), 0)

    def test_reference_weapon_geometry_ends_at_authored_tip(self):
        for name in ('sw_idle', 'sw_upcut', 'sw_down', 'sw_stab'):
            pose = raid.POSES[name]
            parts = raid.katana_parts(pose)
            self.assertIn(pose['WT'], parts['blade'])
            self.assertEqual(len(parts['blade']), 9)
            self.assertEqual(len(parts['tsuba']), 8)

    def test_render_timeline_applies_the_reference_lead_trim(self):
        track = raid.Track(0)
        track.hold(.9)
        track.add(1.2, 1, 'out')
        animation = ET.fromstring(raid.animate('opacity', track, str))
        times = [float(t)*raid.T for t in animation.get('keyTimes').split(';')]
        self.assertAlmostEqual(times[1], .65, places=4)
        self.assertAlmostEqual(times[2], .95, places=4)
        self.assertEqual(times[-1], 31.)

    def test_pose_interpolation_and_world_transform_agree(self):
        actor = raid.Char('stand', (10, 20))
        actor.pose(1, 'kick', tween=.4, ease='lin')
        actor.face(1.2, -1)
        actor.sq.set(1.2, (2, .5))
        expected = raid.POSES['kick']['RF']
        self.assertEqual(actor.world(1.4, 'RF'), (10-expected[0]*2, 20+expected[1]*.5))
        midpoint = actor.pose_at(.8)['RF']
        self.assertAlmostEqual(midpoint[0], (raid.POSES['stand']['RF'][0]+expected[0])/2)

    def test_deterministic_across_python_hash_seeds(self):
        code = ('import importlib.util,hashlib,sys; '
                's=importlib.util.spec_from_file_location("raid",sys.argv[1]); '
                'm=importlib.util.module_from_spec(s);s.loader.exec_module(m); '
                'print(hashlib.sha256(m.render("dark").encode()).hexdigest())')
        hashes = []
        for seed in ('1', '349'):
            env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONDONTWRITEBYTECODE='1')
            result = subprocess.run([sys.executable, '-c', code, str(SCRIPT)], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            hashes.append(result.stdout.strip())
        self.assertEqual(*hashes)

    def test_svg_contract_metadata_and_static_fallback(self):
        self.assertEqual(self.svg, raid.render('light'))
        report = raid.lint_svg(self.svg)
        self.assertEqual(report['duration'], 31)
        self.assertEqual(report['poses'], 88)
        root = ET.fromstring(self.svg)
        metadata = json.loads(root.find('{http://www.w3.org/2000/svg}metadata').text)
        self.assertEqual(len(metadata['acts']), 6)
        self.assertEqual(metadata['duration'], 31)
        static = ET.fromstring(raid.static_svg(self.svg))
        self.assertFalse(any(node.tag.endswith(('}animate', '}animateTransform')) for node in static.iter()))

    def test_linter_rejects_broken_references_and_executable_content(self):
        for body, message in (('<use href="#absent"/>', 'Missing SVG reference'),
                              ('<script/>', 'Unsupported SVG element'),
                              ('<use href="https://example.com/a.svg"/>', 'Executable or external')):
            with self.assertRaisesRegex(ValueError, message):
                raid.lint_svg('<svg xmlns="http://www.w3.org/2000/svg">'+body+'</svg>')

    def test_new_output_directory_and_stale_asset_detection(self):
        with tempfile.TemporaryDirectory(prefix='raid-reference-') as temporary:
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
