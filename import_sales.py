#!/usr/bin/env python3
"""
Import a for-sale MLS/builder inventory export and use it to:
  1. tally each community's sold / under-contract / for-sale counts
     (combined with set_total_homes.py's manually-entered totals into
     % sold), and
  2. discover new streets via subdivision-name matching.

Usage:
    python3 import_sales.py little-rock-ar path/to/sales_export.csv
"""
import argparse
import datetime
import os

from config.metros import get_metro
from src import csv_io
from src.community_match import load_known_communities
from src.community_totals import recompute_totals, upsert_sales_records
from src.rental_import import load_known_streets
from src.sales_import import import_sales_export


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metro_slug")
    parser.add_argument("export_csv")
    parser.add_argument("--output-dir", default="output")
    args = parser.parse_args()

    metro_config = get_metro(args.metro_slug)
    communities_path = os.path.join(args.output_dir, f"{metro_config.METRO_SLUG}-communities.csv")
    if not os.path.exists(communities_path):
        raise SystemExit(f"{communities_path} not found - run run_discovery.py first.")

    known_streets = load_known_streets(communities_path)
    known_communities = load_known_communities(communities_path)

    records, new_streets, unmatched, ambiguous, unrecognized = import_sales_export(
        args.export_csv, metro_config, known_streets, known_communities
    )

    print(f"{len(records)} listings matched a known community (by street or subdivision name).")
    if new_streets:
        print(f"{len(new_streets)} new street(s) discovered:")
        for s in new_streets:
            print(f"   {s['community_name']} ({s['builder']}): {s['street_name']}")
    if ambiguous:
        print(f"{ambiguous} listing(s) had a subdivision name matching more than one known community - skipped.")
    print(f"{unmatched} listings did not match any known street or subdivision.")
    if unrecognized:
        print(f"Unrecognized status code(s) found (counted as 'other'): {', '.join(sorted(unrecognized))}")

    if new_streets:
        csv_io.upsert_communities(communities_path, new_streets)

    today_str = datetime.date.today().isoformat()
    ledger_path = os.path.join(args.output_dir, f"{metro_config.METRO_SLUG}-sales-records.csv")
    totals_path = os.path.join(args.output_dir, f"{metro_config.METRO_SLUG}-community-totals.csv")

    upsert_sales_records(ledger_path, records, today_str)
    recompute_totals(ledger_path, totals_path, metro_config.METRO_AREA, today_str)

    print(f"Wrote {ledger_path}")
    print(f"Wrote {totals_path}")


if __name__ == "__main__":
    main()
