# Organization workflow

## Discover

Inventory names, types, sizes, modification times, and access errors without
reading contents or following directory symlinks. Track evidence as local
metadata, screenshot label, cloud metadata, or verified content. Record scan
scope/depth and unknowns. Selective-sync omissions are unknown, not nonexistent.
Root counts are not recursive totals. Modification times are not last-use dates.

Inspect only selected content needed for the current proposal. Open/download
online-only files selectively when necessary; preserve placeholders when access
is pending. Never hash the entire Dropbox collection just to find duplicates.
Do not read credential-like contents or put secrets in proposal text.

Check whether code, local configuration, Drive governance, shared permissions,
application paths, or links constrain movement. Identify the canonical copy and
destination from existing organization before inventing new folders.

## Review images

For every image selected in the current batch, follow [image review](IMAGE_REVIEW.md)
and the [review-images skill](../.agents/skills/review-images/SKILL.md). Obtain only
those selected bytes, generate private previews with `tools/image_review.py`,
and actually inspect every image using vision tools. Record descriptions,
categories, confidence, uncertainties and frame coverage against exact SHA-256
values. Unreviewed, unreadable or ambiguous images remain holds. Proposals must
show understandable descriptions alongside original filenames. Known content
does not establish inactivity, dependency freedom or Google Photos coverage.
Private inspection needs no extra prompt; external moves retain batch approval.

## Catalog books

For books, also follow [the catalog workflow](BOOK_CATALOG.md). Record physical
copies in their current locations and link digital holdings by verified identity.
An LCC label is classification evidence, not proof of edition, publication year,
file equivalence, or a shelf location. Physical shelf changes need a concrete
old/new-location proposal and approval; digital moves retain the file workflow.
Apply [book security](BOOK_SECURITY.md) before selected digital content use or
filing. Read-only scans and private scan metadata need no further approval;
the usual external filing and preservation rules remain in force.

## Encountered DjVu documents

Automatically convert selected accessible `.djvu`/`.djv` documents into private
PDF staging using [the conversion workflow](DJVU_CONVERSION.md) and
[the skill](../.agents/skills/convert-djvu/SKILL.md). Preserve originals and existing
OCR, verify counts and representative rendered pages, and prefer the verified PDF
for reading. Metadata-only discoveries enter a private queue without bulk hydration.
Conversion does not require another prompt; external filing follows the approved
batch workflow below. Record conversion, visual review, and filing separately.

## Propose and get sign-off

Use `templates/batch.json` for a small coherent batch, generally 10–20 items or
one clearly bounded folder. Include exact source and destination paths, reason,
verified evidence, archive rationale, collisions/duplicates, dependencies, holds,
and the reverse path. Label unknowns instead of guessing. Folder moves need a
descendant inventory and shared/app/link review; a single directory stat is not
an integrity check. Resolve clipped screenshot names before executable plans.

Present the concrete batch and ask the user to approve, revise, or exclude items.
Record the actual approval text, date, batch revision, and covered item IDs in an
ignored private decision record. Never pre-fill approval, fabricate sign-off, or
treat approval of the overall taxonomy as approval of a move list. A changed
destination, overwrite, merge, deletion, or scope expansion needs fresh sign-off.

## Execute only approved items

Revalidate paths and source identity immediately before execution. Stop on drift
or collisions, including case-insensitive/Unicode-equivalent names. Refuse
overwrites, folder merges, and following symlink targets. For local regular files,
record size and SHA-256 after selective hydration when necessary. For cloud moves,
use provider identity/revision/integrity metadata where available; if equivalent
verification is unavailable, record the limitation and hold dependent removals.

Provider revision tokens and server modification times can change on relocation,
as observed in B02b. Record old/new revisions and verify stable file IDs and
provider content hashes rather than requiring a revision token to stay unchanged.

Use an operation that cannot overwrite a destination. Across filesystems, copy
to a new destination, verify, then remove the source only within the approved move
scope. Preserve both copies if verification fails. Avoid partial moves of active
downloads, packages, repositories, application data, and live projects.

After each item, record the outcome, verification, errors, destination identity,
and concrete reverse mapping. Do not declare Dropbox cloud sync complete based
only on local existence. Update affected indexes and project references, including
the physics catalog if its paths change. Report any unverified cloud state.

## Roll back and resume

A reverse mapping is a plan, not permission to overwrite. On rollback, check
source/destination identity and collisions again. Preserve any subsequent edits.
After interruption, inspect both paths and the operation log before continuing;
never assume which side completed. Re-inventory affected areas and retain the
old snapshot. Distinguish planned, approved, in-progress, verified, failed, held,
and rolled-back work. A folder is closed only after all descendants are resolved.

## Privacy

Keep raw inventories, filenames, hashes, manifests, approvals, and private review
artifacts in ignored `.local/`. Git contains reusable workflow and templates.
Never publish, commit private data, change sharing, or move secrets to Dropbox
as an incidental part of organization. Credential-like material is reviewed under
the local configuration exception; filename matching is only a preliminary hint.
