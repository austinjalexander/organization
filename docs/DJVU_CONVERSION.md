# DjVu reading copies

User preference, October 20, 2026: automatically make PDF reading copies whenever
DjVu documents are encountered in active organization or intake work. Both `.djvu`
and `.djv`, with any letter case, qualify. This preference authorizes conversion
into ignored `.local/` without another conversion prompt. It does not start a
background service, expand discovery scope, or authorize unrelated filing changes.

## Reuse and preservation

Check local references and Dropbox cloud for an existing usable PDF of the same
source/edition first. Match metadata and provenance, not just similar filenames.
Keep source DjVu files, annotations, distinct editions, and cloud placeholders.
Treat a generated PDF as a derivative holding with its own hash, format, and path.
An original DjVu may remain the archival source while its verified PDF becomes the
preferred reading link. Do not delete, merge, rename, or replace either automatically.

For metadata-only inventories, record DjVu candidates privately for conversion;
do not open every discovered file or hydrate the entire collection. For a selected
intake document, hydrate/retrieve its bytes and convert automatically. Zero bytes,
unavailable access, or an indirect file missing components are pending conditions.

## Converter

```sh
python3 tools/djvu_to_pdf.py --help
python3 tools/djvu_to_pdf.py \
  --source /absolute/path/to/document.djvu \
  --output .local/djvu/attempt-01/reading.pdf \
  --receipt .local/djvu/attempt-01/conversion.json
```

Use a Python environment with `pypdf` and `reportlab`, and DjVuLibre's `ddjvu`,
`djvused`, and `djvutoxml` on PATH or supplied with `--bin-dir`. Use a Unicode TTF
with `--font` when the automatically located font cannot represent the OCR.
Prefer an existing runtime; the helper does not install software or use the network.
If dependencies are missing, use a temporary/local environment or a verified
temporary native package when permitted, and record versions/integrity evidence.
Do not install a desktop reader or change global file associations incidentally.
Normal filesystem/network permissions still apply.

The helper accepts a selected regular local source and writes only inside this
repo's `.local/`. It validates DjVu structure, rejects incomplete/indirect documents
and rotated pages whose OCR mapping it does not support, and checks source hashes
before/after. It runs native image conversion, carries existing text coordinates
into an invisible Unicode PDF layer, checks all page counts, validates image and
text presence, and publishes output without overwriting. Lossy reading-copy image
settings are recorded; PDF size may substantially exceed the DjVu. Original OCR
errors remain. Documents with no OCR are labeled explicitly; OCR is not invented.

Receipts record exact paths, hashes, tools/settings, outcome, verification limits,
and a staging rollback mapping. A prior matching PDF/receipt pair is hash-checked
and reused. A collision or unmatched existing file is held, not overwritten.
For a failed/pending attempt, retain its receipt and use a new attempt directory
when retrying. Interruptions may leave private temporary work; inspect its state
before resuming rather than guessing that output was published.

## Review and filing

Successful conversion initially means `converted_pending_visual_review`. Render
and inspect title/copyright, equations/diagrams, and a late substantive/index page.
Compare against the source as needed. Test searching/extraction and retain the
source hash and actual checked page numbers in the receipt. If satisfactory, set
`visual_review.status` to `passed` and record the result; do not claim all-page
visual review from samples. Preserve page images as the reading reference when
OCR differs. No learner reading progress is implied by conversion.

After review, use the normal concrete-batch approval workflow to file a new PDF
in an existing subject folder. Keep staging success distinct from external filing
and cloud sync. Prefer the verified PDF in the private book catalog and affected
project/library indexes, with a link back to its source. This workflow does not
replace per-batch sign-off or authorize new external folders, moves, or deletion.

Validation:

```sh
python3 -m unittest discover -s tools -p 'test_*.py'
```

Native integration tests run when DjVuLibre and the Python PDF dependencies are
available; set `DJVU_BIN_DIR` for an isolated native package. They create synthetic
documents inside private test staging and check source preservation, searchable
output, idempotent reuse, rotation holds, and collision/path guards. A skipped
integration test is not evidence of a successful conversion.
