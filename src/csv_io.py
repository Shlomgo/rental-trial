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


def _normalize_address(full_address):
    """'2356 Sam Tillery Dr, Alexander, AR 72002' and
    '2356 Sam Tillery Dr, Alexander, AR' (no zip) must dedupe to the same
    row, so the key drops the zip, lowercases, and collapses whitespace."""
    s = full_address.lower()
    s = re.sub(r"\b\d{5}\b", "", s)  # drop zip if present
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


def upsert_rentals(path, new_rows, today_str):
    """new_rows: list of dicts with RENTALS_COLUMNS keys (status_changed may
    be omitted; it's computed here by comparing to the prior status).
    Key = normalized full_address (zip-insensitive) — a rental property is
    unique by street address regardless of whether the zip was included."""
    key_fields = ["full_address"]
    existing = _read_rows(path, key_fields, normalize_address=True)

    for row in new_rows:
        row = dict(row)
        row["last_checked_date"] = today_str
        key = _row_key(row, key_fields, normalize_address=True)
        prior = existing.get(key)
        if prior and prior.get("status") and prior.get("status") != row.get("status"):
            row["status_changed"] = f"{prior['status']} -> {row.get('status')} ({today_str})"
        else:
            row["status_changed"] = prior.get("status_changed", "") if prior else ""
        existing[key] = row

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RENTALS_COLUMNS)
        writer.writeheader()
        for row in existing.values():
            writer.writerow({k: row.get(k, "") for k in RENTALS_COLUMNS})
