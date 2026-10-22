#!/usr/bin/env python3
"""Read-only ClamAV checks for selected books; hash-bound evidence stays private."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import uuid

PRIVATE = Path(__file__).resolve().parents[1] / '.local'
POLICY_VERSION = 1
LIMITATIONS = 'No threats detected is a scanner result, not proof of safety. No files uploaded, executed, removed, or quarantined.'


def now():
    return datetime.now(timezone.utc).isoformat()


def private_path(value):
    path = Path(value).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Private evidence paths cannot follow links')
    if PRIVATE.resolve() not in path.resolve().parents:
        raise ValueError('Security evidence must stay under repository .local/')
    return path


def fingerprint(value):
    path = Path(value).absolute()
    if '\n' in str(path) or '\r' in str(path):
        raise ValueError('Control characters in file paths require separate review')
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Select a regular book file without symlink ancestors')
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError('Select one regular book file, not a directory or device')
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size == 0:
            raise ValueError('Empty file or online-only placeholder: leave unscanned; do not hydrate broadly')
        sha = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            sha.update(chunk)
        after = os.fstat(stream.fileno())
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
    if identity(before) != identity(after):
        raise ValueError('File changed during hashing')
    return {'path': str(path), 'sha256': sha.hexdigest(), 'bytes': after.st_size,
            'mtime_ns': after.st_mtime_ns, 'device': after.st_dev, 'inode': after.st_ino}


def atomic_json(path, value):
    fd, temporary = tempfile.mkstemp(prefix='.security-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def database_identity(directory):
    files = []
    if directory:
        for p in sorted(Path(directory).iterdir()):
            if p.suffix not in ('.cvd', '.cld') or p.is_symlink() or not p.is_file():
                continue
            with p.open('rb') as stream:
                header = stream.read(512).decode('ascii', 'replace').strip()
            files.append({'name': p.name, 'bytes': p.stat().st_size, 'mtime_ns': p.stat().st_mtime_ns,
                          'header': header})
        if not files:
            raise ValueError('No ClamAV signature databases available')
    return files


def database_current(databases):
    daily = next((d for d in databases if d['name'] in ('daily.cvd', 'daily.cld')), None)
    if not daily:
        return False
    try:
        date = datetime.strptime(daily['header'].split(':')[1], '%d %b %Y %H-%M %z')
        age = (datetime.now(timezone.utc) - date).total_seconds()
        return 0 <= age <= 7 * 86400
    except (ValueError, IndexError):
        return False


def classify(returncode, stdout, stderr, path):
    combined = stdout + '\n' + stderr
    alerts = [line for line in stdout.splitlines() if line.endswith(' FOUND')]
    if re.search(r'Heuristics\.(Limits\.Exceeded|Encrypted)', combined, re.I):
        return 'incomplete', alerts
    if returncode == 1 and alerts:
        return 'detected', alerts
    if returncode != 0:
        return 'error', alerts
    if re.search(r'WARNING|ERROR|skipp|exceed|time.?out', combined, re.I):
        return 'incomplete', alerts
    if f'{path}: OK' not in stdout or not re.search(r'Scanned files:\s*[1-9]\d*', stdout):
        return 'incomplete', alerts
    return 'no_threats_detected', []


def ensure_scan(source, *, database=None, force=False, timeout=180, scanner=None):
    """Reuse only a matching successful hash/engine/database/policy result; otherwise scan."""
    before = fingerprint(source)
    root = private_path(PRIVATE / 'book-security')
    root.mkdir(parents=True, exist_ok=True)
    db = Path(database).absolute() if database else root / 'clamav-db'
    if not db.is_dir():
        db = None
    executable = scanner or shutil.which('clamscan')
    db_args = [f'--database={db}'] if db else []
    engine = None
    if executable:
        version = subprocess.run([executable, *db_args, '--version'], capture_output=True, text=True, timeout=20)
        if version.returncode == 0:
            engine = version.stdout.strip()
    databases = database_identity(db)
    # Explicit database identity is required for reusable results.
    context = {'engine': engine, 'database_directory': str(db) if db else None,
               'databases': databases, 'policy_version': POLICY_VERSION}
    index_path = root / 'index.json'
    index = json.loads(index_path.read_text()) if index_path.exists() else {'schema_version': 1, 'by_sha256': {}}
    previous = index['by_sha256'].get(before['sha256'])
    if previous and not force and database_current(databases):
        old_path = private_path(previous['report'])
        old = json.loads(old_path.read_text())
        age = datetime.now(timezone.utc) - datetime.fromisoformat(old['finished_at'])
        if (old['file']['sha256'] == before['sha256'] and old['status'] == 'no_threats_detected'
                and old['context'] == context and 0 <= age.total_seconds() <= 7 * 86400):
            result = {**old, 'report': str(old_path), 'reused': True, 'current_path': before['path']}
            update_catalog(result)
            return result
    report = {'schema_version': 1, 'scan_id': str(uuid.uuid4()), 'started_at': now(),
              'file': before, 'context': context, 'status': 'unavailable', 'exit_code': None,
              'alerts': [], 'stdout': '', 'stderr': '', 'limitations': LIMITATIONS,
              'actions': {'uploaded': False, 'deleted': False, 'quarantined': False}}
    args = [executable, *db_args, '--official-db-only=yes', '--scan-pdf=yes', '--scan-archive=yes',
            '--follow-file-symlinks=0', '--follow-dir-symlinks=0', '--allmatch=yes', '--disable-cache',
            '--alert-exceeds-max=yes', '--alert-encrypted=yes', '--fail-if-cvd-older-than=7',
            '--max-filesize=1024M', '--max-scansize=2048M', '--max-files=100000',
            '--max-recursion=50', '--max-scantime=120000', before['path']]
    report['command'] = args
    if executable and engine:
        try:
            run = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
            report.update(exit_code=run.returncode, stdout=run.stdout, stderr=run.stderr)
            report['status'], report['alerts'] = classify(run.returncode, run.stdout, run.stderr, before['path'])
            if not database_current(databases) and report['status'] == 'no_threats_detected':
                report.update(status='incomplete', reason='Daily signatures absent, unparseable, or older than seven days')
        except subprocess.TimeoutExpired as error:
            report.update(status='incomplete', reason='Scanner timeout',
                          stdout=(error.stdout or b'').decode('utf-8', 'replace') if isinstance(error.stdout, bytes) else (error.stdout or ''),
                          stderr=(error.stderr or b'').decode('utf-8', 'replace') if isinstance(error.stderr, bytes) else (error.stderr or ''))
    try:
        after = fingerprint(source)
        report['file_unchanged'] = after == before
        if after != before:
            report.update(status='incomplete', reason='File identity changed during scan')
        if database_identity(db) != databases:
            report.update(status='incomplete', reason='Signature database changed during scan')
    except (OSError, ValueError) as error:
        report.update(status='incomplete', file_unchanged=False, reason=str(error))
    report['finished_at'] = now()
    reports = root / 'scans' / before['sha256']
    reports.mkdir(parents=True, exist_ok=True)
    report_path = reports / (report['scan_id'] + '.json')
    with report_path.open('x') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    with (root / 'index.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        index = json.loads(index_path.read_text()) if index_path.exists() else {'schema_version': 1, 'by_sha256': {}}
        index['by_sha256'][before['sha256']] = summary({**report, 'report': str(report_path)})
        atomic_json(index_path, index)
    result = {**report, 'report': str(report_path), 'reused': False}
    update_catalog(result)
    return result


def summary(report):
    return {'status': report['status'], 'sha256': report['file']['sha256'],
            'scanned_at': report['finished_at'], 'engine': report['context']['engine'],
            'report': report['report'], 'policy_version': POLICY_VERSION,
            'database_versions': {d['name']: d['header'].split(':')[2] if len(d['header'].split(':')) > 2 else None
                                  for d in report['context']['databases']},
            'limitation': 'No threats detected does not establish safety.'}


def update_catalog(report):
    """Attach scan evidence to known digital holdings; do not invent bibliographic records."""
    catalog = private_path(PRIVATE / 'book-catalog.json')
    if not catalog.exists():
        return
    root = private_path(PRIVATE / 'book-security')
    with (root / 'catalog.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = json.loads(catalog.read_text())
        changed = False
        for book in data['records']:
            for holding in book.get('holdings', []):
                digital = holding.get('digital')
                if not digital:
                    continue
                if (digital.get('canonical_reference') == report.get('current_path', report['file']['path'])
                        or digital.get('sha256') == report['file']['sha256']):
                    digital.update(sha256=report['file']['sha256'], security_scan=summary(report))
                    changed = True
        if changed:
            data['updated_on'] = datetime.now(timezone.utc).date().isoformat()
            atomic_json(catalog, data)


def require_scan(source):
    report = ensure_scan(source)
    if report['status'] != 'no_threats_detected':
        raise ValueError(f"Book security scan held: {report['status']}; review {report['report']}")
    return summary(report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='+', type=Path, help='Exact selected files; no recursive scan')
    parser.add_argument('--database', type=Path)
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    held = False
    for path in args.files:
        try:
            result = ensure_scan(path, database=args.database, force=args.force)
            print(json.dumps({'path': str(path), **summary(result), 'reused': result['reused']}))
            held |= result['status'] != 'no_threats_detected'
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            print(json.dumps({'path': str(path), 'status': 'not_scanned', 'reason': str(error)}))
            held = True
    return 2 if held else 0


if __name__ == '__main__':
    raise SystemExit(main())
