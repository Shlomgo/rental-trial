# New-Construction Rental Tracker

Tracks D.R. Horton and Lennar new-construction communities across several
metros: which streets they built, which properties have come up for rent,
and (where sales data exists) the new-construction sales pipeline
(sold/under-contract/for-sale counts vs. planned total homes).

This file is what a brand-new session (no memory of any prior conversation)
needs to pick this project up cold. Read it fully before doing anything.

## Metros tracked

| Metro | Slug | Dashboard artifact URL |
|---|---|---|
| Little Rock, AR | `little-rock-ar` | https://claude.ai/code/artifact/5170beda-e22d-451a-8104-a44e243cd0b6 |
| Hickory, NC | `hickory-nc` | https://claude.ai/code/artifact/21660801-3214-4c66-b5c5-05889f2811de |
| Baldwin County, AL | `baldwin-county-al` | https://claude.ai/code/artifact/dca9b9f3-f9a8-4b83-a165-eb7e8964315f |
| Oklahoma City, OK | `oklahoma-city-ok` | https://claude.ai/code/artifact/a5e67897-d8ae-4c71-ac88-0059c722b6bc |

Metros index (links to all of the above): https://claude.ai/code/artifact/04ea9813-4b9f-4cfb-9427-cc38bd526df5

Each metro's authoritative config (region paths, cities, the artifact URL
above) lives in `config/metros/<slug>.py` - always read `DASHBOARD_ARTIFACT_URL`
from there before republishing, never hardcode/guess it, and never mint a
new artifact for an existing metro (always pass the existing `url` to the
Artifact tool).

## Repo layout

- `config/metros/<slug>.py` - one file per metro: builder URL region paths,
  the metro's CITIES list (used as an actual filter, not just cosmetic -
  builders sometimes file a metro under a much broader region, e.g. Hickory
  under D.R. Horton's whole "Charlotte" region), and `DASHBOARD_ARTIFACT_URL`.
- `src/` - the pipeline logic, shared across all metros (metro-specific
  values only ever come from `config/metros/`, never hardcoded in `src/`):
  - `builders/dr_horton.py`, `builders/lennar.py` - sitemap-based community/
    street discovery (Step 1, no manual data needed).
  - `rental_import.py` - imports rental listing exports. Auto-detects two
    Apify Zillow schemas: an old flat one, and a new ~2000-column "wide"
    schema (detected by the `listingAddress/full` column) that most current
    Apify data uses.
  - `mls_import.py` - imports MLS rental/lease exports (Status, Subdivision,
    Address, Price, Days On Market, City columns), with subdivision-name
    fallback matching for streets that sold out and dropped off the
    builder's sitemap.
  - `sales_import.py` / `community_totals.py` - for-sale MLS/builder
    inventory exports -> the sales-pipeline ledger and aggregated totals.
  - `csv_io.py` - upsert/merge logic for rentals.csv (episode-aware: treats
    the same address's different rental periods as distinct, doesn't blend
    an old lease's dates with a new one's status).
  - `sources_registry.py` - see "Sources registry" below.
- `sources/<slug>/` - every raw file ever supplied for that metro, copied
  verbatim, plus `manifest.csv` registering each one. This is what makes a
  full rebuild possible without losing anything (see "Sources registry").
- `output/<slug>-communities.csv`, `-rentals.csv`, `-sales-records.csv`,
  `-community-totals.csv`, `-dashboard.html` - the actual tracked data and
  the generated dashboard for that metro. `output/index.html` is the
  cross-metro landing page.
- `run_discovery.py`, `import_mls.py`, `import_sales.py`, `add_street.py`,
  `set_total_homes.py`, `rerun_imports.py`, `generate_dashboard.py`,
  `generate_index.py` - CLI entry points, each `python3 <script>.py --help`
  documents its own args. `rerun_imports.py <slug>` replays every source
  registered for that metro against the current known streets - this is
  the one to run after adding a street or fixing a bug in `src/`.

## Sources registry (why nothing gets lost)

