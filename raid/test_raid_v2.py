"""Margin Duel: profile content, V2 choreography continuity and SVG output."""
import importlib.util
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET

SCRIPT = Path(__file__).with_name('make_raid_v2.py')
spec = importlib.util.spec_from_file_location('raid_v2', SCRIPT)
raid = importlib.util.module_from_spec(spec)
spec.loader.exec_module(raid)


class MarginDuelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.svg = raid.render('light')
        cls.root = ET.fromstring(cls.svg)
        cls.metadata = json.loads(cls.root.find('{http://www.w3.org/2000/svg}metadata').text)

    def test_exact_profile_copy_and_personalized_targets(self):
        self.assertEqual(raid.H1_TEXT, "Hi, I'm Ansil.")
        self.assertEqual([line for line in raid.PARAS if line], [
            'B.Tech CSE Undergraduate.', 'Developer. Experimenter. Builder.',
            'I build, break, and rebuild things.',
        ])
        self.assertEqual(''.join(letter.text for letter in raid.NL), 'rebuild')
        self.assertEqual([raid.RD.text, raid.S1.text, raid.S2.text, raid.S3.text],
                         ['things.', 'break,', 'Experimenter.', 'Undergraduate.'])
        text = ''.join(self.root.itertext())
        for original_info in ('Jeremy', 'UWaterloo', 'teddy', 'Ted.', 'Dear', 'Diary'):
            self.assertNotIn(original_info, text)

    def test_six_act_player_contract_and_margin_duel_metadata(self):
        self.assertEqual(self.metadata['duration'], 31)
        self.assertEqual([name for name, _, _ in self.metadata['acts']], [
            '01-break-in', '02-the-climb', '03-word-ladder',
            '04-chopper-clones-charm', '05-bankai', '06-reset',
        ])
        self.assertEqual(self.metadata['acts'][0][1], 0)
        self.assertEqual(self.metadata['acts'][-1][2], 31)
        tags = {beat[2] for beat in self.metadata['beats']}
        for required in ('Chopper', 'clones', 'heart', 'reversal', 'Bankai',
                         'storm', 'wall', 'pickaxe', 'collapse', 'salute', 'cameo'):
            self.assertIn(required, tags)
        self.assertGreaterEqual(len(self.metadata['beats']), 30)

    def test_bankai_replaces_domain_expansion(self):
        self.assertIn('Bankai: Margin Storm', raid.ALT)
        self.assertIn('Bankai.', self.svg)
        self.assertIn('Margin Storm.', self.svg)
        self.assertNotIn('Domain Expansion', self.svg)
        self.assertNotIn('domain', self.svg.lower())
        self.assertNotIn('void_svg', self.svg)

    def test_bankai_effects_are_invisible_at_both_loop_seams(self):
        for name in ('STORM_OP', 'BANKAI_R', 'BANKAI_RING_OP', 'BANKAI_SHOCK_OP',
                     'BANKAI_GHOST_OP', 'BANKAI_BLADE_OP', 'BANKAI_CUT_OP',
                     'BANKAI_INK_WIN', 'BUBBLE_OP', 'GLOW', 'WALL_OP',
                     'DARK_HEART_OP', 'RULE_GAP_OP'):
            track = getattr(raid, name)
            self.assertEqual(raid.eval_num(track, 0), 0, f'{name} leaks into the opening')
            self.assertEqual(raid.eval_num(track, 31), 0, f'{name} leaks into the loop point')
        for blade in raid.STORM_BLADES:
            self.assertEqual(raid.eval_num(blade[3], 0), 0)
            self.assertEqual(raid.eval_num(blade[3], 31), 0)

    def test_bankai_field_geometry_and_retraction_into_the_sword(self):
        self.assertEqual(raid.BANKAI_RADIUS, 740)
        self.assertEqual(raid.eval_num(raid.BANKAI_R, 18.6), 740)
        self.assertGreater(raid.eval_num(raid.BANKAI_R, 24.4), 0)
        self.assertEqual(raid.eval_num(raid.BANKAI_R, raid.T_COLLAPSE1), 0)
        sx, sy = raid.BANKAI_TR_TARGET
        self.assertEqual(raid.eval_num(raid.BANKAI_TR, raid.T_COLLAPSE1),
                         (sx - raid.BANKAI_CX, sy - raid.BANKAI_CY))
        # The target is the sheathed sword's rest position, within reach of its tip at collapse.
        self.assertLess(math.dist(raid.BANKAI_TR_TARGET, raid.ink.world(raid.T_COLLAPSE1, 'WT')), 60)
        self.assertGreater(raid.eval_num(raid.BANKAI_BLADE_OP, 19.2), .5)
        self.assertLess(raid.eval_num(raid.BANKAI_BLADE_OP, 24.4), .05)

    def test_margin_storm_has_twelve_orbiters_at_distinct_radii(self):
        self.assertEqual(len(raid.STORM_BLADES), 12)
        radii = [blade[1] for blade in raid.STORM_BLADES]
        self.assertEqual(radii, [150.0 + 10.0 * i for i in range(12)])
        self.assertEqual((raid.BANKAI_CX, raid.BANKAI_CY), (600.0, 160.0))
        for blade in raid.STORM_BLADES:
            self.assertGreater(raid.eval_num(blade[3], 20.0), .5)

    def test_chopper_stays_attached_through_the_boot_shake(self):
        worst = 0.0
        for i in range(200):
            t = 12.42 + i * (12.85 - 12.42) / 199
            x, y = raid.eval_num(raid.chopper.pos, t)
            dx, dy = raid.chopper.grip_offset(t)
            worst = max(worst, math.dist((x + dx, y + dy), raid.red.world(t, 'RF')))
        self.assertLess(worst, .2, f'Chopper loses the boot by {worst:.2f}px')

    def test_chopper_cameo_enters_interrupts_and_waves(self):
        for t, visible in ((0, 0), (11.94, 0), (11.96, 1), (12.6, 1), (13.5, 1),
                           (16.8, 0), (29.05, 1), (30.3, 0), (31, 0)):
            self.assertEqual(raid.eval_num(raid.chopper.op, t), visible, f'Chopper opacity at {t}')
        self.assertIsNotNone(self.root.find('.//*[@id="chopper"]'))
        self.assertTrue(any('Chopper' in beat[1] for beat in self.metadata['beats']))
        self.assertNotIn('A bear', self.svg)

    def test_vertical_clone_pincer_uses_three_levels(self):
        for clone, x, y in ((raid.c1, 300, 84), (raid.c2, 380, 124), (raid.c3, 460, 164)):
            self.assertEqual(raid.eval_num(clone.pos, 13.52), (x, y))
            self.assertEqual(raid.eval_num(clone.op, 13.52), 1)
            self.assertEqual(raid.eval_num(clone.op, 14.06), 0)
            self.assertEqual(raid.eval_num(clone.op, 31), 0)
        ys = [raid.eval_num(clone.pos, 13.52)[1] for clone in (raid.c1, raid.c2, raid.c3)]
        self.assertEqual(len(set(ys)), 3)

    def test_charm_flight_turns_dark_and_triggers_the_bankai(self):
        self.assertEqual(raid.eval_num(raid.HEART['op'], 14.9), 0)
        self.assertEqual(raid.eval_num(raid.HEART['op'], 15.0), 1)
        self.assertEqual(raid.eval_num(raid.HEART['op'], 15.45), 0)
        self.assertEqual(raid.eval_num(raid.HEART['op'], 31), 0)
        self.assertEqual(raid.eval_num(raid.HEART['tr'], 15.36), (700.0, 190.0))
        self.assertEqual(raid.eval_num(raid.DARK_HEART_OP, 16.7), 1)
        self.assertEqual(raid.eval_num(raid.DARK_HEART_OP, 17.1), 0)
        self.assertEqual(raid.eval_num(raid.BUBBLE_OP, 17.6), 1)
        self.assertEqual(raid.eval_num(raid.BUBBLE_OP, 17.95), 0)

    def test_rule_gap_heals_and_cut_words_restore(self):
        self.assertEqual(raid.eval_num(raid.RULE_GAP_OP, 7.8), 0)
        self.assertEqual(raid.eval_num(raid.RULE_GAP_OP, 8.0), 1)
        self.assertEqual(raid.eval_num(raid.RULE_GAP_OP, 27.4), 0)
        for word in (raid.S1, raid.S2, raid.S3):
            self.assertEqual(len(word.halves), 2)
            self.assertEqual(raid.eval_num(word.op, 30.9), 1)
            self.assertEqual(raid.eval_num(word.tr, 30.9), (0, 0))
            for half in word.halves:
                self.assertEqual(raid.eval_num(half.op, 30.9), 0)
                self.assertEqual(raid.eval_num(half.tr, 30.9), (0, 0))
                self.assertEqual(raid.eval_num(half.rot, 30.9), 0)

    def test_kicked_letters_and_chopper_leave_a_clean_loop_point(self):
        self.assertEqual(len(raid.NL), 7)
        for letter in raid.NL:
            self.assertTrue(letter.animated)
            self.assertGreater(math.hypot(*raid.eval_num(letter.tr, 6.5)), 1)
            self.assertEqual(raid.eval_num(letter.tr, 30.9), (0, 0))
            self.assertEqual(raid.eval_num(letter.rot, 30.9), 0)
        self.assertEqual(raid.eval_num(raid.red.op, 31), 0)
        self.assertEqual(raid.eval_num(raid.ink.op, 31), 0)
        self.assertEqual(raid.eval_num(raid.HOLE_SCALE, 31), 0)
        self.assertEqual(raid.eval_num(raid.chopper.op, 31), 0)

    def test_reset_centers_the_duel_before_the_salute(self):
        self.assertEqual(raid.eval_num(raid.red.pos, 27.16), (540.0, float(raid.FLOOR)))
        self.assertEqual(raid.eval_num(raid.ink.pos, 27.30), (600.0, float(raid.FLOOR)))
        self.assertEqual(raid.eval_num(raid.red.pos, 28.28)[0], 540.0)
        self.assertEqual(raid.eval_num(raid.ink.pos, 28.28)[0], 600.0)

    def test_weapons_are_armed_for_the_right_windows(self):
        # Red carries the katana for the duel and the Bankai, then the pickaxe for the dig-out.
        for t in (8.0, 20.0):
            self.assertEqual(raid.eval_num(raid.red.wop, t), 1)
        for t in (10.0, 25.0):
            self.assertEqual(raid.eval_num(raid.red.wop, t), 0)
        self.assertEqual(raid.eval_num(raid.red.pop, 24.7), 1)
        self.assertEqual(raid.eval_num(raid.red.pop, 25.6), 0)
        # Ink is armed in V2; V1 only gave the katana to Red.
        self.assertEqual(raid.eval_num(raid.ink.wop, 19.5), 1)
        self.assertEqual(raid.eval_num(raid.ink.wop, 26.5), 0)
        self.assertEqual(raid.eval_num(raid.ink.wop, 0), 0)
        self.assertEqual(raid.eval_num(raid.ink.wop, 31), 0)

    def test_render_timeline_applies_the_reference_lead_trim(self):
        track = raid.Track(0)
        track.hold(.9)
        track.add(1.2, 1, 'out')
        animation = ET.fromstring(raid.animate('opacity', track, str))
        times = [float(t) * raid.T for t in animation.get('keyTimes').split(';')]
        self.assertAlmostEqual(times[1], .65, places=4)
        self.assertAlmostEqual(times[2], .95, places=4)
        self.assertEqual(times[-1], 31.)

    def test_pose_interpolation_and_world_transform_agree(self):
        actor = raid.Char('stand', (10, 20))
        actor.pose(1, 'kick', tween=.4, ease='lin')
        actor.face(1.2, -1)
        actor.sq.set(1.2, (2, .5))
        expected = raid.POSES['kick']['RF']
        self.assertEqual(actor.world(1.4, 'RF'), (10 - expected[0] * 2, 20 + expected[1] * .5))
        midpoint = actor.pose_at(.8)['RF']
        self.assertAlmostEqual(midpoint[0], (raid.POSES['stand']['RF'][0] + expected[0]) / 2)

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
        self.assertEqual(len(self.metadata['acts']), 6)
        self.assertEqual(self.metadata['duration'], 31)
        static = ET.fromstring(raid.static_svg(self.svg))
        self.assertFalse(any(node.tag.endswith(('}animate', '}animateTransform')) for node in static.iter()))

    def test_linter_rejects_broken_references_and_executable_content(self):
        for body, message in (('<use href="#absent"/>', 'Missing SVG reference'),
                              ('<script/>', 'Unsupported SVG element'),
                              ('<use href="https://example.com/a.svg"/>', 'Executable or external')):
            with self.assertRaisesRegex(ValueError, message):
                raid.lint_svg('<svg xmlns="http://www.w3.org/2000/svg">' + body + '</svg>')

    def test_new_output_directory_and_stale_asset_detection(self):
        with tempfile.TemporaryDirectory(prefix='raid-v2-') as temporary:
            out = Path(temporary) / 'new directory #2' / 'nested'
            command = [sys.executable, str(SCRIPT), '--out', str(out)]
            for suffix in ([], ['--check']):
                result = subprocess.run(command + suffix, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(list(out.glob('*.svg'))), 4)
            (out / 'validation.json').write_text('{}', encoding='utf-8')
            stale = subprocess.run(command + ['--check'], capture_output=True, text=True)
            self.assertNotEqual(stale.returncode, 0)
            self.assertIn('Stale generated asset', stale.stderr)

    def test_assembler_is_idempotent_without_v1_sources(self):
        self.assertFalse(SCRIPT.with_name('make_raid.py').exists())
        digests = []
        for _ in range(2):
            result = subprocess.run(
                [sys.executable, str(SCRIPT.with_name('assemble_v2.py'))],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            digests.append(hashlib.sha256(SCRIPT.read_bytes()).hexdigest())
        self.assertEqual(digests[0], digests[1])

    def test_release_bundle_contains_v2_sources_and_docs(self):
        with tempfile.TemporaryDirectory(prefix='raid-v2-bundle-') as temporary:
            out = Path(temporary)
            files = {}
            for theme in raid.PALETTES:
                svg = raid.render(theme)
                path = out / f'raid-{theme}.svg'
                path.write_text(svg, encoding='utf-8')
                files[theme] = path
                (out / f'raid-{theme}-static.svg').write_text(
                    raid.static_svg(svg), encoding='utf-8')
            (out / 'validation.json').write_text('{}', encoding='utf-8')

            raid.bundle(out, files)

            with zipfile.ZipFile(out / 'ansil-raid.zip') as archive:
                names = set(archive.namelist())
            required = {
                'raid/make_raid_v2.py', 'raid/assemble_v2.py',
                'raid/_v2_acts_2_3.py', 'raid/_v2_act4.py',
                'raid/_v2_act5.py', 'raid/_v2_act6.py',
                'raid/test_raid_v2.py', 'raid/V2_DESIGN.md',
                'raid/preview.html',
            }
            self.assertTrue(required.issubset(names), required - names)
            self.assertNotIn('raid/make_raid.py', names)
            self.assertNotIn('raid/test_raid.py', names)
            self.assertNotIn('raid/README.md', names)
            self.assertNotIn('README.md', names)


if __name__ == '__main__':
    unittest.main()
