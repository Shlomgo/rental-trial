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
        if kn and (kn == norm or re.search(rf"\b{re.escape(kn)}\b", norm) or
                   re.search(rf"\b{re.escape(norm)}\b", kn)):
            return krow
    return None


# Zillow scraper export field names we read from (matches the Apify
# "zillowscraper" actor's output columns as of 2026-07). This is schema v1.
_PRICE_FIELD = "unformattedPrice"
_STATUS_TEXT_FIELD = "statusText"
_STATUS_TYPE_FIELD = "statusType"
_DAYS_ON_ZILLOW_FIELD = "daysOnZillow"
_DETAIL_URL_FIELD = "detailUrl"
_SOLD_DATE_FIELD = "dateSold"
_SOLD_PRICE_FIELD = "listingSoldPrice"
_BEDS_FIELD = "beds"
_SQFT_FIELD = "area"

# A second, much wider (~2000-column) Apify Zillow export schema seen from
# 2026-08 (e.g. Google Drive "Apify Uploads"). Distinguished by having this
# column, which v1 never has. Column names use "/" for nested JSON fields.
_WIDE_SCHEMA_MARKER = "listingAddress/full"


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


def _build_row_v1(metro_config, match, row, today):
    full_address = (row.get("address") or "").strip()
    rent_price = row.get(_PRICE_FIELD) or ""
    list_date = _approx_list_date(row.get(_DAYS_ON_ZILLOW_FIELD), today)
    status = _status_from_row(row)
    source_url = row.get(_DETAIL_URL_FIELD) or ""
    rent_date = row.get(_SOLD_DATE_FIELD) or ""
    days_on_market = _days_between(list_date, rent_date)

    return {
        "metro_area": metro_config.METRO_AREA,
        "community_name": match["community_name"],
        "builder": match["builder"],
        "phase": match.get("phase", ""),
        "street_name": match["street_name"],
        "full_address": full_address,
        "bedrooms": row.get(_BEDS_FIELD) or "",
        "sqft": row.get(_SQFT_FIELD) or "",
        "purchase_price": row.get(_SOLD_PRICE_FIELD) or "",
        "rent_price": rent_price,
        "list_date": list_date,
        "rent_date": rent_date,
        "days_on_market": days_on_market,
        "status": status,
        "source_url": source_url,
    }


def _wide_row_street_guess(row):
    street = (row.get("listingAddress/street") or row.get("address/streetAddress") or
              row.get("abbreviatedAddress") or "").strip()
    parts = street.split()
    i = 0
    while i < len(parts) and re.match(r"^\d+[a-zA-Z]?$", parts[i]):
        i += 1
    return " ".join(parts[i:])


def _wide_price_history(row):
    """[(date_iso, event_text), ...] from the 'listingPriceHistory/N/...'
    columns, in the order they appear (index 0 = most recent, per the data
    observed - Zillow lists price history newest-first)."""
    history = []
    i = 0
    while True:
        date_raw = row.get(f"listingPriceHistory/{i}/date")
        if date_raw is None:
            break
        if date_raw:
            history.append((date_raw[:10], row.get(f"listingPriceHistory/{i}/event") or ""))
        i += 1
    return history


def _normalize_home_status(row):
    """Newer zillow-detail-scraper builds (seen from 2026-09) omit the
    enum-style `homeStatus` field (e.g. "FOR_RENT") this schema was written
    against, and instead only carry a camelCase `listingStatus` (e.g.
    "forRent"). Prefer `homeStatus` when present; otherwise convert
    `listingStatus`'s camelCase into the same SHOUTY_SNAKE_CASE shape so
    the rest of this module doesn't need to know which one it got."""
    home_status = (row.get("homeStatus") or "").upper()
    if home_status:
        return home_status
    listing_status = (row.get("listingStatus") or "").strip()
    if listing_status:
        return re.sub(r"(?<!^)(?=[A-Z])", "_", listing_status).upper()
    return ""