Every file anyone has ever supplied - MLS exports, Apify exports, pasted
listings - gets copied into `sources/<slug>/` and registered in
`sources/<slug>/manifest.csv` with a `source_type` (`apify`, `mls`, `sales`,
or `manual` for hand-entered listings with no backing file). `rerun_imports.py`
replays literally everything registered, so:
- A full rebuild (`rm output/<slug>-rentals.csv && python3 rerun_imports.py <slug>`)
  never loses data, as long as the source was actually registered - **always
  register a source before or immediately after importing it**, never import
  a one-off file without registering it, or a future rebuild will silently
  drop that data (this has happened before - see Known Issues).
- Reruns are idempotent by design - verify with an md5sum before/after
  whenever you touch matching logic in `src/`.

## Daily data-refresh runbook

This is the actual recurring task. Follow it whenever asked to "check for
new data" or on a scheduled/Routine firing.

1. Check whether the **Apify** and **Google Drive** MCP connectors are
   available in this session right now (e.g. list the Apify actor's recent
   runs, or search Drive for the "Apify Uploads" folder). Both are known to
   be intermittent - available in some sessions/turns, not others, with no
   predictable pattern. If **neither** is available: if this is a scheduled/
   unattended firing, stop silently (no message, no retry-loop, no commit -
   pinging about a known intermittent issue is just noise). If a human is
   actively asking in chat, tell them plainly it's unavailable right now.

2. If Apify is available: the actor is `maxcopell/zillow-detail-scraper`
   (ID `ENK9p4RZHg0iVso52`). List its recent runs
   (`http://api.apify.internal:3333/v2/acts/ENK9p4RZHg0iVso52/runs?desc=true&limit=10`
   via `ReadMcpResourceTool`/`resources/read`) and compare the total run
   count against what's already reflected in `sources/*/manifest.csv`
   filenames (they embed run/dataset IDs, e.g. `apify-run-2026-08-12.csv`
   documents which run IDs it came from in its manifest label - check the
   label column, not just the filename, for the exact IDs already covered).
   For each new successful run: fetch its dataset via `get-dataset-items`
   with `fields` narrowed to exactly what `_build_row_v2` in
   `src/rental_import.py` reads (`listingAddress.full`, `listingAddress.street`,
   `homeStatus`, `bedrooms`, `livingArea`, `price`, `listingPrice.amount`,
   `daysOnZillow`, `propertyUrl`, `hdpUrl`, `lastSoldPrice`,
   `listingPriceHistory`) - full unfiltered items are ~2000 columns and will
   blow the token budget. Responses will usually exceed the inline size
   limit and get saved to a file - read/flatten that file with Python, don't
   try to force it inline. Flatten dot-notation keys to "/"-separated
   (`listingAddress.full` -> `listingAddress/full`) and expand
   `listingPriceHistory` into `listingPriceHistory/{i}/date` and
   `listingPriceHistory/{i}/event` - that's the exact shape
   `import_rental_export`'s wide-schema path expects. A single Apify run
   commonly contains addresses for multiple metros mixed together (e.g. a
   "Little Rock" run also carrying Hickory, NC addresses) - check each row's
   city/state and register+import the combined file against every metro it
   actually has addresses for, not just one.

3. If Google Drive is available: check the "Apify Uploads" folder for files
   not yet registered by Drive file ID (manifest filenames follow
   `apify-drive-<first10ofFileId>.csv`). Download and import any new ones
   the same way. Files delivered via Drive and via the Apify API directly
   are very often the same underlying run synced twice - don't assume
   "new file" means "new data"; diffing rentals.csv before/after (by
   normalized address) tells you what's actually new.

