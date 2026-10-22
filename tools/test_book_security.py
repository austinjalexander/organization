import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import book_security as security


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.private = self.root / '.local'
        self.db = self.private / 'book-security/clamav-db'
        self.db.mkdir(parents=True)
        date = security.datetime.now(security.timezone.utc).strftime('%d %b %Y %H-%M %z')
        (self.db / 'daily.cld').write_text(f'ClamAV-VDB:{date}:123:100:90:X:X:fixture:1')
        self.file = self.root / 'book.pdf'
        self.file.write_bytes(b'%PDF-1.7\nfixture\n%%EOF')
        self.addCleanup(patch.stopall)
        patch.object(security, 'PRIVATE', self.private).start()
        self.commands = []

    def runner(self, args, **kwargs):
        self.commands.append(args)
        if '--version' in args:
            return subprocess.CompletedProcess(args, 0, 'ClamAV fixture/123\n', '')
        return subprocess.CompletedProcess(args, 0, f'{self.file}: OK\nScanned files: 1\n', '')

    def scan(self, runner=None):
        with patch.object(security.subprocess, 'run', side_effect=runner or self.runner):
            return security.ensure_scan(self.file, scanner='/trusted/scanner')

    def test_hash_database_cache_and_non_destructive_command(self):
        first = self.scan()
        self.assertEqual(first['status'], 'no_threats_detected')
        self.assertTrue(first['file_unchanged'])
        self.assertTrue(self.scan()['reused'])
        args = next(a for a in self.commands if '--version' not in a)
        self.assertIn('--alert-exceeds-max=yes', args)
        self.assertIn('--alert-encrypted=yes', args)
        self.assertFalse(any(a.startswith(('--move', '--copy', '--remove')) for a in args))
        self.file.write_bytes(b'changed book bytes')
        self.assertFalse(self.scan()['reused'])
        with (self.db / 'daily.cld').open('a') as stream:
            stream.write('updated database')
        self.assertFalse(self.scan()['reused'])

    def test_detection_errors_skips_and_encryption_never_pass(self):
        cases = [(1, f'{self.file}: Test.Signature FOUND\n', '', 'detected'),
                 (2, '', 'ERROR: unreadable', 'error'),
                 (0, f'{self.file}: OK\nScanned files: 0\n', '', 'incomplete'),
                 (0, f'{self.file}: OK\nScanned files: 1\n', 'WARNING: skipped data', 'incomplete'),
                 (1, f'{self.file}: Heuristics.Limits.Exceeded.MaxScanSize FOUND\n', '', 'incomplete'),
                 (1, f'{self.file}: Heuristics.Encrypted.PDF FOUND\n', '', 'incomplete')]
        for code, out, err, expected in cases:
            with self.subTest(expected=expected, out=out):
                self.assertEqual(security.classify(code, out, err, str(self.file))[0], expected)

    def test_drift_and_timeout_are_recorded_and_original_preserved(self):
        def drift(args, **kwargs):
            result = self.runner(args, **kwargs)
            if '--version' not in args:
                self.file.write_bytes(b'changed while scanning')
            return result
        self.assertEqual(self.scan(drift)['status'], 'incomplete')
        def timeout(args, **kwargs):
            if '--version' in args:
                return self.runner(args, **kwargs)
            raise subprocess.TimeoutExpired(args, 1)
        result = self.scan(timeout)
        self.assertEqual(result['status'], 'incomplete')
        self.assertTrue(Path(result['report']).exists())
        self.assertTrue(self.file.exists())

    def test_stale_definitions_cannot_reuse_success(self):
        self.scan()
        with patch.object(security, 'database_current', return_value=False):
            result = self.scan()
        self.assertFalse(result['reused'])
        self.assertEqual(result['status'], 'incomplete')

    def test_symlinks_empty_files_and_external_evidence_refused(self):
        link = self.root / 'alias.pdf'
        link.symlink_to(self.file)
        for path in (link, self.root):
            with self.assertRaises(ValueError):
                security.fingerprint(path)
        self.file.write_bytes(b'')
        with self.assertRaises(ValueError):
            security.fingerprint(self.file)
        with self.assertRaises(ValueError):
            security.private_path(self.root / 'outside.json')

    def test_result_attaches_only_to_matching_digital_holding(self):
        catalog = self.private / 'book-catalog.json'
        data = {'records': [{'holdings': [{'kind': 'physical', 'digital': None},
                 {'kind': 'digital', 'digital': {'canonical_reference': str(self.file)}},
                 {'kind': 'digital', 'digital': {'canonical_reference': '/other/book.pdf'}}]}]}
        catalog.write_text(json.dumps(data))
        self.scan()
        holdings = json.loads(catalog.read_text())['records'][0]['holdings']
        self.assertEqual(holdings[1]['digital']['security_scan']['status'], 'no_threats_detected')
        self.assertNotIn('security_scan', holdings[2]['digital'])
        self.assertIsNone(holdings[0]['digital'])


if __name__ == '__main__':
    unittest.main()
