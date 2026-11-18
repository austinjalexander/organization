---
name: organize-roam-learning
description: Organizes learning resources from Roam Research in this repository. Use when inventorying Roam reading lists or course links, proposing catalog or purchase-queue entries, or applying the organization-repo tag to approved pages after local verification.
---

# Organize learning resources from Roam

Read [repository policy](../../../AGENTS.md) and the [organization workflow](../../../docs/WORKFLOW.md).
Use the [book catalog workflow](../../../docs/BOOK_CATALOG.md) for books.

## Discover and propose

1. Prefer the connected Roam MCP. If the graph is unknown, list the graphs and
   select the one relevant to the request. Get that graph's guidelines once
   per session before reading or writing. If access is missing, use Roam's
   [official MCP and Desktop instructions](https://github.com/Roam-Research/roam-tools)
   and explain the access needed. Keep tokens in local app configuration.
2. Read the selected learning list and relevant resource pages. Capture page
   and source-block IDs, links, observed metadata, and uncertainties in
   ignored `.local/`. Preserve Roam reading notes, status fields, and schedules
   in place. Consult existing local records before proposing additions. A title
   match is a candidate until its identity is resolved. A missing catalog entry
   leaves ownership and cloud availability unknown.
3. Propose a concrete batch with the source pages, local destinations, holds,
   and exact Roam pages to tag. Record approval and exclusions privately. A
   pilot approval covers that batch only.

## Record, verify, and tag

1. Record books in `.local/book-catalog.json` using the existing catalog
   schema. Keep edition and copy details provisional when the only evidence is
   a Roam title or a label such as `#physical-copy` or `#kindle`. Track
   explicit purchase candidates in `.local/roam-purchase-queue.json`. For other
   approved resources, record the source reference and disposition in the
   private batch record or an applicable existing index.
2. Read back each saved record before tagging its Roam page. Verify its ID,
   source page, and intended disposition. The tag marks a verified local
   record. Bibliographic or holdings verification can still be pending.
3. Re-read the approved page by UID and check for an equivalent standalone
   tag. Reuse an existing marker. Otherwise append one top-level
   `#organization-repo` block to the exact resource page. Keep hub and subject
   pages outside an item batch unless explicitly approved.
4. Verify one marker on each page. If a write response is empty or ambiguous,
   re-read the page before considering another write and follow Roam's
   confirmation policy. Record the local record ID, page UID, tag block UID,
   and verification result in the private batch log. For rollback, identify
   only the tag block created by the batch and check for later edits.
