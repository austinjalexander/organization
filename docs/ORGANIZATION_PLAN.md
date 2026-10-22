# Proposed organization — v1, October 19, 2026

Status: structure, archive convention, and review order approved October 19, 2026
(user: "ok, sounds good"). This is not an executable move list. Existing folders
remain where they are until their batch is approved.

## Proposed Dropbox roots

- `Inbox/`: new unfiled material awaiting review; not a permanent catch-all.
- `Personal/`: family and people, identity and legal records, health, finances,
  homes, vehicles, travel, and personal administration.
- `Work/`: employment, businesses, consulting, and professional records that are
  not governed by Google Drive. Separate entities and engagements inside it.
- `1_Studies/`: preserve the existing library root and STEM tree. Eventually
  accommodate learning, schools, courses, and academic records through reviewed
  batches; reuse established subject folders and canonical book files.
- `Creative/`: writing, visual art, design, and creative project source material.
- `Media/`: personal photos, videos, audio, and reference/entertainment collections.
- `Archive/`: inactive records organized by domain and original context, such as
  `Archive/Work/<entity>/<period>/` and `Archive/Imports/<source>/`.

Shared and application-controlled roots may remain at the Dropbox root. Confirm
their actual constraints before proposing a move; do not force every folder into
the taxonomy. Code/config/Drive exceptions are routing rules, not Dropbox roots.

## Filing decisions

Use one canonical file, with indexes/references where useful. A family photo
belongs with its event in Media; a family member's administrative record belongs
in Personal. School course material belongs in Studies; an identity record for
the same person stays in Personal. Business receipts belong with the entity;
personal receipts belong with their financial purpose. Code stays with its repo,
while supporting non-code documents normally belong in Dropbox and can be linked.
Check whether project assets must remain in a repo to build/run before splitting.

Prefer readable, stable names. Use ISO dates when verified; preserve original
filenames until there is a reason to rename. Do not invent dates, full names,
editions, relationships, or the meaning of abbreviations. Record uncertain items
as holds instead of routing them speculatively.

An archive is retained material with a known former context, not trash. Age alone
does not make legal, tax, medical, educational, family, or identity records
inactive. Confirm the user's ongoing use and any dependencies before archiving.
Deletion, duplicate removal, and compression are separate proposals.

## Review sequence

1. **B00 — Coverage and routing.** Reconcile the screenshot folder labels with
   locally visible entries and, when accessible, a cloud listing. Resolve clipped
   names, shared status, code/config dependencies, and Drive ownership. No moves.
2. **B01 — Loose-file pilot.** Review 10–20 completed Desktop/Downloads files.
   Prefer a coherent group of non-sensitive reference documents. Search existing
   Dropbox destinations, verify identity, and present exact paths before approval.
   Avoid credential-like files and app installers in the first pilot.
3. **B02 — Inbox and old imports.** Inspect existing catch-alls, desktop exports,
   phone imports, and old staging areas. Preserve each import's provenance; do
   not flatten, merge, or discard it based on its name.
4. **B03 — Studies and career.** Review schools, courses, resumes, and academic
   records. Preserve the established book library and update affected repo links.
5. **B04 — Personal administration.** Review finances, identity/legal, housing,
   health, vehicles, and travel in separate small batches.
6. **B05 — Work and organizations.** Confirm Drive governance and active versus
   former engagements before organizing supporting records or archives.
7. **B06 — People, creative work, and media.** Confirm personal-name folders and
   organize photos/media with event context and versions preserved.
8. **B07 — Archive and closure.** Review unresolved folders and confirmed inactive
   material. Reconcile every discovered root entry and then every descendant.

The private initial review proposes a route or hold for every cloud root entry
and one additional local Finder metadata entry. The connected Dropbox listing on
October 19, 2026 exhausted pagination: 120 folders/shared mounts and seven files.
All five clipped screenshot labels were resolved. One shared mount is held for
ownership/dependency review. These routes are name-based hypotheses; descendants,
file contents, inactivity, and governance remain unverified.

## Physical and digital books — addition, October 20, 2026

Include physical books in the organization project. Use a shared catalog to
connect physical copies, digital files, editions, existing subject folders, and
LCC call numbers. The user already labels physical books with LCC when available.
Preserve those labels as evidence and record missing classifications explicitly.

LCC is an additional catalog browsing and proposed shelving feature. It does not
replace the established `1_Studies/1_STEM` tree or authorize renaming digital
files. Subject tags can connect books across disciplines without copying files.
Keep each physical copy, annotated digital file, and distinct edition identifiable.

Start by cataloging a small shelf or user-selected group in its current location.
Then propose shelf zones with stable location IDs and LCC order within each zone,
recording exceptions for size, sets, and frequently used books. Review exact
physical relocations separately, with old/new locations and a reverse mapping.
See [the catalog specification](BOOK_CATALOG.md) for fields and evidence rules.
The working catalog stays private in `.local/`; choosing a canonical Dropbox
catalog location and any related folder creation remains pending approval.

## Completion standard

Every discovered source folder and descendant is reconciled: retained in an
approved home, relocated and verified, held with a specific question, or excluded
with a documented owner/reason. Cloud coverage must be established before calling
all of Dropbox complete. Desktop, Downloads, Documents, home-level loose files,
and other user-selected locations receive the same reconciliation later.

## Structure approval recorded

The user approved the seven roots (keeping `1_Studies`), archive convention,
and review sequence on October 19, 2026. This authorizes planning against those
destinations; it does not authorize a bulk relocation. B01 has its own exact
source/destination manifest and requires separate sign-off.
