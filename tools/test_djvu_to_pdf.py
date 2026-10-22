import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import djvu_to_pdf as djvu


def chunk(kind, payload):
    return kind + len(payload).to_bytes(4, 'big') + payload + (b'\0' if len(payload) % 2 else b'')


def synthetic_header(orientation=1):
    info = struct.pack('>HH', 600, 900) + b'\x18\0\x2c\x01\x16' + bytes([orientation])
    return b'AT&T' + chunk(b'FORM', b'DJVU' + chunk(b'INFO', info))


class DjVuTests(unittest.TestCase):
    def setUp(self):
        gate = patch('book_security.require_scan', return_value={'status': 'no_threats_detected'})
        gate.start()
        self.addCleanup(gate.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.private = self.root / '.local'
        self.private.mkdir()
        self.source = self.root / 'source.djvu'
        self.source.write_bytes(synthetic_header())
        self.output = self.private / 'copy.pdf'
        self.receipt = self.private / 'receipt.json'
        self.patcher = patch.object(djvu, 'PRIVATE', self.private)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.temp.cleanup()

    def test_private_scope_and_symlinks(self):
        with self.assertRaises(ValueError):
            djvu.private_path(self.root / 'outside.pdf')
        (self.private / 'escape').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            djvu.private_path(self.private / 'escape' / 'outside.pdf')
        alias = self.root / 'alias.djvu'
        alias.symlink_to(self.source)
        with self.assertRaises(ValueError):
            djvu.convert(alias, self.output, self.receipt)

    def test_header_truncation_and_orientation(self):
        self.assertEqual(djvu.page_info(synthetic_header())[0]['width'], 600)
        for bad in (b'', synthetic_header()[:-3], synthetic_header(2), synthetic_header(5)):
            with self.assertRaises(ValueError):
                djvu.page_info(bad)

    def test_exporter_control_entities_and_line_or_word_text(self):
        xml = b'<DjVuXML><BODY><OBJECT width="600" height="900"><HIDDENTEXT><LINE coords="1,50,99,20">A&#31;B</LINE><LINE><WORD coords="1,90,50,60">word</WORD></LINE></HIDDENTEXT></OBJECT></BODY></DjVuXML>'
        zones = djvu.text_pages(xml)[0]['zones']
        self.assertEqual(zones[0], (1, 20, 99, 50, 'AB'))
        self.assertEqual(zones[1][4], 'word ')

    def test_placeholder_and_missing_tools_leave_pending_receipt(self):
        self.source.write_bytes(b'')
        result = djvu.convert(self.source, self.output, self.receipt)
        self.assertEqual(result['status'], 'pending')
        self.assertTrue(result['source_preserved'])
        self.assertFalse(self.output.exists())
        self.assertEqual(self.source.read_bytes(), b'')
        self.receipt.unlink()
        self.source.write_bytes(synthetic_header())
        with patch.object(djvu.shutil, 'which', return_value=None):
            result = djvu.convert(self.source, self.output, self.receipt)
        self.assertEqual(result['status'], 'pending')
        self.assertFalse(self.output.exists())

    def test_existing_outputs_are_never_overwritten(self):
        self.output.write_bytes(b'original')
        with self.assertRaises(FileExistsError):
            djvu.convert(self.source, self.output, self.receipt)
        self.assertEqual(self.output.read_bytes(), b'original')
        self.assertFalse(self.receipt.exists())

    def test_reuse_requires_matching_source_settings_and_pdf_hash(self):
        self.output.write_bytes(b'verified existing PDF fixture')
        record = {'source': str(self.source), 'source_sha256': djvu.digest(self.source), 'output': str(self.output),
                  'output_sha256': djvu.digest(self.output), 'status': 'converted_pending_visual_review',
                  'settings': {'width': 1400, 'height': 2100, 'jpeg_quality': 85, 'font_requested': None}}
        self.receipt.write_text(json.dumps(record))
        self.assertTrue(djvu.convert(self.source, self.output, self.receipt)['reused'])
        self.output.write_bytes(b'subsequent edits')
        with self.assertRaises(FileExistsError):
            djvu.convert(self.source, self.output, self.receipt)


    def test_real_conversion_keeps_source_searchable_text_and_page_count(self):
        directory = os.environ.get('DJVU_BIN_DIR')
        paths = {name: str(Path(directory) / name) if directory else shutil.which(name)
                 for name in ('c44', 'djvm', 'djvused', 'ddjvu', 'djvutoxml')}
        if any(not path or not Path(path).is_file() for path in paths.values()):
            self.skipTest('Native DjVuLibre tools unavailable')
        try:
            from pypdf import PdfReader
            from reportlab.pdfbase import pdfmetrics
        except ImportError:
            self.skipTest('Python PDF dependencies unavailable')
        # Synthetic image and supplied OCR; no private book contents in tests.
        image = self.root / 'fixture.ppm'
        image.write_bytes(b'P6\n60 90\n255\n' + bytes([240, 240, 255]) * 60 * 90)
        self.source.unlink()
        subprocess.run([paths['c44'], str(image), str(self.source)], check=True, capture_output=True)
        second_image = self.root / 'second.ppm'
        second_image.write_bytes(b'P6\n60 90\n255\n' + bytes([255, 220, 220]) * 60 * 90)
        second_page = self.root / 'second.djvu'
        subprocess.run([paths['c44'], str(second_image), str(second_page)], check=True, capture_output=True)
        text = self.root / 'fixture.txt'
        text.write_text('(page 0 0 60 90 (line 4 70 55 82 "Searchable conversion fixture"))\n')
        subprocess.run([paths['djvused'], str(self.source), '-e', f'select 1; set-txt {text}; save'], check=True, capture_output=True)
        bundled = self.root / 'bundled.djvu'
        subprocess.run([paths['djvm'], '-c', str(bundled), str(self.source), str(second_page)], check=True, capture_output=True)
        os.replace(bundled, self.source)
        before = self.source.read_bytes()
        result = djvu.convert(self.source, self.output, self.receipt, bin_dir=directory, width=240, height=360)
        self.assertEqual(result['status'], 'converted_pending_visual_review', result)
        self.assertEqual(result['pages'], 2)
        self.assertEqual(result['pages_with_ocr'], 1)
        self.assertEqual(self.source.read_bytes(), before)
        pdf = PdfReader(self.output)
        self.assertEqual(len(pdf.pages), 2)
        self.assertIn('Searchable conversion fixture', pdf.pages[0].extract_text())
        self.assertFalse(pdf.pages[1].extract_text().strip())
        first_color = pdf.pages[0].images[0].image.convert('RGB').getpixel((10, 10))
        second_color = pdf.pages[1].images[0].image.convert('RGB').getpixel((10, 10))
        self.assertGreater(first_color[2], first_color[0])
        self.assertGreater(second_color[0], second_color[2])
        self.assertEqual(result['output_sha256'], hashlib.sha256(self.output.read_bytes()).hexdigest())
        self.assertTrue(djvu.convert(self.source, self.output, self.receipt, bin_dir=directory, width=240, height=360)['reused'])
        no_ocr = djvu.convert(second_page, self.private / 'no-ocr.pdf', self.private / 'no-ocr.json',
                              bin_dir=directory, width=240, height=360)
        self.assertEqual(no_ocr['status'], 'converted_pending_visual_review', no_ocr)
        self.assertEqual(no_ocr['ocr_status'], 'none_in_source')
        self.assertEqual(no_ocr['pages_with_ocr'], 0)
        # Real rotated documents must be held rather than mapping OCR incorrectly.
        rotated = self.root / 'rotated.djvu'
        rotated.write_bytes(before)
        subprocess.run([paths['djvused'], str(rotated), '-e', 'select 1; set-rotation 1; save'], check=True, capture_output=True)
        pending = djvu.convert(rotated, self.private / 'rotated.pdf', self.private / 'rotated.json', bin_dir=directory)
        self.assertEqual(pending['status'], 'pending')
        self.assertFalse((self.private / 'rotated.pdf').exists())


if __name__ == '__main__':
    unittest.main()
