#!/usr/bin/env python3
"""
Step 2 (practical version): import a rental-listing export you've already
collected (e.g. from your own Apify Zillow-scraper run) and merge it into
<metro-slug>-rentals.csv, cross-referenced against the communities/streets
found in Step 1.

Usage:
    python3 import_rentals.py little-rock-ar path/to/export.csv
"""
import argparse
import datetime
import os

from config.metros import get_metro
from src import csv_io
from src.rental_import import import_rental_export, load_known_streets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metro_slug", help="e.g. little-rock-ar")
    parser.add_argument("export_csv", help="path to your rental-listing export CSV")
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
    matched_rows, unmatched = import_rental_export(
        args.export_csv, metro_config, known_streets, today=datetime.date.today()
    )

    print(f"{len(matched_rows)} listings matched a known community street.")
    print(f"{unmatched} listings did not match any known street (not on a tracked builder's streets, or outside this metro).")

    rentals_path = os.path.join(
        args.output_dir, f"{metro_config.METRO_SLUG}-rentals.csv"
    )
    csv_io.upsert_rentals(rentals_path, matched_rows, datetime.date.today().isoformat())
    print(f"Wrote/updated {rentals_path}")


if __name__ == "__main__":
    main()
