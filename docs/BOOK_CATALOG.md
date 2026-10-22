# Physical and digital book catalog

Scope confirmed October 20, 2026: include physical books and add Library of
Congress Classification (LCC) to the organization project. The catalog model and
shelving approach below are a starting proposal. No shelf or file moves are
authorized by this document.

## One catalog, distinct holdings

Use one record per identified edition, with a stable `record_id` independent of
title, path, ISBN, or call number. A `work_id` groups related editions once their
relationship is established. Each physical copy or digital file has its own
`holding_id`; owning a printed copy does not establish ownership of a digital one.
An incompletely identified edition may have a provisional record. Consolidate
metadata only after identity review; retain IDs, history, and all distinct copies.

Use [the reusable template](../templates/book-catalog.json) for the structure.
The private working catalog is `.local/book-catalog.json`. Keep personal titles,
paths, shelf locations, photos, annotations, and evidence out of tracked files.
The template contains a blank record and holding to illustrate the fields; remove
unused placeholders in real catalogs. `null` means unknown, and an empty holdings
list means none recorded, not proof that the user owns none.

Each record includes:

- Title, authors, edition statement, publisher, publication year, language,
  ISBNs, and optional LCCN, with evidence and verification status. Leave unobserved
  fields unknown. ISBN identifies an edition/format, not an individual copy.
- Subject tags and references to existing subject folders or indexes. A topic
  inferred from a title must be labeled as such. A folder reference requires an
  observed path; do not create a plausible-looking path as if it existed.
- LCC assignments, preserving both raw text and normalized display text,
  component fields, source, verification status, and the holdings they describe.
- Physical holdings: format, current room/bookcase/shelf/position, proposed
  location separately, label evidence, volume, copy number, annotations, and loans.
- Digital holdings: canonical provider/path or link, provider identity when known,
  file format, volume, annotations/version distinctions, and match evidence.
  Respect Dropbox, Drive, repository, shared-folder, and app constraints.
  Add `digital.sha256` and `digital.security_scan` for exact file bytes, following
  [the security workflow](BOOK_SECURITY.md). Keep scan status, date, engine,
  signature versions and private report reference. Scan selected unscanned books
  before content use; a physical copy or matching title does not inherit a scan.
- Evidence records with source/date, supported fields, and limitations, plus
  unresolved questions. Evidence pointers do not imply archival preservation of
  a temporary attachment or verification of its bibliographic claims.

## LCC as an organizational feature

Support browsing by class letters, classification number, full call number,
subject, author, location, and format. A full call number can contain a class
number, Cutter(s), a date, and other item information. Store the original label
even if parsing is incomplete. LCCN is a separate catalog-record identifier and
must never be used as a shelving key.

An observed handwritten label is not an LC-assigned number verified against the
correct edition. Use assignment statuses `observed_label`, `candidate`,
`verified_edition`, or `unresolved`; keep `assigned_by` unknown until supported.
Attach each assignment to the relevant holding IDs so one copy's label is not
silently applied to another edition or format. Preserve conflicting numbers with
their sources for review, and do not silently replace existing labels.

For sorting ordinary parsed call numbers, compare class letters alphabetically,
then the class number numerically including its decimal portion, then successive
Cutter letters and decimal digits, then date and any remaining item information.
A plain string sort is insufficient. Complex or partially parsed call numbers
need manual review rather than a guessed shelf position. This document specifies
the proposed behavior; the JSON template does not implement a sorting engine.

If no LCC is available, catalog the book anyway. Leave its assignment list empty
and track the lookup status; do not invent an authoritative number. A future
lookup should match edition/ISBN against LC, publisher, or library evidence and
retain its source. Any locally proposed classification stays marked `candidate`.

## Shelving proposal

Give current physical locations stable IDs such as `CASE-01-SHELF-02`; record the
real room and shelf orientation before using an ID. An initial photo can establish
that a copy was observed without establishing where it is shelved.

Propose broad subject/LCC zones and call-number order within them, then adjust
for available space, oversized books, multi-volume sets, and frequent use. Record
each exception's actual location in the catalog so it remains findable. The user
can review strict LCC order versus practical zones after shelf coverage is known.

Begin with 10–20 books or one shelf. Capture title/author, full label, copy identity,
and current location first. Resolve bibliographic gaps selectively using an ISBN
or title/copyright-page photo supplied for that purpose. Inventory the current
arrangement before proposing any relocation or relabeling.

For an approved physical rearrangement, record the exact holding IDs, old and new
locations, approval scope, execution outcome, and reverse mapping privately.
Verify each copy and its new position afterward. Physical checks use copy/label
and location evidence; digital moves still require the normal manifest, collision,
integrity, link-update, and rollback workflow. Never treat an annotated copy as
disposable because another holding shares its title or call number.

## Digital integration and storage

Keep existing canonical digital files in their approved homes, including the
established STEM tree. Link rather than copy. Match a digital file to a print
edition only with adequate identity evidence; otherwise use a separate provisional
record and an unresolved relationship. LCC browsing can span multiple folders and
physical locations without changing the underlying paths.

For now `.local/book-catalog.json` is the working catalog. A canonical private
catalog in Dropbox fits the default storage policy, but its exact destination,
any new folders, and migration need a concrete proposal and approval. If the
catalog later moves, keep one authoritative dataset and clearly identify any
local exports or generated indexes. No Dropbox catalog folder is created now.

## Classification references

- [LC explanation of call numbers](https://ask.loc.gov/faq/396298).
- [LC MARC 050: class number, item number, and assignment source](https://www.loc.gov/marc/bibliographic/bd050.html).
- [Library of Congress Control Numbers](https://www.loc.gov/marc/lccn.html).
