"""
Step 2 (another practical source): import an MLS rental/lease export (the
kind a real estate agent can pull, e.g. columns like MLS #, Subdivision,
Price, Closed Date, Days On Market, Address, City, Status) and cross-
reference it against the communities/streets found in Step 1.

Like rental_import.py, this only reads a file the user already obtained
through their own access (here, an MLS export) - no fetching happens here.

MLS status values vary by board, but in practice a residential-lease MLS
export reuses whatever generic status picklist the MLS has, so labels like
"Sold" or "Pending" show up meaning "the lease closed" / "lease pending"
rather than a home sale.
"""
import csv
import datetime
import re

from src.community_match import extract_phase, find_subdivision_matches

_STATUS_MAP = {
    "rented": "previously rented",
    "leased": "previously rented",
    "sold": "previously rented",
    "active": "currently for rent",
    "new listing": "currently for rent",
    "pending (fc, ss, reo)": "currently for rent",
    "pending": "currently for rent",
    "withdrawn": "unknown",
    "expired": "unknown",
}


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


def _match_street(street_guess, known_streets):
    norm = _normalize_street(street_guess)
    if not norm:
        return None
    for kn, krow in known_streets:
        if kn and (kn == norm or kn in norm or norm in kn):
            return krow
    return None


def _strip_house_number(address):
    parts = address.split()
    i = 0
    while i < len(parts) and re.match(r"^\d+[a-zA-Z]?$", parts[i]):
        i += 1
    return " ".join(parts[i:])


def _parse_price(price_str):
    return re.sub(r"[^\d.]", "", price_str or "")


def _parse_date(date_str):
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(date_str.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def _build_row(metro_config, community_name, builder, phase, street_name, address, city, row):
    status_raw = (row.get("Status") or "").strip().lower()
    status = _STATUS_MAP.get(status_raw, "unknown")

    closed_date = _parse_date(row.get("Closed Date", ""))
    try:
        days_on_market = int(float(row.get("Days On Market", "") or 0))
    except ValueError:
        days_on_market = None

    list_date, rent_date = "", ""
    if status == "previously rented" and closed_date:
        rent_date = closed_date.isoformat()
        if days_on_market is not None:
            list_date = (closed_date - datetime.timedelta(days=days_on_market)).isoformat()

    mls_number = (row.get("MLS #") or "").strip()

    return {
        "metro_area": metro_config.METRO_AREA,
        "community_name": community_name,
        "builder": builder,
        "phase": phase,
        "street_name": street_name,
        "full_address": f"{address}, {city}, AR",
        "bedrooms": (row.get("Beds") or "").strip(),
        "sqft": (row.get("Approx SQFT") or "").strip(),
        "purchase_price": "",  # this export is rental/lease data, not sale price
        "rent_price": _parse_price(row.get("Price", "")),
        "list_date": list_date,
        "rent_date": rent_date,
        "days_on_market": str(days_on_market) if days_on_market is not None else "",
        "status": status,
        "source_url": f"MLS #{mls_number}" if mls_number else "",
    }


def import_mls_export(export_csv_path, metro_config, known_streets, known_communities=None):
    """Returns (matched_rows, new_streets, unmatched_count, ambiguous_count).

    matched_rows: dicts with RENTALS_COLUMNS keys (minus last_checked_date/
    status_changed), for rows that matched a known street OR a known
    community via its subdivision name.
    new_streets: {community_name, builder, phase, street_name} dicts for
    streets discovered via subdivision match that weren't already in
    communities.csv - the caller should upsert these into communities.csv
    so a sold-out street stays on record even after this one export.
    ambiguous_count: rows whose subdivision text matched more than one
    known community - skipped rather than guessed.
    """
    metro_cities = {c.lower() for c in getattr(metro_config, "CITIES", [])}
    known_communities = known_communities or []
    # community_name -> [(normalized_street, krow), ...], for containment
    # matching so "Cain" still matches an already-known "Cain Trail".
    known_streets_by_community = {}
    for kn, krow in known_streets:
        known_streets_by_community.setdefault(krow["community_name"], []).append((kn, krow))

    matched_rows = []
    # community_name -> [{"norm": ..., "display": ..., "builder": ..., "phase": ...}]
    new_street_candidates = {}
    unmatched = 0
    ambiguous = 0

    with open(export_csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            city = (row.get("City") or "").strip()
            if metro_cities and city.lower() not in metro_cities:
                continue

            address = (row.get("Address") or "").strip()
            street_guess = _strip_house_number(address)
            match = _match_street(street_guess, known_streets)

            if match:
                matched_rows.append(_build_row(
                    metro_config, match["community_name"], match["builder"],
                    match.get("phase", ""), match["street_name"], address, city, row,
                ))
                continue

            # No known street matched - fall back to matching the MLS
            # "Subdivision" text against known community names. This is
            # what catches a street that already sold out and dropped off
            # the builder's live sitemap before Step 1 ever saw it.
            subdivision = (row.get("Subdivision") or "").strip()
            subdivision_matches = find_subdivision_matches(subdivision, known_communities)
            if len(subdivision_matches) > 1:
                ambiguous += 1
                continue
            if len(subdivision_matches) == 0:
                unmatched += 1
                continue
            community = subdivision_matches[0]

            phase = community.get("phase") or extract_phase(subdivision)
            matched_rows.append(_build_row(
                metro_config, community["community_name"], community["builder"],
                phase, street_guess, address, city, row,
            ))

            community_name = community["community_name"]
            norm = _normalize_street(street_guess)
            if not norm:
                continue

            # Already known for this community (even with a missing/short
            # suffix, e.g. "Cain" vs. known "Cain Trail")? Not new.
            if _match_street(street_guess, known_streets_by_community.get(community_name, [])):
                continue

            # Seen already this run, just spelled differently ("Olympic" vs
            # "Olympic Drive")? Merge into the longer/more descriptive form.
            candidates = new_street_candidates.setdefault(community_name, [])
            existing = next(
                (c for c in candidates if c["norm"] == norm or c["norm"] in norm or norm in c["norm"]),
                None,
            )
            if existing:
                if len(street_guess) > len(existing["display"]):
                    existing["display"] = street_guess
                    existing["norm"] = norm
            else:
                candidates.append({
                    "norm": norm, "display": street_guess,
                    "builder": community["builder"], "phase": phase,
                })

    new_streets = [
        {
            "metro_area": metro_config.METRO_AREA,
            "community_name": community_name,
            "builder": c["builder"],
            "phase": c["phase"],
            "street_name": c["display"],
        }
        for community_name, candidates in new_street_candidates.items()
        for c in candidates
    ]

    return matched_rows, new_streets, unmatched, ambiguous
