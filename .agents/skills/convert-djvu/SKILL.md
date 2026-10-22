---
name: convert-djvu
description: Create PDF reading copies of DjVu documents encountered during file organization or book intake, preserving originals, existing OCR, and private provenance.
---

# Convert encountered DjVu documents

Read this repo's `AGENTS.md` and `docs/DJVU_CONVERSION.md`. The user requested automatic conversion of `.djvu` and `.djv` documents encountered in the current organization/intake work. Do not ask again to convert a selected, accessible document into private staging. This is task-time behavior, not a background watcher or permission to bulk-hydrate the collection.

- Check for an existing PDF of this same source/edition, locally and in Dropbox cloud when relevant. Verify its identity and usability before reusing it; preserve distinct editions and annotations. Do not acquire another book merely to change its format.
- Obtain only the selected source's actual bytes. Preserve online-only placeholders if hydration/retrieval is pending. Inventory-only discoveries enter a conversion queue without turning metadata discovery into a bulk content read.
- Apply `docs/BOOK_SECURITY.md` before decoding the source and before parsing or using derived PDFs. The conversion helper enforces these gates; a detection, incomplete scan or missing scanner is a hold, never a ready reading copy.
- Run `tools/djvu_to_pdf.py` with new output/receipt paths under ignored `.local/`. Use its `--help` and the conversion guide for dependencies and examples. The helper never files externally or modifies the source. Missing tools, incomplete/indirect files, unsupported orientation, or verification failures are recorded as pending/failed, never successful PDFs.
- Retain the source's OCR as searchable text when present; do not silently deliver an image-only substitute. Record when the source has no OCR. OCR errors, especially equations, remain; the page images are the reading reference. Do not claim that resized JPEG images are an archival or pixel-identical conversion.
- Before calling the result ready, visually review title/copyright, a representative equation/diagram page, and a late page; verify search/text extraction, page count, and unchanged source hash. Add checked page numbers and the actual outcome to the private receipt. A parsed PDF alone is not visual QA.
- Prefer the verified PDF for reading and index it as a derivative of the preserved DjVu. Filing, folders, moves, deletion, sharing, and application installation retain the repo's existing authorization rules. Update affected catalogs/links only for destinations actually verified. Record pending filing separately from successful conversion.
