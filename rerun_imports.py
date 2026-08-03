#!/usr/bin/env python3
"""
Re-runs matching against every rental-data file registered for a metro
(sources/<metro-slug>/manifest.csv) - this is the "Run" step: after adding
a new street with add_street.py, this checks that street against
everything you've uploaded so far, not just new uploads.

Usage:
    python3 rerun_imports.py little-rock-ar
"""
import argparse
import datetime
import os

from config.metros import get_metro
from src import csv_io
from src.community_match import load_known_communities
from src.community_totals import recompute_totals, upsert_sales_records
from src.mls_import import import_mls_export
from src.rental_import import import_rental_export, load_known_streets
from src.sales_import import import_sales_export
from src.sources_registry import load_manifest, source_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metro_slug", help="e.g. little-rock-ar")
    parser.add_argument("--output-dir", default="output")
    args = parser.parse_args()

    metro_config = get_metro(args.metro_slug)
    communities_path = os.path.join(args.output_dir, f"{metro_config.METRO_SLUG}-communities.csv")
    rentals_path = os.path.join(args.output_dir, f"{metro_config.METRO_SLUG}-rentals.csv")
    ledger_path = os.path.join(args.output_dir, f"{metro_config.METRO_SLUG}-sales-records.csv")
    totals_path = os.path.join(args.output_dir, f"{metro_config.METRO_SLUG}-community-totals.csv")
    if not os.path.exists(communities_path):
        raise SystemExit(f"{communities_path} not found - run run_discovery.py first.")

    manifest = load_manifest(args.metro_slug)
    if not manifest:
        raise SystemExit(
            f"No sources registered for {args.metro_slug} yet - nothing to re-run. "
            f"(sources/{args.metro_slug}/manifest.csv is empty or missing.)"
        )

    today = datetime.date.today()
    today_str = today.isoformat()
    total_matched = 0
    total_new_streets = 0
    any_sales_source = False

    for entry in manifest:
        path = source_path(args.metro_slug, entry["filename"])
        if not os.path.exists(path):
            print(f"  [skip] {entry['filename']} - file missing from sources/{args.metro_slug}/")
            continue

        # Reload known streets/communities fresh each pass, since an
        # earlier source in this same run may have just discovered a new
        # street that a later source should also get to match against.
        known_streets = load_known_streets(communities_path)
        known_communities = load_known_communities(communities_path)

        if entry["source_type"] == "apify":
            matched_rows, unmatched = import_rental_export(path, metro_config, known_streets, today=today)
            new_streets, ambiguous = [], 0
            csv_io.upsert_rentals(rentals_path, matched_rows, today_str)
        elif entry["source_type"] == "mls":
            matched_rows, new_streets, unmatched, ambiguous = import_mls_export(
                path, metro_config, known_streets, known_communities
            )
            if new_streets:
                csv_io.upsert_communities(communities_path, new_streets)
            csv_io.upsert_rentals(rentals_path, matched_rows, today_str)
        else:  # sales
            any_sales_source = True
            matched_rows, new_streets, unmatched, ambiguous, unrecognized = import_sales_export(
                path, metro_config, known_streets, known_communities
            )
            if new_streets:
                csv_io.upsert_communities(communities_path, new_streets)
            upsert_sales_records(ledger_path, matched_rows, today_str)

        total_matched += len(matched_rows)
        total_new_streets += len(new_streets)
        print(f"  {entry['filename']} ({entry['source_type']}): {len(matched_rows)} matched, "
              f"{len(new_streets)} new street(s), {unmatched} unmatched"
              + (f", {ambiguous} ambiguous" if ambiguous else ""))

    if any_sales_source:
        recompute_totals(ledger_path, totals_path, metro_config.METRO_AREA, today_str)
        print(f"Updated {totals_path}.")

    print(f"\nDone. {total_matched} total matches across {len(manifest)} source file(s), "
          f"{total_new_streets} new street(s) added to {communities_path}.")
    print(f"Updated {rentals_path}.")


if __name__ == "__main__":
    main()
