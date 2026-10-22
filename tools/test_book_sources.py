import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import book_sources as books


class Response(io.BytesIO):
    url = 'https://example.org/book.pdf'
    headers = {'Content-Type': 'application/pdf'}


class BookSourcesTests(unittest.TestCase):
    def setUp(self):
        gate = patch.object(books, 'require_scan', return_value={'status': 'no_threats_detected'})
        gate.start()
        self.addCleanup(gate.stop)

    def test_security_hold_preserves_download_without_returning_ready_receipt(self):
        with tempfile.TemporaryDirectory() as root:
            private = Path(root) / '.local'
            private.mkdir()
            destination = private / 'book.pdf'
            check = {'status':'no_confirmed_match','checked_at':'2026-01-01','evidence':'cloud.json'}
            with patch.object(books, 'PRIVATE', private), patch.object(books, 'request', return_value=Response(b'%PDF-1.7\n%%EOF')):
                with patch.object(books, 'require_scan', side_effect=ValueError('security hold')):
                    with self.assertRaisesRegex(ValueError, 'security hold'):
                        books.stage_pdf(Response.url, destination, dropbox_check=check)
            self.assertTrue(destination.exists())

    def test_catalog_keeps_metadata_with_its_download_link(self):
        parser = books.CatalogHTML('https://example.org/index.php')
        parser.feed('<table><tr><td>Wrong book</td></tr><tr><td>Title &amp; Author</td>'
                    '<td><a href="/ads.php?md5=abc">1</a></td></tr></table>')
        self.assertEqual(parser.rows[1]['text'], 'Title & Author 1')
        self.assertEqual(parser.rows[1]['links'][0]['url'], 'https://example.org/ads.php?md5=abc')

    def test_staging_refuses_unchecked_duplicate_status(self):
        with self.assertRaises(ValueError):
            books.stage_pdf('https://example.org/book.pdf', books.PRIVATE/'book.pdf', dropbox_check={})

    def test_staging_rejects_external_and_symlink_destinations(self):
        with self.assertRaises(ValueError):
            books.private_path('/tmp/book.pdf')
        with tempfile.TemporaryDirectory() as root:
            private = Path(root)/'private'
            private.mkdir()
            (private/'link').symlink_to(Path(root), target_is_directory=True)
            with patch.object(books, 'PRIVATE', private), self.assertRaises(ValueError):
                books.private_path(private/'link'/'book.pdf')

    def test_pdf_integrity_and_collision_guards(self):
        with tempfile.TemporaryDirectory() as root:
            private = Path(root)/'private'
            private.mkdir()
            check = {'status':'no_confirmed_match','checked_at':'2026-01-01','evidence':'cloud-search.json'}
            destination = private/'book.pdf'
            payload = b'%PDF-1.7\nTest fixture\n%%EOF\n'
            with patch.object(books,'PRIVATE',private):
                with patch.object(books,'request',return_value=Response(b'<html>Challenge</html>')):
                    with self.assertRaises(ValueError):
                        books.stage_pdf(Response.url,destination,dropbox_check=check)
                with patch.object(books,'request',return_value=Response(payload)):
                    with self.assertRaises(ValueError):
                        books.stage_pdf(Response.url,destination,dropbox_check=check,expected_md5='wrong')
                self.assertFalse(destination.exists())
                with patch.object(books,'request',return_value=Response(payload)):
                    receipt=books.stage_pdf(Response.url,destination,dropbox_check=check,
                                            expected_md5=hashlib.md5(payload).hexdigest())
                self.assertEqual(receipt['sha256'],hashlib.sha256(payload).hexdigest())
                with self.assertRaises(FileExistsError):
                    books.stage_pdf(Response.url,destination,dropbox_check=check)
                self.assertEqual(destination.read_bytes(),payload)
                self.assertEqual(list(private.glob('.download-*')),[])


if __name__ == '__main__':
    unittest.main()
