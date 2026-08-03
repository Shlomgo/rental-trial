#!/usr/bin/env python3
"""
Step 2 (another practical source): import an MLS rental/lease export you
already have (e.g. from a real estate agent's MLS access) and merge it into
<metro-slug>-rentals.csv, cross-referenced against Step 1's communities.

Usage:
    python3 import_mls.py little-rock-ar path/to/mls_export.csv
"""
import argparse
import datetime
import os

from config.metros import get_metro
from src import csv_io
from src.community_match import load_known_communities
from src.mls_import import import_mls_export
from src.rental_import import load_known_streets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metro_slug", help="e.g. little-rock-ar")
    parser.add_argument("export_csv", help="path to your MLS export CSV")
    parser.add_argument("--output-dir", default="output")
    args = parser.parse_args()

    metro_config = get_metro(args.metro_slug)
    communities_path = os.path.join(
        args.output_dir, f"{metro_config.METRO_SLUG}-communities.csv"
    )
    if not os.path.exists(communities_path):
        raise SystemExit(
            f"{communities_path} not found - run run_discovery.py first."
        )

    known_streets = load_known_streets(communities_path)
    known_communities = load_known_communities(communities_path)
    matched_rows, new_streets, unmatched, ambiguous, city_by_community = import_mls_export(
        args.export_csv, metro_config, known_streets, known_communities
    )

    print(f"{len(matched_rows)} listings matched (by street name or by subdivision name).")
    if new_streets:
        print(f"{len(new_streets)} new street(s) discovered via subdivision match (not in the original sitemap scrape):")
        for s in new_streets:
            print(f"   {s['community_name']} ({s['builder']}): {s['street_name']}")
    print(f"{ambiguous} listing(s) had a subdivision name matching more than one known community - skipped rather than guessed.")
    print(f"{unmatched} listings did not match any known street or subdivision.")

    if new_streets:
        csv_io.upsert_communities(communities_path, new_streets)
        print(f"Added {len(new_streets)} new street row(s) to {communities_path}")

    backfilled = csv_io.backfill_city(communities_path, city_by_community)
    if backfilled:
        print(f"Filled in city for {backfilled} existing communities.csv row(s).")

    rentals_path = os.path.join(
        args.output_dir, f"{metro_config.METRO_SLUG}-rentals.csv"
    )
    csv_io.upsert_rentals(rentals_path, matched_rows, datetime.date.today().isoformat())
    print(f"Wrote/updated {rentals_path}")


if __name__ == "__main__":
    main()
