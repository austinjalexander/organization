# Security checks for digital books

The user requested security scans for new downloads and previously unscanned
books selected in active work. This authorizes read-only local scanning of the
selected bytes and private catalog updates without another confirmation.
Metadata-only discovery remains metadata-only; do not hydrate a collection or
enable a background watcher. External filing, deletion and sharing keep their
existing approval requirements.

## Before content use

Run this before opening, extracting, rendering, converting or filing a selected
book, including a browser download. New files must finish downloading first.

```sh
python3 tools/book_security.py /absolute/path/to/book.pdf
```

The helper uses the installed `clamscan` locally. It never uploads books and does
not enable removal, copying or quarantine options. It hashes the selected regular
file before and after scanning, refuses links/directories/empty placeholders, and
stores an immutable report under `.local/book-security/scans/<sha256>/`.
`.local/book-security/index.json` points to the latest attempt by SHA-256.

The private signature database defaults to `.local/book-security/clamav-db/`.
Supply `--database /absolute/signature/directory` for another installed database.
Update official signatures with `freshclam` before an intake or when definitions
are stale. The current machine's private updater configuration is
`.local/book-security/freshclam.conf`; its logs remain private. Keep local
configuration out of Git and do not disable TLS or signature verification.
Signature downloads send no book contents. No scheduled updater is installed.

The default scan permits up to 1 GiB per file, 2 GiB scanned container data,
100,000 embedded files, recursion depth 50, and 120 seconds per scanner file.
The subprocess has a separate 180-second limit. Limit/encryption alerts and any
warning, skip, error or timeout prevent a successful status. These explicit limits
avoid silently treating an unscanned large book as clean. Daily signatures must
be dated within seven days. If coverage cannot be established, keep a hold and
report the reason rather than automatically relaxing limits.

`ensure_scan()` can reuse a `no_threats_detected` result only when the SHA-256,
engine/version, database identity and policy match, daily signatures are current,
and the result is no older than seven days. Changed bytes or definitions require
a new scan; preserved older reports retain their historical meaning. `--force`
requests a fresh attempt. A move alone does not invalidate a matching hash.

## Catalog metadata

Security belongs to the individual digital holding and exact bytes, not to the
title, ISBN, edition or physical copy. `digital.security_scan` stores:

- `status`: `not_scanned`, `no_threats_detected`, `detected`, `incomplete`,
  `error`, or `unavailable`.
- `sha256`, `scanned_at`, engine/version, database versions and policy version.
- The private immutable `report` reference, with full command, limits, database
  headers/dates, exit code, alerts, stdout/stderr and unchanged-file evidence.
- A limitation: no threats detected does not establish safety.

Missing, empty, inaccessible or metadata-only files remain `not_scanned` with a
reason; do not infer success. Physical holdings have no digital scan result.
The helper updates existing matching digital holdings in `.local/book-catalog.json`
by canonical path or SHA-256. If the book is not cataloged yet, its hash registry
is the evidence source; attach the result when registering its holding. Keep
annotations, editions, original formats and converted copies distinct. Scan each
derivative; never carry a source result over to different bytes.

## Integration and holds

- `book_sources.stage_pdf()` scans the completed private download before returning
  a ready receipt. A held download remains private for review.
- `djvu_to_pdf.convert()` gates the original before decoding, the native PDF
  before PDF parsing, and the final reading copy before publication. Reused
  conversions also need a current scan.
- `execute_local_batch.py` applies the gate to `BK` book-filing batches.
- Reading or manually acquired books use the CLI gate and the persistent project
  instructions. This does not intercept unrelated applications opening files.

On any detection or incomplete/error status, stop routine content processing and
surface the report. Do not execute embedded content or automatically repair,
sanitize, rename, move, quarantine or delete the book. Further action requires
a concrete review and the relevant authorization. A scanner hit can be a false
positive; retain its exact signature and evidence rather than declaring malware
without investigation.

ClamAV provides one local detection layer, not a guarantee against new exploits,
malicious links or all active content. Transfer/MD5 checks, PDF readability and
visual QA are separate checks, not substitutes for scanning.

Reference: [ClamAV scanning documentation](https://docs.clamav.net/manual/Usage/Scanning.html).
