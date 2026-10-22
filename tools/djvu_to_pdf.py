#!/usr/bin/env python3
"""Preserve a selected DjVu and stage a searchable PDF/receipt under repo .local/."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import subprocess
import tempfile
import xml.etree.ElementTree as ET

PRIVATE = Path(__file__).resolve().parents[1] / '.local'


def private_path(value):
    if PRIVATE.is_symlink():
        raise ValueError('Repository .local must not be a symlink')
    path = Path(value).absolute()
    if path.is_symlink():
        raise ValueError('Private output must not be a symlink')
    path = path.resolve()
    if PRIVATE.resolve() not in path.parents:
        raise ValueError('Output and receipts must stay under repository .local/')
    return path


def digest(path):
    sha = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            sha.update(chunk)
    return sha.hexdigest()


def page_info(data):
    """Read bundled DjVu INFO records, including orientation; never follow links."""
    if not data.startswith(b'AT&TFORM'):
        raise ValueError('Missing DjVu header or unreadable placeholder')
    result = []

    def walk(start, end, parent=None):
        while start < end:
            if start + 8 > end:
                raise ValueError('Truncated DjVu chunk')
            kind, size = data[start:start + 4], int.from_bytes(data[start + 4:start + 8], 'big')
            payload, stop = start + 8, start + 8 + size
            if stop > end:
                raise ValueError('Truncated DjVu payload')
            if kind == b'FORM':
                if size < 4:
                    raise ValueError('Invalid DjVu FORM')
                walk(payload + 4, stop, data[payload:payload + 4])
            elif kind == b'INFO' and parent == b'DJVU':
                if size < 5:
                    raise ValueError('Invalid DjVu INFO')
                width, height = struct.unpack('>HH', data[payload:payload + 4])
                flags = data[payload + 9] & 7 if size >= 10 else 1
                if not width or not height:
                    raise ValueError('Invalid DjVu page dimensions')
                result.append({'width': width, 'height': height, 'orientation': flags})
            start = stop + (size & 1)
        if start > end + 1:
            raise ValueError('Invalid DjVu padding')

    walk(4, len(data))
    if not result:
        raise ValueError('No bundled pages; indirect documents need their components first')
    if any(p['orientation'] not in (0, 1) for p in result):
        raise ValueError('Rotated pages require explicit OCR coordinate support; source preserved')
    return result


def legal_xml(raw):
    """DjVu exporters can emit XML-1.0-illegal OCR controls, even as entities."""
    def allowed(n):
        return n in (9, 10, 13) or 32 <= n <= 0xD7FF or 0xE000 <= n <= 0xFFFD or 0x10000 <= n <= 0x10FFFF

    text = raw.decode('utf-8')
    text = re.sub(r'&#(x[0-9a-fA-F]+|[0-9]+);',
                  lambda m: m.group() if allowed(int(m[1][1:], 16) if m[1].startswith('x') else int(m[1])) else '', text)
    return ''.join(c for c in text if allowed(ord(c)))


def text_pages(xml_bytes):
    document = ET.fromstring(legal_xml(xml_bytes))
    pages = []
    for obj in document.iter('OBJECT'):
        zones = []
        hidden = obj.find('HIDDENTEXT')
        if hidden is not None:
            for node in hidden.iter():
                if len(node) or 'coords' not in node.attrib:
                    continue
                text = ' '.join((node.text or '').split())
                if not text:
                    continue
                coords = [int(n) for n in node.attrib['coords'].split(',')]
                if len(coords) != 4:
                    raise ValueError('Invalid OCR coordinates')
                left, right = sorted((coords[0], coords[2]))
                top, bottom = sorted((coords[1], coords[3]))
                if right > left and bottom > top:
                    zones.append((left, top, right, bottom, text + (' ' if node.tag == 'WORD' else '')))
        pages.append({'width': int(obj.attrib['width']), 'height': int(obj.attrib['height']), 'zones': zones})
    return pages


def assemble(native_pdf, xml, target, font=None):
    from pypdf import PdfReader, PdfWriter
    import reportlab
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    reader = PdfReader(native_pdf)
    pages = text_pages(xml)
    if len(reader.pages) != len(pages):
        raise ValueError('Image/OCR page counts differ')
    ocr_count = sum(bool(p['zones']) for p in pages)
    font_path = None
    if ocr_count:
        choices = [font] if font else [
            '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            str(Path(reportlab.__file__).parent / 'fonts/Vera.ttf')]
        font_path = next((str(p) for p in choices if p and Path(p).is_file()), None)
        if not font_path:
            raise ValueError('No Unicode TTF available for existing OCR; supply --font')
        registered = TTFont('DjVuOCR', font_path)
        used = {ord(c) for page in pages for zone in page['zones'] for c in zone[4]}
        missing = used - registered.face.charToGlyph.keys()
        if missing:
            raise ValueError('OCR font lacks characters; supply --font with the required coverage')
        pdfmetrics.registerFont(registered)
    overlay = io.BytesIO()
    layer = canvas.Canvas(overlay, pageCompression=1)
    for image_page, text_page in zip(reader.pages, pages):
        width, height = float(image_page.mediabox.width), float(image_page.mediabox.height)
        if abs((width / height) / (text_page['width'] / text_page['height']) - 1) > .02:
            raise ValueError('Image/OCR orientation or aspect ratio differs')
        sx, sy = width / text_page['width'], height / text_page['height']
        layer.setPageSize((width, height))
        for left, top, right, bottom, text in text_page['zones']:
            size = max(1, (bottom - top) * sy * .8)
            measured = pdfmetrics.stringWidth(text, 'DjVuOCR', size)
            if measured <= 0:
                continue
            obj = layer.beginText(left * sx, height - (bottom - (bottom - top) * .15) * sy)
            obj.setFont('DjVuOCR', size)
            obj.setTextRenderMode(3)
            obj.setHorizScale((right - left) * sx / measured * 100)
            obj.textOut(text)
            layer.drawText(obj)
        layer.showPage()
    layer.save()
    overlay.seek(0)
    text_reader = PdfReader(overlay)
    writer = PdfWriter()
    for image_page, text_page in zip(reader.pages, text_reader.pages):
        added = writer.add_page(image_page)
        added.merge_page(text_page)
    writer.add_metadata({'/Subject': 'PDF reading copy; original DjVu preserved. Existing OCR is uncorrected.'})
    with target.open('xb') as stream:
        writer.write(stream)
        stream.flush()
        os.fsync(stream.fileno())
    check = PdfReader(target)
    if len(check.pages) != len(pages):
        raise ValueError('Final page count mismatch')
    for page, text in zip(check.pages, pages):
        if not any(o.get_object().get('/Subtype') == '/Image' for o in page['/Resources']['/XObject'].values()):
            raise ValueError('Final PDF page lacks its image')
        if text['zones'] and not (page.extract_text() or '').strip():
            raise ValueError('Existing OCR missing from final PDF page')
    return {'pages': len(pages), 'pages_with_ocr': ocr_count,
            'ocr_status': 'existing_ocr_retained_uncorrected' if ocr_count else 'none_in_source',
            'font': font_path}


def convert(source, output, receipt, *, bin_dir=None, font=None, timeout=3600, width=1400, height=2100, quality=85):
    from book_security import require_scan
    output, receipt = private_path(output), private_path(receipt)
    if output == receipt or output.suffix.lower() != '.pdf' or receipt.suffix.lower() != '.json':
        raise ValueError('Use distinct PDF output and JSON receipt paths')
    source = Path(source).absolute()
    if any(p.is_symlink() for p in (source, *source.parents)):
        raise ValueError('Source links require separate review')
    if source.suffix.lower() not in ('.djvu', '.djv') or not stat.S_ISREG(source.stat().st_mode):
        raise ValueError('Select a regular .djvu/.djv file')
    source_scan = require_scan(source)
    source_sha = digest(source)
    settings = {'width': width, 'height': height, 'jpeg_quality': quality, 'font_requested': str(font) if font else None}
    if min(width, height, timeout) <= 0 or not 1 <= quality <= 100:
        raise ValueError('Invalid conversion settings')
    if output.exists() or receipt.exists():
        if output.is_file() and receipt.is_file():
            old = json.loads(receipt.read_text())
            if (old.get('source') == str(source) and old.get('source_sha256') == source_sha
                    and old.get('status', '').startswith('converted') and old.get('settings') == settings
                    and old.get('output') == str(output) and old.get('output_sha256') == digest(output)):
                return {**old, 'reused': True, 'security_scan': require_scan(output)}
        raise FileExistsError('Unmatched existing output/receipt; use a new attempt, never overwrite')
    output.parent.mkdir(parents=True, exist_ok=True)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    result = {'source': str(source), 'source_sha256': source_sha, 'source_bytes': source.stat().st_size,
              'output': str(output), 'settings': settings, 'created_at': datetime.now(timezone.utc).isoformat(),
              'source_preserved': True, 'source_security_scan': source_scan, 'status': 'pending',
              'visual_review': {'status': 'pending', 'checked_pages': []},
              'limitations': ['Resized JPEG reading copy, not pixel-identical archival output',
                              'Original OCR errors remain; annotations, links, and bookmarks are not migrated'],
              'filing': 'private_staging_only; external filing needs the relevant approved batch',
              'rollback': {'remove_only_derived_output': str(output), 'keep_source': str(source)}}
    try:
        info = page_info(source.read_bytes())
        import pypdf
        import reportlab
        commands = {name: str(Path(bin_dir) / name) if bin_dir else shutil.which(name)
                    for name in ('ddjvu', 'djvused', 'djvutoxml')}
        if any(not path or not Path(path).is_file() for path in commands.values()):
            raise ValueError('DjVuLibre tools unavailable; provide --bin-dir or a local runtime')
        result['tools'] = {'executables': commands, 'pypdf': pypdf.__version__, 'reportlab': reportlab.Version}

        def run(args):
            completed = subprocess.run(args, capture_output=True, timeout=timeout)
            if completed.returncode:
                raise ValueError(completed.stderr.decode('utf-8', 'replace')[-4000:])
            return completed.stdout

        count = int(run([commands['djvused'], str(source), '-e', 'n']).strip())
        if count != len(info):
            raise ValueError('Missing bundled components or source page count mismatch')
        result['tools']['decoder_banner'] = subprocess.run(
            [commands['ddjvu'], '--help'], capture_output=True, timeout=30).stderr.decode('utf-8', 'replace').splitlines()[:2]
        with tempfile.TemporaryDirectory(prefix='.djvu-', dir=output.parent) as temp:
            temp = Path(temp)
            native, xml, final = temp / 'images.pdf', temp / 'text.xml', temp / 'reading.pdf'
            run([commands['ddjvu'], '-format=pdf', f'-quality={quality}', f'-size={width}x{height}', str(source), str(native)])
            require_scan(native)
            run([commands['djvutoxml'], '--without-anno', str(source), str(xml)])
            result.update(assemble(native, xml.read_bytes(), final, font))
            result['security_scan'] = require_scan(final)
            if result['pages'] != count or digest(source) != source_sha:
                raise ValueError('Source changed or final page count mismatch')
            result.update(output_sha256=digest(final), output_bytes=final.stat().st_size,
                          status='converted_pending_visual_review')
            os.link(final, output)  # Atomic publication that cannot overwrite.
    except Exception as error:
        result.update(status='pending', reason=f'{type(error).__name__}: {error}', source_preserved=source.exists() and digest(source) == source_sha)
    with receipt.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', required=True, help='New PDF path under repo .local/')
    parser.add_argument('--receipt', required=True, help='New JSON path under repo .local/')
    parser.add_argument('--bin-dir', help='Existing DjVuLibre executable directory')
    parser.add_argument('--font', help='Unicode TTF for source OCR')
    parser.add_argument('--timeout', type=int, default=3600, help='Seconds per native command')
    parser.add_argument('--width', type=int, default=1400, help='Maximum rendered pixel width')
    parser.add_argument('--height', type=int, default=2100, help='Maximum rendered pixel height')
    parser.add_argument('--quality', type=int, default=85, help='JPEG reading-copy quality, 1–100')
    args = parser.parse_args()
    try:
        result = convert(args.source, args.output, args.receipt, bin_dir=args.bin_dir, font=args.font,
                         timeout=args.timeout, width=args.width, height=args.height, quality=args.quality)
    except (ValueError, OSError) as error:
        parser.exit(2, f'{error}\n')
    print(json.dumps({'status': result['status'], 'receipt': str(private_path(args.receipt)), 'reused': result.get('reused', False)}))
    return 0 if result['status'].startswith('converted') else 2


if __name__ == '__main__':
    raise SystemExit(main())
