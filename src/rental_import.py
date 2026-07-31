"""
Step 2 (practical version): import an already-scraped rental-listing export
(e.g. an Apify "zillowscraper"-style dataset CSV) and cross-reference it
against the communities/streets we discovered from builder sitemaps in
Step 1.

We do not fetch these listing pages ourselves - Zillow/Realtor.com/
Apartments.com/Rent.com block automated access and disallow it in
robots.txt. This module only reads a CSV the user already collected
through their own tooling/account and matches it locally against known
builder streets.
"""
import csv
import datetime
import re


def _normalize_street(s):
    s = s.lower()
    s = re.sub(r"\bdrive\b", "dr", s)
    s = re.sub(r"\blane\b", "ln", s)
    s = re.sub(r"\bcourt\b", "ct", s)
    s = re.sub(r"\bcircle\b", "cir", s)
    s = re.sub(r"\bstreet\b", "st", s)
    s = re.sub(r"\bavenue\b", "ave", s)
    s = re.sub(r"\bboulevard\b", "blvd", s)
    s = re.sub(r"\broad\b", "rd", s)
    s = re.sub(r"[^a-z0-9 ]", "", s)
    return s.strip()


def load_known_streets(communities_csv_path):
    """Returns [(normalized_street, row_dict), ...] from a communities.csv
    produced by run_discovery.py."""
    known = []
    with open(communities_csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("street_name"):
                known.append((_normalize_street(row["street_name"]), row))
    return known


def _match_street(street_guess, known_streets):
    norm = _normalize_street(street_guess)
    if not norm:
        return None
    for kn, krow in known_streets:
        if kn and (kn == norm or kn in norm or norm in kn):
            return krow
    return None


# Zillow scraper export field names we read from (matches the Apify
# "zillowscraper" actor's output columns as of 2026-07).
_PRICE_FIELD = "unformattedPrice"
_STATUS_TEXT_FIELD = "statusText"
_STATUS_TYPE_FIELD = "statusType"
_DAYS_ON_ZILLOW_FIELD = "daysOnZillow"
_DETAIL_URL_FIELD = "detailUrl"
_SOLD_DATE_FIELD = "dateSold"
_SOLD_PRICE_FIELD = "listingSoldPrice"


def _status_from_row(row):
    status_type = (row.get(_STATUS_TYPE_FIELD) or "").upper()
    if "RENT" in status_type:
        return "currently for rent"
    if "SOLD" in status_type:
        return "previously rented" if "RENT" in (row.get(_STATUS_TEXT_FIELD) or "").upper() else "unknown"
    return "unknown"


def _approx_list_date(days_on_zillow_str, today):
    if not days_on_zillow_str:
        return ""
    try:
        days = int(float(days_on_zillow_str))
    except ValueError:
        return ""
    return (today - datetime.timedelta(days=days)).isoformat()


def _days_between(list_date_iso, rent_date_iso):
    if not list_date_iso or not rent_date_iso:
        return ""
    try:
        d1 = datetime.date.fromisoformat(list_date_iso)
        d2 = datetime.date.fromisoformat(rent_date_iso[:10])
        return str((d2 - d1).days)
    except ValueError:
        return ""


def import_rental_export(export_csv_path, metro_config, known_streets, today=None):
    """Returns (matched_rows, unmatched_count). matched_rows are dicts with
    RENTALS_COLUMNS keys (minus last_checked_date/status_changed, which the
    caller/csv_io fills in)."""
    today = today or datetime.date.today()
    matched_rows = []
    unmatched = 0

    with open(export_csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            street_raw = (row.get("addressStreet") or "").strip()
            # Strip leading house number to get just the street name.
            parts = street_raw.split()
            i = 0
            while i < len(parts) and re.match(r"^\d+[a-zA-Z]?$", parts[i]):
                i += 1
            street_guess = " ".join(parts[i:])

            match = _match_street(street_guess, known_streets)
            if not match:
                unmatched += 1
                continue

            full_address = (row.get("address") or "").strip()
            rent_price = row.get(_PRICE_FIELD) or ""
            list_date = _approx_list_date(row.get(_DAYS_ON_ZILLOW_FIELD), today)
            rent_date = row.get(_SOLD_DATE_FIELD) or ""
            status = _status_from_row(row)
            source_url = row.get(_DETAIL_URL_FIELD) or ""
            days_on_market = _days_between(list_date, rent_date)

            matched_rows.append({
                "metro_area": metro_config.METRO_AREA,
                "community_name": match["community_name"],
                "builder": match["builder"],
                "phase": match.get("phase", ""),
                "street_name": match["street_name"],
                "full_address": full_address,
                "purchase_price": row.get(_SOLD_PRICE_FIELD) or "",
                "rent_price": rent_price,
                "list_date": list_date,
                "rent_date": row.get(_SOLD_DATE_FIELD) or "",
                "days_on_market": days_on_market,
                "status": status,
                "source_url": source_url,
            })

    return matched_rows, unmatched
