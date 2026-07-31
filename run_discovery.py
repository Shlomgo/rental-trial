#!/usr/bin/env python3
"""
Step 1-3 entry point: discover new-construction communities for a metro and
write <metro-slug>-communities.csv.

Usage:
    python3 run_discovery.py little-rock-ar
"""
import argparse
import os

from config.metros import get_metro
from src import csv_io
from src.discover import discover_communities, communities_to_rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metro_slug", help="e.g. little-rock-ar")
    parser.add_argument("--output-dir", default="output")
    args = parser.parse_args()

    metro_config = get_metro(args.metro_slug)
    os.makedirs(args.output_dir, exist_ok=True)

    print(f"Discovering communities for {metro_config.METRO_AREA}...")
    communities = discover_communities(metro_config)
    print(f"Found {len(communities)} communities total.")

    rows = communities_to_rows(metro_config, communities)
    communities_path = os.path.join(
        args.output_dir, f"{metro_config.METRO_SLUG}-communities.csv"
    )
    csv_io.upsert_communities(communities_path, rows)
    print(f"Wrote {len(rows)} street rows to {communities_path}")


if __name__ == "__main__":
    main()
