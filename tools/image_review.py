#!/usr/bin/env python3
"""Prepare selected image previews and bind visual descriptions to exact bytes.

Pillow decodes images; the agent's vision tools supply the semantic review.
No network calls, recursive discovery, external filing, or automatic classifiers.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import stat
import warnings

from PIL import Image, ImageOps


PRIVATE = Path(__file__).resolve().parents[1] / '.local'
CATEGORIES = {'photo', 'screenshot', 'document', 'diagram', 'artwork',
              'ui_asset', 'mixed', 'unknown'}


def no_links(path):
    path = Path(path).absolute()
    for part in [*reversed(path.parents), path]:
        if part.is_symlink():
            raise ValueError('Symlinks are not review sources or outputs')
    return path


def private_path(path):
    path = no_links(path).resolve()
    if not path.is_relative_to(PRIVATE.resolve()):
        raise ValueError('Review artifacts must stay under this repo .local/')
    return path


def fingerprint(path):
    path = no_links(path)
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_size == 0:
        raise ValueError('Source is not a nonempty regular file; placeholder/empty hold')
    sha, dropbox = hashlib.sha256(), hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(4194304):
            sha.update(block)
            dropbox.update(hashlib.sha256(block).digest())
    after = path.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError('Source changed while hashing')
    return {'sha256': sha.hexdigest(), 'provider_content_hash': dropbox.hexdigest(),
            'size': after.st_size}


def save_new(path, data):
    path = private_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')


def load(path):
    return json.loads(private_path(path).read_text())


def prepare(sources, out, edge=1600):
    rows = load(sources)
    if not isinstance(rows, list) or not rows or len(rows) > 50:
        raise ValueError('Supply 1–50 explicit source records, not a directory scan')
    ids = [r['item_id'] for r in rows]
    if len(set(ids)) != len(ids) or any(not re.fullmatch(r'[A-Za-z0-9_-]+', i) for i in ids):
        raise ValueError('Item IDs must be unique and path-safe')
    out = private_path(out)
    out.mkdir(parents=True, exist_ok=False)
    report = {'schema_version': 1, 'prepared_at_utc': datetime.now(timezone.utc).isoformat(),
              'method': 'agent_visual_inspection_required', 'items': []}
    for row in rows:
        item = {k: row[k] for k in ('item_id', 'local_path', 'source', 'provider_file_id')
                if k in row}
        item.update(status='hold', previews=[], classification=None)
        try:
            actual = fingerprint(row['local_path'])
            item.update(actual)
            for key in ('sha256', 'provider_content_hash', 'size'):
                if key in row and row[key] != actual[key]:
                    raise ValueError('Source identity mismatch: ' + key)
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(row['local_path']) as image:
                    count = getattr(image, 'n_frames', 1)
                    if count > 1000:
                        raise ValueError('More than 1000 frames: selected-frame review needed')
                    frames = sorted({0, count // 2, count - 1})
                    item.update(format=image.format, width=image.width, height=image.height,
                                frame_count=count, sampled_frames=frames,
                                coverage='all_frames' if count == len(frames) else 'sampled_frames')
                    for frame in frames:
                        image.seek(frame)
                        rendered = ImageOps.exif_transpose(image.copy()).convert('RGBA')
                        rendered.thumbnail((edge, edge), Image.Resampling.LANCZOS)
                        background = Image.new('RGBA', rendered.size, '#eeeeee')
                        background.alpha_composite(rendered)
                        path = out / f"{row['item_id']}-frame-{frame}.jpg"
                        background.convert('RGB').save(path, quality=92)
                        item['previews'].append({'frame': frame, 'path': str(path),
                                                 'sha256': fingerprint(path)['sha256']})
            if fingerprint(row['local_path'])['sha256'] != item['sha256']:
                raise ValueError('Source changed during preview generation')
            item['status'] = 'pending_visual_review'
        except (OSError, ValueError, SyntaxError, Image.DecompressionBombError,
                Image.DecompressionBombWarning, EOFError) as exc:
            item['error'] = type(exc).__name__ + ': ' + str(exc)
        report['items'].append(item)
    save_new(out / 'review.json', report)
    return report


def annotate(review, annotations, out):
    report, notes = load(review), load(annotations)
    ids = [i['item_id'] for i in report['items']]
    if not isinstance(notes, list) or len(notes) != len(ids):
        raise ValueError('Exactly one annotation per selected image is required')
    by_id = {a['item_id']: a for a in notes}
    if set(by_id) != set(ids) or len(by_id) != len(notes):
        raise ValueError('Missing, duplicate or extra image annotation')
    for item in report['items']:
        note = by_id[item['item_id']]
        if item['status'] != 'pending_visual_review':
            raise ValueError('Cannot mark an undecodable or unprepared image reviewed')
        if fingerprint(item['local_path'])['sha256'] != item['sha256']:
            raise ValueError('Source changed since preview preparation')
        if note.get('sha256') != item['sha256']:
            raise ValueError('Annotation is for different image bytes')
        if note.get('method') != 'agent_visual_inspection':
            raise ValueError('Classifier/filename guesses cannot replace visual review')
        if note.get('category') not in CATEGORIES or note.get('confidence') not in {
                'high', 'medium', 'low'}:
            raise ValueError('Specify a valid category and confidence')
        if not isinstance(note.get('description'), str) or len(note['description'].strip()) < 12:
            raise ValueError('A plain-language description is required')
        if not isinstance(note.get('uncertainties'), list):
            raise ValueError('Record uncertainties explicitly (empty list if none)')
        if sorted(set(note.get('reviewed_frames', []))) != item['sampled_frames']:
            raise ValueError('Inspect every prepared frame; a batch sample is insufficient')
        if not note.get('reviewer') or not note.get('evidence_tool'):
            raise ValueError('Record who reviewed the image and the vision tool used')
        for preview in item['previews']:
            if fingerprint(private_path(preview['path']))['sha256'] != preview['sha256']:
                raise ValueError('Preview changed after preparation')
        item['classification'] = note
        item['reviewed_at_utc'] = datetime.now(timezone.utc).isoformat()
        item['status'] = ('hold' if note['category'] == 'unknown' or
                          note['confidence'] == 'low' or note.get('needs_user_context') else 'reviewed')
    report['note'] = 'Visual review supports descriptions only; filing and naming need batch approval.'
    save_new(out, report)
    return report


def check(review):
    report = load(review)
    errors = []
    for item in report['items']:
        try:
            if item['status'] != 'reviewed' or not item.get('classification'):
                raise ValueError('Image remains unreviewed or held')
            if fingerprint(item['local_path'])['sha256'] != item['sha256']:
                raise ValueError('Source bytes changed; repeat review')
            for preview in item['previews']:
                if fingerprint(private_path(preview['path']))['sha256'] != preview['sha256']:
                    raise ValueError('Preview bytes changed; repeat review')
        except (OSError, ValueError, KeyError) as exc:
            errors.append({'item_id': item['item_id'], 'error': str(exc)})
    return {'ready_for_proposal': bool(report['items']) and not errors,
            'image_count': len(report['items']), 'errors': errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    prep = subs.add_parser('prepare', help='Decode only explicitly selected local sources')
    prep.add_argument('--sources', required=True, help='Private JSON list of selected source records')
    prep.add_argument('--out', required=True, help='New private output directory')
    record = subs.add_parser('annotate', help='Record actual visual observations; does not run a model')
    record.add_argument('--review', required=True)
    record.add_argument('--annotations', required=True)
    record.add_argument('--out', required=True, help='New private reviewed JSON file')
    gate = subs.add_parser('check', help='Reject holds, unreviewed images and changed bytes')
    gate.add_argument('--review', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'prepare':
            report = prepare(args.sources, args.out)
            print(json.dumps({'images': len(report['items']),
                              'holds': sum(i['status'] == 'hold' for i in report['items'])}))
        elif args.command == 'annotate':
            report = annotate(args.review, args.annotations, args.out)
            print(json.dumps({'images': len(report['items']),
                              'reviewed': sum(i['status'] == 'reviewed' for i in report['items'])}))
        else:
            result = check(args.review)
            print(json.dumps(result))
            return 0 if result['ready_for_proposal'] else 1
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f'{type(exc).__name__}: {exc}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
