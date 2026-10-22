#!/usr/bin/env python3
"""Execute an explicitly approved local batch using macOS atomic no-overwrite moves."""
import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import unicodedata


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.writing')
    with temporary.open('w') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def folded(name):
    return unicodedata.normalize('NFC', name).casefold()


def no_symlink_ancestors(path):
    for parent in path.parents:
        if parent.is_symlink():
            raise ValueError(f'symlink ancestor: {parent}')


def inspect_source(item):
    source = Path(item['source'])
    no_symlink_ancestors(source)
    fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(f'not a regular file: {source}')
        expected = item['integrity']
        if (before.st_size, before.st_mtime_ns) != (expected['bytes'], expected['source_mtime_ns']):
            raise ValueError(f'source size/mtime changed: {source}')
        actual_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
        after = os.fstat(stream.fileno())
        if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
            raise ValueError(f'source changed during hashing: {source}')
        if actual_hash != expected['sha256']:
            raise ValueError(f'source hash changed: {source}')
    return before


def inspect_destination(item):
    destination = Path(item['destination'])
    no_symlink_ancestors(destination)
    if not destination.parent.is_dir():
        raise ValueError(f'destination parent unavailable: {destination.parent}')
    collisions = [e.name for e in os.scandir(destination.parent)
                  if folded(e.name) == folded(destination.name)]
    if collisions:
        raise ValueError(f'destination collision: {destination}')
    return destination.parent.stat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--preflight-only', action='store_true')
    args = parser.parse_args()
    path = args.manifest.absolute()
    batch = json.loads(path.read_text())
    approval = batch.get('approval')
    if not approval or approval.get('revision') != batch['revision']:
        raise ValueError('explicit approval for this revision is required')
    if batch.get('status') != 'approved':
        raise ValueError('batch is not in approved state; inspect its log before resuming')
    items = batch['items']
    if set(approval.get('item_ids', [])) != {i['item_id'] for i in items}:
        raise ValueError('approval does not cover exactly these items')
    for item in items:
        if item['status'] != 'approved' or item['action'] not in {'move', 'move and rename'}:
            raise ValueError('unsupported or unapproved item')
        source_stat = inspect_source(item)
        parent_stat = inspect_destination(item)
        if source_stat.st_dev != parent_stat.st_dev:
            raise ValueError('cross-filesystem move requires a separately verified copy workflow')
        if batch['batch_id'].startswith('BK'):
            from book_security import require_scan
            item['security_scan'] = require_scan(item['source'])
    if args.preflight_only:
        print(f"Preflight passed: {len(items)} sources hash-verified; no local collisions.")
        return
    if sys.platform != 'darwin':
        raise ValueError('atomic renamex_np implementation requires macOS')
    library = ctypes.CDLL(None, use_errno=True)
    rename_exclusive = library.renamex_np
    rename_exclusive.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
    rename_exclusive.restype = ctypes.c_int
    # RENAME_EXCL = 0x00000004, verified in the installed macOS SDK sys/stdio.h.
    batch['status'] = 'in_progress'
    batch['started_utc'] = timestamp()
    save(path, batch)
    for item in items:
        try:
            source_stat = inspect_source(item)
            inspect_destination(item)
            item['status'] = 'in_progress'
            item['outcomes'].append({'event': 'before_move', 'at_utc': timestamp(),
                                     'source_inode': source_stat.st_ino, 'source_device': source_stat.st_dev})
            save(path, batch)
            current = os.lstat(item['source'])
            if (current.st_ino, current.st_dev, current.st_mtime_ns) != (source_stat.st_ino, source_stat.st_dev, source_stat.st_mtime_ns):
                raise ValueError('source identity changed immediately before move')
            if rename_exclusive(os.fsencode(item['source']), os.fsencode(item['destination']), 4) != 0:
                error = ctypes.get_errno()
                raise OSError(error, os.strerror(error), item['destination'])
            destination = Path(item['destination'])
            with destination.open('rb') as stream:
                actual_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
            destination_stat = destination.stat()
            if actual_hash != item['integrity']['sha256'] or destination_stat.st_size != item['integrity']['bytes']:
                raise ValueError('destination verification failed; preserve destination and inspect both paths')
            if os.path.lexists(item['source']):
                raise ValueError('source path exists after move; inspect both paths')
            item['status'] = 'verified_local'
            item['outcomes'].append({'event': 'moved_and_hash_verified', 'at_utc': timestamp(),
                'destination_sha256': actual_hash, 'destination_bytes': destination_stat.st_size,
                'destination_inode': destination_stat.st_ino, 'source_absent': True,
                'cloud_sync_status': 'pending'})
            save(path, batch)
            print(item['item_id'] + ': moved and SHA-256 verified', flush=True)
        except Exception as exc:
            item['status'] = 'needs_inspection'
            item['outcomes'].append({'event': 'error', 'at_utc': timestamp(), 'message': str(exc),
                'source_exists': os.path.lexists(item['source']), 'destination_exists': os.path.lexists(item['destination'])})
            batch['status'] = 'needs_inspection'
            save(path, batch)
            raise
    batch['status'] = 'verified_local_cloud_pending'
    batch['completed_local_utc'] = timestamp()
    save(path, batch)
    print(f"Completed {len(items)} approved moves; cloud verification pending.")


if __name__ == '__main__':
    main()
