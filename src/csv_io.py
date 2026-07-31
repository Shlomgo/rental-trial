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
    "full_address", "purchase_price", "rent_price", "list_date", "rent_date",
    "days_on_market", "status", "source_url", "last_checked_date",
    "status_changed",
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
    Key = (metro_area, community_name, builder, phase, street_name)."""
    key_fields = ["metro_area", "community_name", "builder", "phase", "street_name"]
    existing = _read_rows(path, key_fields)
    for row in new_rows:
        key = tuple(row.get(k, "") for k in key_fields)
        existing[key] = row  # add new, or overwrite identical existing row

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COMMUNITIES_COLUMNS)
        writer.writeheader()
        for row in existing.values():
            writer.writerow({k: row.get(k, "") for k in COMMUNITIES_COLUMNS})


_MERGE_FIELDS = [
    "purchase_price", "rent_price", "list_date", "rent_date",
    "days_on_market",
]


def _merge_row(prior, new_row):
    """Different sources fill in different fields for the same property
    (e.g. Zillow gives a rent price + list_date, an MLS export gives
    days_on_market + an MLS-number citation) - a blind overwrite would
    throw away whichever source ran first. Prefer the new value where the
    source has one; otherwise keep what's already on file."""
    merged = dict(prior) if prior else {}
    merged.update(new_row)  # new row's non-key fields as the starting point
    for field in _MERGE_FIELDS:
        if not new_row.get(field) and prior and prior.get(field):
            merged[field] = prior[field]
    if prior:
        old_src, new_src = prior.get("source_url", ""), new_row.get("source_url", "")
        if old_src and new_src and old_src != new_src:
            merged["source_url"] = f"{old_src} | {new_src}"
        elif not new_src:
            merged["source_url"] = old_src
    return merged


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

        merged = _merge_row(prior, row)
        merged["last_checked_date"] = today_str
        if prior and prior.get("status") and prior.get("status") != row.get("status"):
            merged["status_changed"] = f"{prior['status']} -> {row.get('status')} ({today_str})"
        else:
            merged["status_changed"] = prior.get("status_changed", "") if prior else ""
        existing[key] = merged

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RENTALS_COLUMNS)
        writer.writeheader()
        for row in existing.values():
            writer.writerow({k: row.get(k, "") for k in RENTALS_COLUMNS})
