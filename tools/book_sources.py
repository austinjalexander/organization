#!/usr/bin/env python3
"""Book-source discovery and PDF staging; never writes outside repo .local.

Catalog results are candidates, not verified identities or proof of availability.
Dropbox cloud searches must be performed separately before using stage_pdf.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import tempfile
import urllib.parse
import urllib.request
from book_security import require_scan

PRIVATE = Path(__file__).resolve().parents[1] / '.local'


class CatalogHTML(HTMLParser):
    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.rows, self.links = [], []
        self.row = None
        self.anchor = None
        self.suppressed = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('script', 'style'):
            self.suppressed += 1
        if tag == 'tr':
            self.row = {'text_parts': [], 'links': []}
        if tag == 'a' and attrs.get('href'):
            self.anchor = {'url': urllib.parse.urljoin(self.base_url, attrs['href']), 'label': ''}
            self.links.append(self.anchor)
            if self.row is not None:
                self.row['links'].append(self.anchor)

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.suppressed = max(0, self.suppressed - 1)
        if tag == 'a':
            self.anchor = None
        if tag == 'tr' and self.row is not None:
            self.row['text'] = ' '.join(self.row.pop('text_parts'))
            self.rows.append(self.row)
            self.row = None

    def handle_data(self, data):
        if self.suppressed or not data.strip():
            return
        if self.row is not None:
            self.row['text_parts'].append(data.strip())
        if self.anchor is not None:
            self.anchor['label'] += data.strip() + ' '


def private_path(path):
    path = Path(path).resolve()
    if PRIVATE.resolve() not in path.parents:
        raise ValueError('Private artifacts must stay under repository .local/')
    return path


def request(url, timeout=30):
    if urllib.parse.urlsplit(url).scheme != 'https':
        raise ValueError('Only HTTPS sources are supported')
    return urllib.request.urlopen(urllib.request.Request(
        url, headers={'User-Agent': 'BookIntake/0.1'}), timeout=timeout)


def search_libgen(title, evidence_path):
    url = 'https://libgen.li/index.php?' + urllib.parse.urlencode({
        'req': title, 'topics[]': 'l', 'objects[]': 'f', 'res': 100, 'curtab': 'f'})
    with request(url) as response:
        raw = response.read(8 * 1024 * 1024 + 1)
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError('Catalog response exceeds 8 MiB')
    with private_path(evidence_path).open('xb') as evidence:
        evidence.write(raw)
    parser = CatalogHTML(url)
    parser.feed(raw.decode('utf-8-sig', 'replace'))
    return {
        'search_url': url,
        'candidates': [r for r in parser.rows if any('/ads.php?md5=' in a['url'] for a in r['links'])],
        'json_urls': [a['url'] for a in parser.links if '/json.php?' in a['url']],
        'pagination_links': [a['url'] for a in parser.links if 'page=' in a['url']],
        'coverage': 'First result page only; review pagination before claiming absence',
    }


def stage_pdf(url, destination, *, dropbox_check, expected_md5=None, max_bytes=300*1024*1024):
    """Download into private staging, refusing overwrites and non-PDF payloads.

    The caller supplies a recent cloud-search evidence record. Human identity,
    edition, and completeness checks still precede a separately approved filing.
    """
    if dropbox_check.get('status') != 'no_confirmed_match' or not dropbox_check.get('evidence') or not dropbox_check.get('checked_at'):
        raise ValueError('A dated Dropbox duplicate-search evidence record is required')
    destination = private_path(destination)
    if destination.suffix.lower() != '.pdf':
        raise ValueError('Destination must be a PDF filename')
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    sha, md5, size = hashlib.sha256(), hashlib.md5(), 0
    fd, temp = tempfile.mkstemp(prefix='.download-', dir=destination.parent)
    try:
        with os.fdopen(fd, 'wb') as output, request(url, timeout=45) as response:
            final_url, content_type = response.url, response.headers.get('Content-Type')
            declared = response.headers.get('Content-Length')
            if declared and int(declared) > max_bytes:
                raise ValueError('PDF exceeds download size limit')
            first = True
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                if first and not chunk.startswith(b'%PDF-'):
                    raise ValueError('Response is not a PDF; login, challenge, or HTML page')
                first = False
                size += len(chunk)
                if size > max_bytes:
                    raise ValueError('PDF exceeds download size limit')
                output.write(chunk)
                sha.update(chunk)
                md5.update(chunk)
            if not size or (declared and size != int(declared)):
                raise ValueError('Empty or incomplete HTTP response')
            output.flush()
            os.fsync(output.fileno())
        with open(temp, 'rb') as stream:
            stream.seek(max(0, size - 4096))
            if b'%%EOF' not in stream.read():
                raise ValueError('Missing PDF end marker')
        if expected_md5 and md5.hexdigest().lower() != expected_md5.lower():
            raise ValueError('Catalog MD5 mismatch')
        os.link(temp, destination)  # Atomic creation; cannot overwrite.
        # Keep a held download in private staging; never parse, file, or delete it on an alert.
        security_scan = require_scan(destination)
        return {'source_url': url, 'final_url': final_url, 'content_type': content_type,
                'acquired_at': datetime.now(timezone.utc).isoformat(),
                'staged_path': str(destination), 'bytes': size, 'sha256': sha.hexdigest(),
                'md5': md5.hexdigest(), 'catalog_md5_verified': bool(expected_md5),
                'dropbox_check': dropbox_check, 'security_scan': security_scan,
                'verification': 'PDF header, EOF, length, hashes and security gate; identity review pending',
                'rollback': 'Remove only this staged path after verifying its SHA-256; no Dropbox change made'}
    finally:
        os.unlink(temp)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    search = commands.add_parser('search', help='Save a first-page catalog candidate report')
    search.add_argument('--query', required=True)
    search.add_argument('--evidence', required=True, help='New HTML path under .local/')
    search.add_argument('--output', required=True, help='New JSON path under .local/')
    stage = commands.add_parser('stage', help='Download a reviewed URL into private staging')
    stage.add_argument('--url', required=True)
    stage.add_argument('--destination', required=True)
    stage.add_argument('--dropbox-check', required=True, help='JSON with status, checked_at, evidence')
    stage.add_argument('--receipt', required=True, help='New JSON receipt path under .local/')
    stage.add_argument('--md5')
    args = parser.parse_args()
    output = private_path(args.output if args.command == 'search' else args.receipt)
    if output.exists() or output.is_symlink():
        parser.error('Refusing to overwrite an existing report or receipt')
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.command == 'search':
        evidence = private_path(args.evidence)
        if evidence == output or evidence.exists() or evidence.is_symlink():
            parser.error('Evidence requires a distinct new path')
        evidence.parent.mkdir(parents=True, exist_ok=True)
        result = search_libgen(args.query, evidence)
    else:
        if output == private_path(args.destination):
            parser.error('PDF destination and JSON receipt must be distinct')
        check = json.loads(private_path(args.dropbox_check).read_text())
        result = stage_pdf(args.url, args.destination, dropbox_check=check, expected_md5=args.md5)
    with output.open('x') as stream:
        json.dump(result, stream, indent=2)
    print(output)


if __name__ == '__main__':
    main()
