"""CSV read/write with upsert semantics, so re-running the pipeline updates
existing rows in place instead of duplicating them."""
import csv
import os
import re

COMMUNITIES_COLUMNS = [
    "metro_area", "community_name", "builder", "phase", "street_name",
]

RENTALS_COLUMNS = [
    "metro_area", "community_name", "builder", "phase", "street_name",
    "full_address", "bedrooms", "sqft", "purchase_price", "rent_price",
    "list_date", "rent_date", "days_on_market", "status", "source_url",
    "last_checked_date", "status_changed",
]


_STREET_SUFFIX_SUBS = [
    (r"\bdrive\b", "dr"), (r"\blane\b", "ln"), (r"\bcourt\b", "ct"),
    (r"\bcircle\b", "cir"), (r"\bstreet\b", "st"), (r"\bavenue\b", "ave"),
    (r"\bboulevard\b", "blvd"), (r"\broad\b", "rd"), (r"\btrail\b", "trl"),
]


def _normalize_address(full_address):
    """Different sources spell the same address differently - '...Dr' vs
    '...Drive', with/without zip - so these must all dedupe to one row:
    the key drops the zip, lowercases, normalizes street suffixes, and
    collapses whitespace/punctuation."""
    s = full_address.lower()
    s = re.sub(r"\b\d{5}\b", "", s)  # drop zip if present
    for pattern, repl in _STREET_SUFFIX_SUBS:
        s = re.sub(pattern, repl, s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return s.strip()


def _read_rows(path, key_fields, normalize_address=False):
    """Returns {key_tuple: row_dict} for an existing CSV, or {} if missing."""
    if not os.path.exists(path):
        return {}
    rows = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = _row_key(row, key_fields, normalize_address)
            rows[key] = row
    return rows


def _row_key(row, key_fields, normalize_address=False):
    if normalize_address and key_fields == ["full_address"]:
        return (_normalize_address(row.get("full_address", "")),)
    return tuple(row.get(k, "") for k in key_fields)


def upsert_communities(path, new_rows):
    """new_rows: list of dicts with COMMUNITIES_COLUMNS keys.
    Key = (metro_area, community_name, builder, phase, street_name).

    A community with zero confirmed streets gets one placeholder row with
    a blank street_name (from Step 1 discovery). The moment a real street
    is confirmed for that community, the placeholder is redundant - drop
    it instead of leaving a stale blank row sitting next to real streets."""
    key_fields = ["metro_area", "community_name", "builder", "phase", "street_name"]
    existing = _read_rows(path, key_fields)
    for row in new_rows:
        key = tuple(row.get(k, "") for k in key_fields)
        existing[key] = row  # add new, or overwrite identical existing row
        if row.get("street_name"):
            placeholder_key = (row.get("metro_area", ""), row.get("community_name", ""),
                                row.get("builder", ""), row.get("phase", ""), "")
            existing.pop(placeholder_key, None)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COMMUNITIES_COLUMNS)
        writer.writeheader()
        for row in existing.values():
            writer.writerow({k: row.get(k, "") for k in COMMUNITIES_COLUMNS})


# Fields that describe one specific rental *episode* (a single listing/
# lease), as opposed to fields that are true regardless of which episode
# we're looking at (purchase_price) or are pure citations (source_url).
_EPISODE_FIELDS = ["rent_price", "list_date", "rent_date", "days_on_market", "status"]


def _episode_date(row):
    """The date that identifies which rental episode a row describes.
    ISO 'YYYY-MM-DD' strings sort correctly as plain strings."""
    return row.get("rent_date") or row.get("list_date") or ""


def _merge_row(prior, new_row):
    """The same address can appear multiple times across (or within) an
    import - either as different sources describing the SAME rental episode
    (Zillow gives a price, an MLS export adds days-on-market), or as
    genuinely different, chronologically distinct episodes (the house was
    rented in 2022, then again in 2026). Blending fields across two
    different episodes produces nonsense (e.g. a "currently for rent"
    status paired with a 2022 list date), so: if the new row's episode is
    the same as or newer than what's on file, adopt its episode fields
    wholesale; otherwise treat it as supplementary and only fill gaps.

    Returns (merged_dict, adopted_new_episode: bool)."""
    if not prior:
        return dict(new_row), True

    new_ep, prior_ep = _episode_date(new_row), _episode_date(prior)
    adopted_new = bool(new_ep) and (not prior_ep or new_ep >= prior_ep)

    merged = dict(prior)
    if adopted_new:
        merged.update(new_row)
    else:
        for field, value in new_row.items():
            if field in _EPISODE_FIELDS:
                if not merged.get(field) and value:
                    merged[field] = value
            elif value:
                merged[field] = value

    # Sale price, bedroom count, and square footage are physical facts
    # about the property, not tied to which rental episode we're looking
    # at - always fine to backfill, and a source that's silent on them
    # should never blank out a value another source already gave us.
    for field in ("purchase_price", "bedrooms", "sqft"):
        if new_row.get(field):
            merged[field] = new_row[field]
        elif prior.get(field):
            merged[field] = prior[field]

    # Combine citations as a deduped set, not a blind append - otherwise
    # re-running the same source file keeps re-appending the same
    # citation forever.
    old_tokens = [t.strip() for t in prior.get("source_url", "").split("|") if t.strip()]
    new_tokens = [t.strip() for t in new_row.get("source_url", "").split("|") if t.strip()]
    combined = list(old_tokens)
    for token in new_tokens:
        if token not in combined:
            combined.append(token)
    merged["source_url"] = " | ".join(combined)

    return merged, adopted_new


def upsert_rentals(path, new_rows, today_str):
    """new_rows: list of dicts with RENTALS_COLUMNS keys (status_changed may
    be omitted; it's computed here by comparing to the prior status).
    Key = normalized full_address (zip/suffix-insensitive) — a rental
    property is unique by street address regardless of source formatting."""
    key_fields = ["full_address"]
    existing = _read_rows(path, key_fields, normalize_address=True)

    for row in new_rows:
        row = dict(row)
        key = _row_key(row, key_fields, normalize_address=True)
        prior = existing.get(key)

        merged, adopted_new = _merge_row(prior, row)
        merged["last_checked_date"] = today_str
        if adopted_new and prior and prior.get("status") and prior.get("status") != row.get("status"):
            merged["status_changed"] = f"{prior['status']} -> {row.get('status')} ({today_str})"
        else:
            merged["status_changed"] = prior.get("status_changed", "") if prior else ""
        existing[key] = merged

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RENTALS_COLUMNS)
        writer.writeheader()
        for row in existing.values():
            writer.writerow({k: row.get(k, "") for k in RENTALS_COLUMNS})
