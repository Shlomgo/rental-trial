"""
Tracks each community's overall new-construction sales pipeline:
manually-entered total planned home count, plus sold/under-contract/
for-sale counts computed from sales-export data (src/sales_import.py).
"""
import csv
import os
from collections import defaultdict

SALES_RECORDS_COLUMNS = [
    "metro_area", "community_name", "builder", "phase", "street_name",
    "full_address", "bedrooms", "sqft", "list_price", "price",
    "status_bucket", "status_raw", "input_date", "closed_date",
    "last_checked_date", "status_changed",
]

TOTALS_COLUMNS = [
    "metro_area", "community_name", "builder", "phase", "total_homes_planned",
    "sold_count", "under_contract_count", "for_sale_count",
    "withdrawn_count", "expired_count", "to_be_built_count", "other_count",
    "pct_sold", "last_updated",
]


def _read_rows(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_rows(path, rows, columns):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in columns})


def _normalize_address(full_address):
    import re
    s = full_address.lower()
    s = re.sub(r"\b\d{5}\b", "", s)
    for pattern, repl in [
        (r"\bdrive\b", "dr"), (r"\blane\b", "ln"), (r"\bcourt\b", "ct"),
        (r"\bcircle\b", "cir"), (r"\bstreet\b", "st"), (r"\bavenue\b", "ave"),
        (r"\bboulevard\b", "blvd"), (r"\broad\b", "rd"), (r"\btrail\b", "trl"),
    ]:
        s = re.sub(pattern, repl, s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return s.strip()


def upsert_sales_records(path, new_rows, today_str):
    """Sales-export rows are point-in-time snapshots, not multi-episode
    history like rentals - so on conflict the row with the more recent
    Input Date simply replaces the old one wholesale (not field-merged)."""
    existing = {}
    for row in _read_rows(path):
        existing[_normalize_address(row.get("full_address", ""))] = row

    for row in new_rows:
        row = dict(row)
        key = _normalize_address(row.get("full_address", ""))
        prior = existing.get(key)

        if prior and prior.get("input_date", "") > row.get("input_date", ""):
            merged = dict(prior)  # prior is newer; keep it as-is
        else:
            merged = dict(row)
            if prior and prior.get("status_bucket") != row.get("status_bucket"):
                merged["status_changed"] = f"{prior['status_bucket']} -> {row['status_bucket']} ({today_str})"
            else:
                merged["status_changed"] = prior.get("status_changed", "") if prior else ""
        merged["last_checked_date"] = today_str
        existing[key] = merged

    _write_rows(path, list(existing.values()), SALES_RECORDS_COLUMNS)


def set_total_homes_planned(path, metro_area, community_name, builder, phase, total_homes):
    rows = _read_rows(path)
    key = (community_name, builder)
    found = False
    for row in rows:
        if (row["community_name"], row["builder"]) == key:
            row["total_homes_planned"] = str(total_homes)
            found = True
    if not found:
        rows.append({
            "metro_area": metro_area, "community_name": community_name,
            "builder": builder, "phase": phase, "total_homes_planned": str(total_homes),
            "sold_count": "0", "under_contract_count": "0", "for_sale_count": "0",
            "withdrawn_count": "0", "to_be_built_count": "0", "other_count": "0",
            "pct_sold": "", "last_updated": "",
        })
    _write_rows(path, rows, TOTALS_COLUMNS)


def recompute_totals(ledger_path, totals_path, metro_area, today_str):
    """Recomputes sold/under_contract/for_sale/... counts for every
    community that appears in the sales-records ledger, preserving
    whatever total_homes_planned is already on file (this never touches
    that column - use set_total_homes_planned for it)."""
    ledger_rows = _read_rows(ledger_path)
    prior_totals = {(r["community_name"], r["builder"]): r for r in _read_rows(totals_path)}

    counts = defaultdict(lambda: defaultdict(int))
    phase_by_key = {}
    for r in ledger_rows:
        key = (r["community_name"], r["builder"])
        counts[key][r["status_bucket"]] += 1
        if r.get("phase"):
            phase_by_key[key] = r["phase"]

    all_keys = set(counts) | set(prior_totals)
    output_rows = []
    for key in sorted(all_keys):
        community_name, builder = key
        prior = prior_totals.get(key, {})
        c = counts.get(key, {})
        sold = c.get("sold", 0)
        total_planned = prior.get("total_homes_planned", "")
        pct_sold = ""
        if total_planned:
            try:
                pct_sold = f"{sold / int(total_planned) * 100:.1f}"
            except (ValueError, ZeroDivisionError):
                pct_sold = ""

        output_rows.append({
            "metro_area": metro_area,
            "community_name": community_name,
            "builder": builder,
            "phase": phase_by_key.get(key, prior.get("phase", "")),
            "total_homes_planned": total_planned,
            "sold_count": str(sold),
            "under_contract_count": str(c.get("under_contract", 0)),
            "for_sale_count": str(c.get("for_sale", 0)),
            "withdrawn_count": str(c.get("withdrawn", 0)),
            "expired_count": str(c.get("expired", 0)),
            "to_be_built_count": str(c.get("to_be_built", 0)),
            "other_count": str(c.get("other", 0)),
            "pct_sold": pct_sold,
            "last_updated": today_str,
        })

    _write_rows(totals_path, output_rows, TOTALS_COLUMNS)