def _wide_status_and_dates(row, today):
    """Returns (status, list_date, rent_date). Prefers the price-history
    log (real listed/removed dates) over the daysOnZillow estimate used for
    schema v1, since this schema happens to carry it."""
    home_status = _normalize_home_status(row)
    history = _wide_price_history(row)
    listed_date = next((d for d, e in history if "listed" in e.lower()), "")
    left_market_date = history[0][0] if history and "listed" not in history[0][1].lower() else ""

    if home_status == "FOR_RENT":
        status = "currently for rent"
        list_date = listed_date or _approx_list_date(row.get("daysOnZillow"), today)
        rent_date = ""
    elif home_status:
        # This dataset comes from a rental search, so any other non-blank
        # status (OFF_MARKET, RECENTLY_SOLD, ...) means it left the rental
        # market - the most recent history entry marks when.
        status = "previously rented"
        list_date = listed_date
        rent_date = left_market_date
    else:
        status = "unknown"
        list_date, rent_date = "", ""
    return status, list_date, rent_date


def _build_row_v2(metro_config, match, row, today):
    full_address = (row.get("listingAddress/full") or "").strip()
    status, list_date, rent_date = _wide_status_and_dates(row, today)
    source_url = (row.get("propertyUrl") or "").strip()
    if not source_url:
        hdp = (row.get("hdpUrl") or row.get("bdpUrl") or "").strip()
        source_url = f"https://www.zillow.com{hdp}" if hdp.startswith("/") else hdp
    days_on_market = _days_between(list_date, rent_date) or (row.get("daysOnZillow") or "")

    # price/listingPrice/amount are only a rent figure while the listing is
    # actually FOR_RENT - once it's left the rental market (sold, off
    # market, ...) those same fields hold whatever price that other status
    # means (e.g. a sale price), and blindly reusing them as rent produces
    # nonsense like a "$191,000/month" rent. Leave rent_price blank rather
    # than guess in that case.
    home_status = _normalize_home_status(row)
    rent_price = (row.get("listingPrice/amount") or row.get("price") or "") if home_status == "FOR_RENT" else ""

    return {
        "metro_area": metro_config.METRO_AREA,
        "community_name": match["community_name"],
        "builder": match["builder"],
        "phase": match.get("phase", ""),
        "street_name": match["street_name"],
        "full_address": full_address,
        "bedrooms": row.get("bedrooms") or "",
        "sqft": row.get("livingArea") or "",
        "purchase_price": row.get("lastSoldPrice") or "",
        "rent_price": rent_price,
        "list_date": list_date,
        "rent_date": rent_date,
        "days_on_market": days_on_market,
        "status": status,
        "source_url": source_url,
    }


def import_rental_export(export_csv_path, metro_config, known_streets, today=None):
    """Returns (matched_rows, unmatched_count). matched_rows are dicts with
    RENTALS_COLUMNS keys (minus last_checked_date/status_changed, which the
    caller/csv_io fills in). Auto-detects which of the two known Apify
    Zillow export schemas the file uses."""
    today = today or datetime.date.today()
    matched_rows = []
    unmatched = 0

    with open(export_csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        is_wide = _WIDE_SCHEMA_MARKER in (reader.fieldnames or [])
        for row in reader:
            street_guess = _wide_row_street_guess(row) if is_wide else _street_guess_v1(row)
            match = _match_street(street_guess, known_streets)
            if not match:
                unmatched += 1
                continue

            if is_wide:
                matched_rows.append(_build_row_v2(metro_config, match, row, today))
            else:
                matched_rows.append(_build_row_v1(metro_config, match, row, today))

    return matched_rows, unmatched


def _street_guess_v1(row):
    street_raw = (row.get("addressStreet") or "").strip()
    parts = street_raw.split()
    i = 0
    while i < len(parts) and re.match(r"^\d+[a-zA-Z]?$", parts[i]):
        i += 1
    return " ".join(parts[i:])
