#!/usr/bin/env python3
"""Read-only metadata discovery. Does not open source contents or follow links."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import stat

REPO = Path(__file__).resolve().parents[1]


def inspect_root(root, depth):
    result = {"root": str(root), "depth": depth, "entries": [], "errors": []}

    def visit(directory, level):
        try:
            with os.scandir(directory) as iterator:
                entries = sorted(iterator, key=lambda item: item.name.casefold())
            for entry in entries:
                if entry.name.startswith('.'):
                    continue
                path = Path(entry.path)
                try:
                    meta = entry.stat(follow_symlinks=False)
                    kind = ("symlink" if stat.S_ISLNK(meta.st_mode) else
                            "directory" if stat.S_ISDIR(meta.st_mode) else
                            "file" if stat.S_ISREG(meta.st_mode) else "other")
                    result["entries"].append({
                        "path": str(path), "relative_path": str(path.relative_to(root)),
                        "name": entry.name, "kind": kind,
                        "reported_bytes": meta.st_size if kind == "file" else None,
                        "modified_utc": datetime.fromtimestamp(meta.st_mtime, timezone.utc).isoformat(),
                        "stat_flags": getattr(meta, "st_flags", None),
                        "content_verified": False, "cloud_availability": "unknown",
                    })
                    if kind == "directory" and level < depth:
                        if (path / '.git').exists():
                            result["errors"].append({"path": str(path), "reason": "repository recursion skipped"})
                        else:
                            visit(path, level + 1)
                except OSError as exc:
                    result["errors"].append({"path": str(path), "reason": str(exc)})
        except OSError as exc:
            result["errors"].append({"path": str(directory), "reason": str(exc)})

    # Reject linked roots as well as linked descendants.
    try:
        if root.is_symlink():
            result["errors"].append({"path": str(root), "reason": "symlink root skipped; select real path explicitly"})
        elif root.is_dir():
            visit(root, 1)
        else:
            result["errors"].append({"path": str(root), "reason": "not an accessible directory"})
    except OSError as exc:
        result["errors"].append({"path": str(root), "reason": str(exc)})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', action='append', help='Directory to inspect; repeatable')
    parser.add_argument('--depth', type=int, default=1, choices=range(1, 4))
    args = parser.parse_args()
    home = Path.home()
    roots = [Path(p).expanduser().absolute() for p in args.root] if args.root else [
        home / 'Dropbox', home / 'Desktop', home / 'Documents', home / 'Downloads', home]
    now = datetime.now(timezone.utc)
    report = {
        "captured_utc": now.isoformat(), "method": "scandir+lstat; no content reads; no symlink traversal",
        "limitations": ["hidden entries excluded", "selective-sync omissions unknown", "cloud sync and contents unverified",
                        "reported bytes are not disk usage", "mtime does not establish last use or archive eligibility",
                        "metadata enumeration may contact the file provider; no deliberate content hydration"],
        "roots": [inspect_root(root, args.depth) for root in roots],
    }
    private_dir = REPO / '.local'
    private_dir.mkdir(mode=0o700, exist_ok=True)
    output = private_dir / ('inventory-' + now.strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    with output.open('x') as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
    print(output)
    for root in report['roots']:
        print(f"{root['root']}: {len(root['entries'])} entries; {len(root['errors'])} errors/holds")


if __name__ == '__main__':
    main()
