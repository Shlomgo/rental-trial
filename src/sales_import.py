"""
Step 3 (sales pipeline tracking): import a for-sale MLS/builder inventory
export (Status, Subdivision, Address, prices, sqft, beds, dates) and:
  1. tally each community's sold / under-contract / for-sale counts, and
  2. discover new streets via subdivision-name matching, same as
     mls_import.py does for rentals.

This is a separate concern from rentals.csv: rentals.csv tracks individual
properties that came up for RENT: this tracks the community's overall
NEW-CONSTRUCTION SALES pipeline (how many of the planned homes have sold).

Status code mapping (interpreted from the codes actually seen in a real
export - flagged to the user since a few are genuinely ambiguous):
  SLD, SBL   -> sold        (both have a populated Closed Date close to
                              the input date; SBL looks like "Sold -
                              Builder Lot", a sold variant for
                              builder-owned inventory)
  UCT, UCBL  -> under_contract (both have "UC" in them; UCBL's Closed Date
                              looks like an *expected* closing, not an
                              actual one)
  ACT        -> for_sale
  WITH       -> withdrawn   (excluded from sold/UC/for-sale and from the
                              percent-sold denominator)
  TBU        -> to_be_built (no Closed Date; kept separate - unclear if
                              this should count as "for sale" yet)
  PCHG       -> other       (only ever seen once; looks like a stray
                              price-change log row, not a real status)
"""
import csv
import re

from src.community_match import extract_phase, find_subdivision_matches

_STATUS_BUCKET = {
    "SLD": "sold", "SBL": "sold",
    "UCT": "under_contract", "UCBL": "under_contract",
    "ACT": "for_sale",
    "WITH": "withdrawn",
    "TBU": "to_be_built",
}

BUCKETS_IN_PIPELINE = ("sold", "under_contract", "for_sale")


def _strip_house_number(address):
    parts = address.split()
    i = 0
    while i < len(parts) and re.match(r"^\d+[a-zA-Z]?$", parts[i]):
        i += 1
    return " ".join(parts[i:])


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


def _parse_price(price_str):
    return re.sub(r"[^\d.]", "", price_str or "")


def import_sales_export(export_csv_path, metro_config, known_streets, known_communities):
    """Returns (records, new_streets, unmatched_count, ambiguous_count,
    unrecognized_statuses: set).

    records: one dict per matched row - {community_name, builder, phase,
    street_name, full_address, bedrooms, sqft, list_price, price,
    status_bucket, status_raw, input_date, closed_date}.
    new_streets: same shape as mls_import.py's, for upsert_communities.
    """
    known_streets_by_community = {}
    for kn, krow in known_streets:
        known_streets_by_community.setdefault(krow["community_name"], []).append((kn, krow))

    records = []
    new_street_candidates = {}
    unmatched = 0
    ambiguous = 0
    unrecognized_statuses = set()

    with open(export_csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            address = (row.get("Address") or "").strip()
            street_guess = _strip_house_number(address)
            match = _match_street(street_guess, known_streets)

            if match:
                community_name, builder, phase, street_name = (
                    match["community_name"], match["builder"], match.get("phase", ""), match["street_name"],
                )
            else:
                subdivision = (row.get("Subdivision") or "").strip()
                subdivision_matches = find_subdivision_matches(subdivision, known_communities)
                if len(subdivision_matches) > 1:
                    ambiguous += 1
                    continue
                if len(subdivision_matches) == 0:
                    unmatched += 1
                    continue
                community = subdivision_matches[0]
                community_name, builder = community["community_name"], community["builder"]
                phase = community.get("phase") or extract_phase(subdivision)
                street_name = street_guess

                norm = _normalize_street(street_guess)
                if norm and not _match_street(street_guess, known_streets_by_community.get(community_name, [])):
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
                        candidates.append({"norm": norm, "display": street_guess, "builder": builder, "phase": phase})

            status_raw = (row.get("Status") or "").strip().upper()
            status_bucket = _STATUS_BUCKET.get(status_raw)
            if status_bucket is None:
                status_bucket = "other"
                if status_raw:
                    unrecognized_statuses.add(status_raw)

            records.append({
                "metro_area": metro_config.METRO_AREA,
                "community_name": community_name,
                "builder": builder,
                "phase": phase,
                "street_name": street_name,
                "full_address": address,
                "bedrooms": (row.get("Beds") or "").strip(),
                "sqft": (row.get("Apx SQFT") or "").strip(),
                "list_price": _parse_price(row.get("List Price", "")),
                "price": _parse_price(row.get("Price", "")),
                "status_bucket": status_bucket,
                "status_raw": status_raw,
                "input_date": (row.get("Input Date") or "").strip(),
                "closed_date": (row.get("Closed Date") or "").strip(),
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

    return records, new_streets, unmatched, ambiguous, unrecognized_statuses
