---
name: zotero-lit-import
description: Import a set of literature references into a Zotero library via the Zotero Web API. Turns a bibliography (DOIs or normalized records) into journalArticle items, verifies metadata against CrossRef, and posts them to a user-chosen collection. Always asks which collection to import into.
---

# Zotero literature import

Push a curated set of references into the user's Zotero library. Designed as the
final step of a literature-research workflow: after you have a list of papers
(DOIs, PMIDs, or assembled bibliography records), this skill verifies the
metadata and writes clean `journalArticle` items into a Zotero collection the
user picks.

## Prerequisites

1. **Credential** — a Zotero API key stored as a Claude Science credential named
   `ZOTERO` (Customize → Credentials). The key needs **library + write** access.
   Get one at https://www.zotero.org/settings/keys ("Create new private key",
   enable "Allow library access" and "Allow write access").
2. **Network** — `api.zotero.org` must be on the allowlist. If a call fails with
   `Connection refused`, call `request_network_access(domain="api.zotero.org")`.
   CrossRef verification additionally needs `api.crossref.org`.

## Kernel helpers (auto-loaded from `kernel.py`)

Run these in the **`python` tool** (they make plain HTTP calls; `host.credentials`
is available there):

- `get_zotero_auth(credential_name="ZOTERO")` → `{"api_key", "user_id", "access"}`.
  Resolves the numeric userID and confirms write access. Check
  `auth["access"]["user"]["write"] is True` before posting.
- `list_zotero_collections(auth)` → list of `{"key","name","parent"}`.
- `create_zotero_collection(auth, name, parent_key=None)` → new collection key
  (top-level when `parent_key` is None).
- `crossref_record(doi, email=None)` → normalized bib dict
  (`authors`/`title`/`journal`/`volume`/`issue`/`pages`/`year`/`doi`/`retracted`).
  Use it to build records from bare DOIs and to catch **retractions** — skip any
  record where `retracted` is True and tell the user.
- `bib_to_zotero_items(records, collection_key=None, extra_tags=None)` → item
  payloads. Each record accepts `authors` (list of `"Last, First"`), `title`,
  `journal`, `volume`, `issue`, `pages`, `year`, `doi`, `pmid`.
- `post_zotero_items(auth, items)` → `{"successful","failed","failures"}`.
  Chunks at 50 items/request automatically.

Pass the contact email from `host.get_user_email()` to `crossref_record` when
available (catch `host.ContactEmailUnavailable` and omit it otherwise).

## Workflow

1. `auth = get_zotero_auth()`; verify `auth["access"]["user"]["write"]`.
2. Build `records` — from `crossref_record(doi)` for each DOI, or from a
   bibliography you already assembled. Drop retracted entries.
3. **Ask the user which collection to import into — every time.** Fetch
   `list_zotero_collections(auth)`, present them (respect parent/child nesting),
   and offer "create a new collection" as an option. Do not assume a destination
   or reuse a previous one. Use the `ask_user` tool with concrete options.
4. If the user wants a new collection, `create_zotero_collection(auth, name,
   parent_key)`; otherwise use the chosen collection's key.
5. `items = bib_to_zotero_items(records, collection_key=key, extra_tags=[...])`
   then `post_zotero_items(auth, items)`.
6. Report successful/failed counts. On failures, surface `result["failures"]`.

## Notes

- Items are created **without PDF attachments** — attach separately if needed.
- The Zotero API caps items at 50 per request; the helper chunks for you.
- Group libraries: this skill targets the user's personal library
  (`/users/{id}/...`). For a group library, swap the path prefix to
  `/groups/{groupID}/...` in a one-off call.