4. For every metro touched by new data: `python3 rerun_imports.py <slug>`,
   then `python3 generate_dashboard.py <slug>`, then republish via the
   Artifact tool to that metro's **existing** `DASHBOARD_ARTIFACT_URL` from
   its config file (never omit `url`/mint a new one). If the Artifact tool
   returns a "another session published a newer version" conflict and you
   have no reason to believe a real competing edit happened (the usual
   case - it's a stale version-tracking artifact), republish with
   `force: true`. Also regenerate + republish `output/index.html` to
   https://claude.ai/code/artifact/04ea9813-4b9f-4cfb-9427-cc38bd526df5
   if any metro's summary numbers changed.

5. `git add`, commit with a message describing what actually changed
   (new addresses found, any bug fixed, counts), `git push -u origin
   claude/new-construction-rental-tracker-wl3jze`.

6. Report back (or, for a scheduled firing, end silently) only if something
   new was actually imported or a real error needs flagging - not for a
   routine "connectors were down" outcome.

Before reporting "N new listings," always diff old vs. new `rentals.csv` by
*normalized address* (`src/csv_io._normalize_address`), not by raw import
match-count - a "matched" count includes re-matches of already-known
addresses (just a days-on-market refresh), which is not new data and
shouldn't be reported as such.

## Known issues already fixed (don't reintroduce these)

- **Street-name containment matching used to be a raw substring check**
  (`kn in norm or norm in kn`), which matched on word fragments, not words -
  e.g. "Kim Drive" silently matched a known street "IM Drive" because
  "kim dr" contains "im dr". Fixed to require word boundaries
  (`\bword\b` regex) in `_match_street` in all three importers
  (`sales_import.py`, `mls_import.py`, `rental_import.py`) plus the
  analogous new-street-candidate dedup check in `sales_import.py`/
  `mls_import.py`. If you ever touch street matching, keep the word-boundary
  behavior.
- **Address dedup key used to strip *any* 5-digit number, not just a
  trailing zip** (`\b\d{5}\b` unanchored), so a 5-digit house number (e.g.
  "10805 Mason Drive") collided with a different address on the same street.
  Fixed by anchoring to end-of-string (`\b\d{5}\b\s*$`) in
  `csv_io._normalize_address` and `community_totals._normalize_address`.
- **`rent_price` used to be read from `price`/`listingPrice/amount`
  regardless of `homeStatus`** - fine while a listing is actively
  `FOR_RENT`, but once it flips to `RECENTLY_SOLD`/other, those same fields
  hold a sale price, not rent (produced literal "$191,000/month" rows).
  Fixed in `_build_row_v2` (`src/rental_import.py`) to only trust those
  fields as rent when `homeStatus == "FOR_RENT"`; otherwise leave
  `rent_price` blank rather than guess - matches the project's general
  policy (also stated on the dashboard footer): blank means unreported, not
  guessed.
- **A full-CSV rebuild once silently dropped hand-entered listings** that
  had never been registered as a source (they'd only been upserted directly
  into rentals.csv, not saved to a replayable file). Fixed by adding a
  `manual` source type (`sources/<slug>/manual-entries.csv`) specifically
  for this - any time you add a listing by hand from pasted text with no
  backing export file, append it there and register it, don't just upsert
  it into the output CSV directly.
- **Dashboard header/title used to be hardcoded "Little Rock"** regardless
  of which metro was being generated. `generate_dashboard.py`'s `TEMPLATE`
  now substitutes `__METRO_AREA__` from `metro_config.METRO_AREA`.
- **A new metro's first dashboard generation used to hard-fail** if
  `rentals.csv` didn't exist yet (impossible for a metro with only
  discovery done, no rental data imported yet). `generate_dashboard.py`
  now treats a missing rentals.csv as an empty list, same as it already did
  for totals/sales.
- **Builder discovery used to trust a builder's region path as an exact
  metro boundary.** Some builders file a metro under a much broader region
  (D.R. Horton and Lennar both file Hickory, NC under their whole
  "Charlotte" region alongside dozens of unrelated cities). Both
  `src/builders/dr_horton.py` and `lennar.py` now also filter discovered
  cities against `metro_config.CITIES` - keep this filter when adding new
  metros with a similarly broad builder region.

## Connector automation status (as of this writing)

Scheduled Routines created via the `create_trigger` tool from inside a chat
session do **not** reliably carry Apify/Google Drive connector access to
the sessions they fire into - the platform has explicitly warned about this
every time. A daily Routine exists (self-bound to a specific session) but
has fired mostly as a no-op since connectors weren't available at firing
time. The one untried path: creating the Routine directly through claude.ai's
own Routines UI (not through this tool), explicitly attaching the Apify and
Google Drive connectors during setup - that may attach the grant correctly
where the tool-created one couldn't. If you set that up, point its prompt
at this file rather than re-embedding the runbook (e.g. "Follow the
daily-check runbook in CLAUDE.md at the root of shlomgo/rental-trial,
branch claude/new-construction-rental-tracker-wl3jze") - keeps the Routine
prompt short and means updating the runbook here is enough, no need to
also update the trigger.
