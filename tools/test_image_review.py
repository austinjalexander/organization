import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

import image_review as review


class ImageReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.private = self.root / '.local'
        self.private.mkdir()
        self.patcher = patch.object(review, 'PRIVATE', self.private)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.source = self.root / 'image.png'
        Image.new('RGB', (120, 80), 'blue').save(self.source)

    def prepare(self, rows=None, folder='prepared'):
        rows = rows or [{'item_id': 'test-01', 'local_path': str(self.source),
                         'sha256': review.fingerprint(self.source)['sha256']}]
        sources = self.private / (folder + '-sources.json')
        sources.write_text(json.dumps(rows))
        return review.prepare(sources, self.private / folder)

    def note(self, report):
        item = report['items'][0]
        return {'item_id': item['item_id'], 'sha256': item['sha256'],
                'method': 'agent_visual_inspection', 'evidence_tool': 'test fixture',
                'reviewer': 'test fixture', 'reviewed_frames': item['sampled_frames'],
                'category': 'artwork', 'description': 'A solid blue rectangular image.',
                'confidence': 'high', 'uncertainties': []}

    def annotate(self, notes, name='reviewed.json'):
        annotations = self.private / 'notes.json'
        annotations.write_text(json.dumps(notes))
        return review.annotate(self.private / 'prepared/review.json', annotations,
                               self.private / name)

    def test_unreviewed_gate_and_valid_review_preserve_original(self):
        original = self.source.read_bytes()
        report = self.prepare()
        self.assertFalse(review.check(self.private / 'prepared/review.json')['ready_for_proposal'])
        recorded = self.annotate([self.note(report)])
        self.assertEqual(recorded['items'][0]['status'], 'reviewed')
        self.assertTrue(review.check(self.private / 'reviewed.json')['ready_for_proposal'])
        self.assertEqual(self.source.read_bytes(), original)

    def test_source_and_preview_drift_invalidate_review(self):
        report = self.prepare()
        self.annotate([self.note(report)])
        Image.new('RGB', (120, 80), 'red').save(self.source)
        self.assertFalse(review.check(self.private / 'reviewed.json')['ready_for_proposal'])
        with self.assertRaises(ValueError):
            self.annotate([self.note(report)], 'drifted.json')
        Image.new('RGB', (120, 80), 'blue').save(self.source)
        Path(report['items'][0]['previews'][0]['path']).write_bytes(b'changed')
        self.assertFalse(review.check(self.private / 'reviewed.json')['ready_for_proposal'])

    def test_every_image_and_exact_hash_are_required(self):
        report = self.prepare()
        for alteration in ('hash', 'missing', 'filename_guess', 'frames'):
            notes = [self.note(report)]
            if alteration == 'hash':
                notes[0]['sha256'] = '0' * 64
            elif alteration == 'missing':
                notes = []
            elif alteration == 'filename_guess':
                notes[0]['method'] = 'filename_guess'
            else:
                notes[0]['reviewed_frames'] = []
            with self.subTest(alteration=alteration), self.assertRaises(ValueError):
                self.annotate(notes)

    def test_uncertainty_and_unknown_classifications_stay_held(self):
        report = self.prepare()
        for n, changes in enumerate([{'category': 'unknown'}, {'confidence': 'low'},
                                      {'needs_user_context': True}]):
            note = self.note(report)
            note.update(changes)
            recorded = self.annotate([note], f'held-{n}.json')
            self.assertEqual(recorded['items'][0]['status'], 'hold')
            self.assertFalse(review.check(self.private / f'held-{n}.json')['ready_for_proposal'])

    def test_animation_coverage_is_explicit(self):
        gif = self.root / 'motion.gif'
        frames = [Image.new('RGB', (20, 20), color) for color in
                  ['red', 'blue', 'green', 'yellow', 'purple']]
        frames[0].save(gif, save_all=True, append_images=frames[1:], duration=100, loop=0)
        report = self.prepare([{'item_id': 'test-01', 'local_path': str(gif)}])
        item = report['items'][0]
        self.assertEqual(item['sampled_frames'], [0, 2, 4])
        self.assertEqual(item['coverage'], 'sampled_frames')
        self.assertEqual(len(item['previews']), 3)
        note = self.note(report)
        note['reviewed_frames'] = [0]
        with self.assertRaises(ValueError):
            self.annotate([note])

    def test_invalid_sources_are_holds_and_links_not_followed(self):
        empty, corrupt, link = self.root / 'empty.png', self.root / 'bad.png', self.root / 'link.png'
        empty.touch()
        corrupt.write_bytes(b'not an image')
        link.symlink_to(self.source)
        rows = [{'item_id': f'bad-{n}', 'local_path': str(p)}
                for n, p in enumerate([empty, corrupt, link])]
        report = self.prepare(rows)
        self.assertTrue(all(i['status'] == 'hold' for i in report['items']))
        self.assertTrue(all(i['error'] for i in report['items']))

    def test_private_outputs_and_no_overwrites(self):
        self.prepare()
        with self.assertRaises(FileExistsError):
            self.prepare()
        with self.assertRaises(ValueError):
            review.private_path(self.root / 'external.json')
        link = self.private / 'external-link'
        link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            review.private_path(link / 'output.json')

    def test_provider_hash_mismatch_never_becomes_a_review(self):
        report = self.prepare([{'item_id': 'test-01', 'local_path': str(self.source),
                                'provider_content_hash': '0' * 64}])
        self.assertEqual(report['items'][0]['status'], 'hold')
        self.assertIn('identity mismatch', report['items'][0]['error'])


if __name__ == '__main__':
    unittest.main()
