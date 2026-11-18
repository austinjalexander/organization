# Personal file organization

Dropbox is the default home for documents and media. Code, local configuration,
and Google Drive-governed material keep their appropriate homes. This repo holds
the tools and decisions for organizing those files, not the files themselves.
It also coordinates a catalog of physical books and their digital counterparts,
using Library of Congress Classification (LCC) alongside the existing subjects.

## Start here

- [Proposed structure and review order](docs/ORGANIZATION_PLAN.md)
- [Discovery, approval, verification, and rollback workflow](docs/WORKFLOW.md)
- [Confirmed policy and pending decisions](docs/DECISIONS.md)
- [Physical and digital book catalog, LCC, and shelving proposal](docs/BOOK_CATALOG.md)
- [Reusable book catalog template](templates/book-catalog.json)
- [Batch manifest template](templates/batch.json)
- [Dropbox-first book acquisition workflow](docs/BOOK_INTAKE.md)
- [Book security checks and catalog scan metadata](docs/BOOK_SECURITY.md)
- [Visual review of every selected image](docs/IMAGE_REVIEW.md) and the
  [image-review skill](.agents/skills/review-images/SKILL.md)
- [Automatic DjVu-to-PDF reading copies](docs/DJVU_CONVERSION.md) and the
  [conversion skill](.agents/skills/convert-djvu/SKILL.md)

The structure and review order are approved. B01's ten approved study-PDF moves
are complete: local SHA-256 verification passed, Dropbox filenames/sizes are
confirmed, and the physics library catalog is refreshed. Results and rollback
mappings are in `.local/B01-results.md` and `.local/B01-manifest.json`.
B02's two approved phone-import archives are complete: 610 child identities,
names, sizes, and client modification times are preserved. The user chose to
proceed on an assumption; complete Google Photos backup coverage is unverified.
Results are in `.local/B02-results.md`. B02b's 26 approved bookmark moves are
complete: provider content hashes match and the other 33 immediate source entries
are unchanged. Results are in `.local/B02b-results.md`. B02c's intact bookmark
folder archive is complete: 21 file identities and metadata are preserved, and
the other 32 immediate source entries are unchanged. Independent content hashes
were not retrieved. Results are in `.local/B02c-results.md`. B02d's two video
moves are complete: provider identities and metadata match, while existing
collection entries and the held installer are unchanged. Independent content
hashes were not retrieved. Results are in `.local/B02d-results.md`. B02e's three
approved schedule-export archives are complete in one new parent folder;
provider identities and metadata match, and the other 29 source entries are
unchanged. Contents were not independently hashed. Results are in
`.local/B02e-results.md`. Every image selected for organization now receives
visual review before sign-off. B02f's seven images have private descriptions and
previews in `.local/image-reviews/B02f/review.md`. Its original blanket archive
proposal is superseded. B02f revision 3 is complete: six approved images were
archived with descriptive names in three new folders, and all six SHA-256/provider
content hashes match. The other 23 immediate source entries remain unchanged,
including the held project asset. Results are in `.local/B02f-results.md`.
B02g is complete: three publication-format references were archived with
descriptive names in one new folder. SHA-256/provider content hashes match,
and the other 20 immediate source entries are unchanged. Results and reverse
paths are in `.local/B02g-results.md`. B02h is complete: three study references
were filed with descriptive names in existing subject folders, and all three
SHA-256/provider content hashes match. The other 17 source entries and 120
existing destination entries are unchanged. The physics filename catalog was
refreshed to 3,686 records and includes all three new paths as local placeholders.
Results and reverse paths are in `.local/B02h-results.md`. B02i is complete:
three documents were moved and renamed, three folders were created, and all
SHA-256 and provider content hashes match. The refreshed physics catalog
includes the new periodical path. Results and reverse paths are in
`.local/B02i-results.md`; 14 immediate desktop entries remain for review.
The initial review is in ignored
`.local/initial-review.json`; `.local/initial-review.html` is its searchable view.
Raw inventories and private decisions stay in `.local/`, outside Git tracking.
The working book catalog is `.local/book-catalog.json`. It starts with one
photo-observed physical copy; shelf location and edition verification are pending.
Its eventual Dropbox destination and physical shelving layout require review.
The separately approved BK01 and BK02 intakes are complete: eight acquired book
PDFs were filed in the established optics folder, verified locally and by cloud
name/size, and indexed in the physics catalog. Private results and reverse paths
are in `.local/books-2026-10-20/BK01-results.md` and
`.local/books-2026-10-20/BK02/BK02-results.md`; three requests remain unresolved.
BK03's two approved book moves are complete in three new literature subject
folders. Local SHA-256 hashes and Dropbox cloud names, paths, and sizes are
verified; the private book catalog is updated. Approval, results, and reverse
paths are in `.local/books-2026-10-26-irish/BK03-results.txt`; the other two titles
from that intake remain unacquired.
BK05's one approved textbook move is complete in the existing chemistry folder.
Local SHA-256 and Dropbox cloud name/path/size are verified; the private book
catalog and physics filename index are updated. Approval, results and reverse
mapping are in `.local/books-2026-11-09-mit-3091/BK05-results.md` and its manifest.
The two exact custom editions requested in that intake remain unacquired; the
filed book is a separately identified open-textbook adaptation.

## Metadata inventory

```sh
python3 tools/inventory.py
python3 tools/inventory.py --root /Users/nwprt/Dropbox/1_Studies --depth 1
```

The default scans only the immediate entries in Dropbox, Desktop, Documents,
Downloads, and the home directory. It does not open contents, follow links,
download files, or change anything in those source locations. It writes a dated
JSON snapshot to `.local/` and reports errors and partial coverage. A local scan
cannot enumerate folders excluded by Dropbox selective sync. Counts and file
sizes are metadata observations, not verified cloud totals or disk usage.

The initial approach adapts the physics repo's external-document/index split,
placeholder handling, and reversible manifests. Its permission to reorganize
selected books does not carry over here: this project requires batch sign-off.
